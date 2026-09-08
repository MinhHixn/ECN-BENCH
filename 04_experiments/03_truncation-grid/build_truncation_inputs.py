#!/usr/bin/env python
"""Build the evidence-truncation grid for the volume dose-response experiment.

Section~\\ref{sec:volume_mechanism} argues that the *amount* of evidence an
unconstrained evaluator must compress is what drives degenerate (exactly uniform)
forecasts. That argument currently rests on natural terciles of Mistral-7B's
evidence length, which is an observational contrast: long transcripts might differ
from short ones in kind as well as in size.

This script makes the manipulation experimental. It takes Mistral-7B's 60 simulated
units -- the one campaign in which evidence length varies without also varying
whether deliberation occurred -- and produces, for each unit, the *same* transcript
truncated to several target lengths. Scoring the grid under a fixed evaluator turns
"long transcripts happen to be flat" into "shortening this transcript un-flattens it".

Truncation preserves the structure of the record rather than cutting it off. Each
`evidence_text` is `"Simulation high-level log tail:\\n<log>\\n\\nRepresentative Social
Media Actions (Sample):\\n<one line per action>"`. We keep both sections and both
headers at every level, retaining the *last* f of the log's lines (the tail is what
the pipeline itself keeps) and a uniformly spaced f-subsample of the action lines,
with f found by bisection so the total lands on the target. So the levels differ in
how much of each section is present, not in which sections are present: the actions
block is 84-94% of the characters at every level.

What this does NOT isolate, and we do not claim it does: reducing how much transcript
is shown necessarily reduces how many distinct voices are shown with it. The median
number of distinct speakers visible in the actions block falls 44 -> 29 -> 20 -> 9
across untruncated -> 8k -> 5k -> 2k. So the manipulation varies "amount of
deliberation shown" as a bundle -- characters, speakers, distinct claims -- exactly
as the natural length variation across units does. It converts an observational
contrast into an experimental one; it does not decompose the bundle. Isolating raw
character count would need padding with semantically null filler at a fixed speaker
count, which is a different experiment.

Usage:
    python build_truncation_inputs.py                 # writes the input files
    python build_truncation_inputs.py --report        # length/flat table only
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z"
SOURCE = CAMPAIGN / "event_results.json"

ACTIONS_HEADER = "Representative Social Media Actions (Sample):"
LOG_HEADER = "Simulation high-level log tail:"
LEVELS = [2000, 5000, 8000]          # plus the untruncated control, written as "full"
# Arms are (evaluator tag, enforcement) pairs. The evaluator that actually degenerates
# is qwen3-14b -- deepseek-r1 never returns a uniform vector, so a length titration
# under it has nothing to titrate and serves only as a negative control.
ARMS = ["unconstrained", "enforced", "q14b_unconstrained", "q14b_enforced"]


def split_evidence(text: str) -> tuple[str, str]:
    """-> (log section including its header, actions section including its header)."""
    i = text.find(ACTIONS_HEADER)
    if i < 0:
        return text, ""
    return text[:i], text[i:]


def _keep_tail_lines(body: str, frac: float) -> str:
    lines = body.split("\n")
    k = max(1, round(len(lines) * frac))
    return "\n".join(lines[-k:])


def _subsample_lines(body: str, frac: float) -> str:
    lines = [l for l in body.split("\n") if l]
    if not lines:
        return ""
    k = max(1, round(len(lines) * frac))
    if k >= len(lines):
        return "\n".join(lines)
    # uniformly spaced, deterministic, endpoints included
    idx = [round(i * (len(lines) - 1) / (k - 1)) for i in range(k)] if k > 1 else [0]
    return "\n".join(lines[i] for i in sorted(set(idx)))


def truncate(text: str, target: int) -> str:
    """Shrink `text` to about `target` characters, keeping both sections."""
    if len(text) <= target:
        return text
    log_sec, act_sec = split_evidence(text)
    log_body = log_sec[len(LOG_HEADER):].lstrip("\n") if log_sec.startswith(LOG_HEADER) else log_sec
    act_body = act_sec[len(ACTIONS_HEADER):].lstrip("\n") if act_sec else ""

    def build(f: float) -> str:
        parts = [LOG_HEADER, _keep_tail_lines(log_body, f)]
        if act_body:
            parts += ["", ACTIONS_HEADER, _subsample_lines(act_body, f)]
        return "\n".join(parts)

    lo, hi = 0.0, 1.0
    best = build(1.0)
    for _ in range(40):
        mid = (lo + hi) / 2
        cand = build(mid)
        if len(cand) > target:
            hi = mid
        else:
            lo = mid
            best = cand
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="print the grid, write nothing")
    args = ap.parse_args()

    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    sim = [r for r in rows if r.get("condition") in ("B", "C")]
    assert len(sim) == 60, len(sim)

    def flat(r):
        p = r.get("probabilities") or {}
        return bool(p) and max(abs(v - 1.0 / len(p)) for v in p.values()) < 0.005

    print(f"source        {SOURCE.relative_to(HERE)}")
    print(f"simulated units {len(sim)}   flat under the July evaluator "
          f"{sum(map(flat, sim))}/{len(sim)}")
    lens = sorted(len(r.get("evidence_text") or "") for r in sim)
    print(f"evidence chars  min {lens[0]}  median {lens[len(lens)//2]}  max {lens[-1]}")
    print()

    for level in ["full"] + LEVELS:
        out = []
        realised = []
        for r in sim:
            new = dict(r)
            src = r.get("evidence_text") or ""
            new["evidence_text"] = src if level == "full" else truncate(src, level)
            realised.append(len(new["evidence_text"]))
            # clear the stored verdict so a stale value can never be mistaken for a re-read
            for k in ("probabilities", "brier_score", "rps", "mcq_dimensions",
                      "micro_epistemic_mapping", "validated_scales"):
                new.pop(k, None)
            new["evaluator_fallback_used"] = True     # marks every unit as needing a read
            new["truncation_level"] = level
            out.append(new)
        tag = level if level == "full" else f"{level//1000}k"
        print(f"  level {tag:>4}: realised chars "
              f"min {min(realised)}  median {sorted(realised)[len(realised)//2]}  "
              f"max {max(realised)}")
        if args.report:
            continue
        for arm in ARMS:
            p = CAMPAIGN / f"event_results_trunc_{tag}_{arm}.json"
            # never clobber a cell that already carries scored units: the runner writes
            # its results back into this same file, and regenerating it would silently
            # discard them (and the API spend that produced them).
            if p.exists():
                existing = json.loads(p.read_text(encoding="utf-8"))
                scored = sum(1 for r in existing if r.get("probabilities"))
                if scored:
                    print(f"           kept  {p.name}  ({scored} units already scored)")
                    continue
            p.write_text(json.dumps(out, indent=2), encoding="utf-8")
            print(f"           wrote {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
