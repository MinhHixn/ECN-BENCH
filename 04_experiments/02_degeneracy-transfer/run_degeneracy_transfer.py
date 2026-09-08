#!/usr/bin/env python
"""Does degenerate consensus transfer to other unconstrained evaluators?

Section~\\ref{sec:volume_mechanism} of the technical report attributes the flat
forecasts to two factors acting together: structured-output enforcement disabled at
the request layer, and a large volume of evidence to compress. That account predicts
that any unconstrained evaluator handed the same long transcripts should degenerate
similarly.

This script tests the prediction directly. It takes the units the July instrument
(DeepSeek-R1-14B, served locally, enforcement disabled) returned an exactly uniform
vector for, and re-scores each of them with several other evaluators, all of them
run WITHOUT any response_format -- the same unconstrained condition -- on the same
byte-identical transcript.

We deliberately keep the prompt minimal and identical across evaluators (question,
condition, evidence, and an instruction to return a probability object with exactly
the given option keys). The pipeline's full rubric prompt asks for six further
nested structures, which some of these models cannot produce without a schema; the
minimal prompt isolates the quantity under test.

Run:  python run_degeneracy_transfer.py [--units all|flat] [--models a,b,c]
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z"
OUT = HERE / "degeneracy_transfer.json"

DEFAULT_MODELS = [
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1-distill-llama-70b",
    "qwen/qwen3-14b",
    "qwen/qwen3-32b",
    "mistralai/ministral-14b-2512",
]


def api_key() -> str:
    for name in (".env", ".env.openrouter"):
        p = HERE / "MiroFish-Offline" / name
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("OPENROUTER_API_KEY="):
                    return line.partition("=")[2].strip().strip('"').strip("'")
    raise SystemExit("no OPENROUTER_API_KEY")


def flat(p) -> bool:
    return bool(p) and max(abs(v - 1.0 / len(p)) for v in p.values()) < 0.005


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", choices=["flat", "all"], default="flat",
                    help="'flat' = only the units the July instrument flattened")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--max-tokens", type=int, default=4000)
    args = ap.parse_args()

    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key(),
                    timeout=240.0, max_retries=2)

    july = json.loads((CAMPAIGN / "event_results.json").read_text(encoding="utf-8"))
    sim = [r for r in july if r.get("condition") in ("B", "C")]
    units = [r for r in sim if flat(r.get("probabilities"))] if args.units == "flat" else sim
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"units: {len(units)} ({args.units})   evaluators: {len(models)}   "
          f"calls: {len(units) * len(models)}", flush=True)

    lock = threading.Lock()
    results: list[dict] = []

    def one(model: str, row: dict) -> None:
        ev = row["evidence_text"]
        opts = row.get("options") or ["YES", "NO"]
        msgs = [
            {"role": "system",
             "content": ("You are a Report Agent. Read the simulation transcript and return "
                         "a JSON object with a 'probabilities' field mapping each option to "
                         "a probability summing to 1. The keys MUST be exactly: "
                         f"{', '.join(opts)}.")},
            {"role": "user",
             "content": (f"Question: {row.get('question')}\n"
                         f"Condition: {row['condition']}\nEvidence: {ev}")},
        ]
        rec = {"model": model, "unit_id": row["unit_id"], "event_id": row["event_id"],
               "condition": row["condition"], "chars": len(ev),
               "july_flat": flat(row.get("probabilities"))}
        try:
            resp = client.chat.completions.create(
                model=model, messages=msgs, temperature=0.0,
                max_tokens=args.max_tokens)          # no response_format: unconstrained
            content = resp.choices[0].message.content or ""
            rec["finish_reason"] = resp.choices[0].finish_reason
            m = re.search(r"\{[\s\S]*\}", content)
            probs = None
            if m:
                try:
                    probs = json.loads(m.group(0)).get("probabilities")
                except Exception:
                    probs = None
            if isinstance(probs, dict) and probs:
                tot = sum(probs.values())
                if tot > 0:
                    probs = {k: v / tot for k, v in probs.items()}
            rec["probabilities"] = probs
            rec["parsed"] = isinstance(probs, dict) and bool(probs)
            rec["flat"] = flat(probs)
            rec["modal"] = max(probs.values()) if rec["parsed"] else None
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            rec["parsed"] = False
        with lock:
            results.append(rec)
            n = len(results)
            if n % 10 == 0:
                print(f"  {n}/{len(units) * len(models)}", flush=True)

    jobs = [(m, r) for m in models for r in units]
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(lambda t: one(*t), jobs))

    july_flat_ids = {r["unit_id"] for r in units if flat(r.get("probabilities"))}
    scope = ("all simulated units" if args.units == "all"
             else "units the July instrument flattened")
    print("\n" + "=" * 92, flush=True)
    print(f"Degeneracy transfer over {len(units)} {scope}", flush=True)
    print(f"{'evaluator':<44}{'parsed':>10}{'flat':>10}{'modal':>8}"
          f"{'flat on the July-flat subset':>30}", flush=True)
    summary = {}
    for m in models:
        rs = [x for x in results if x["model"] == m]
        ok = [x for x in rs if x.get("parsed")]
        fl = sum(1 for x in ok if x["flat"])
        mm = (sum(x["modal"] for x in ok) / len(ok)) if ok else float("nan")
        sub = [x for x in ok if x["unit_id"] in july_flat_ids]
        sub_fl = sum(1 for x in sub if x["flat"])
        summary[m] = {"n": len(rs), "parsed": len(ok), "flat": fl,
                      "flat_rate": fl / len(ok) if ok else None, "mean_modal": mm,
                      "july_flat_subset_n": len(sub), "july_flat_subset_flat": sub_fl}
        print(f"{m:<44}{len(ok):>5}/{len(rs):<4}{fl:>5}/{len(ok):<4}{mm:>8.3f}"
              f"{sub_fl:>25}/{len(sub):<4}", flush=True)
    # the July instrument's own row, computed rather than assumed
    j_flat = len(july_flat_ids)
    print(f"{'DeepSeek-R1-14B, local (the July instrument)':<44}"
          f"{len(units):>5}/{len(units):<4}{j_flat:>5}/{len(units):<4}"
          f"{'--':>8}{j_flat:>25}/{j_flat:<4}", flush=True)
    summary["_july_instrument"] = {"n": len(units), "parsed": len(units), "flat": j_flat,
                                   "flat_rate": j_flat / len(units)}

    OUT.write_text(json.dumps({"units": args.units, "n_units": len(units),
                               "summary": summary, "detail": results}, indent=2),
                   encoding="utf-8")
    print(f"\nwrote {OUT.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
