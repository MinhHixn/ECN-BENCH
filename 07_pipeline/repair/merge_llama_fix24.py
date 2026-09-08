#!/usr/bin/env python
"""Assemble the corrected Llama-3.1-8B campaign from the 2026-08-16 re-scoring.

What goes where
---------------
For each of the campaign's six evaluator files, the 24 repaired events get:

  Condition B, C  <- the matching fix24 pass (real simulation, real evidence,
                     root catalogue), scored 2026-08-16
  Condition A     <- RESTORED from the pre-repair snapshot. Condition A is the
                     No-Sim baseline: it has no simulation to re-read, and it is a
                     record shared byte-for-byte across all three campaigns. The
                     2026-08-16 repair overwrote it only because its merge filtered
                     on event_id without filtering on condition; restoring it puts
                     Llama back on the same reference as Mistral and Qwen.

The 6 events the outage never touched (C3, S2, S3, S4, S5, S6) are left exactly
as they are in each file -- they are valid July local-vLLM data.

Every target file is backed up to archive_pre_session_repairs/ with a timestamp
before being written. Use --dry-run first.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMP = HERE / "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z"
ARCHIVE = CAMP / "archive_pre_session_repairs"

PRE_JULY = ARCHIVE / "event_results.json.bak_20260813_192149"
PRE_AUGB = ARCHIVE / "event_results_evaluatorB_openrouter.json.bak_20260814_014554"

# target file -> (fix24 source for B/C, source for the restored Condition A)
PLAN = {
    "event_results.json":                        ("event_results_llama_fix24_primary.json",   PRE_JULY),
    "event_results_evaluatorB_openrouter.json":  ("event_results_llama_fix24_evaluatorB.json", PRE_AUGB),
    "event_results_evaluatorC_gptlunapro.json":  ("event_results_llama_fix24_evaluatorC.json", PRE_JULY),
    "event_results_evaluatorA_repeat1.json":     ("event_results_llama_fix24_repeat1.json",   PRE_JULY),
    "event_results_evaluatorA_repeat2.json":     ("event_results_llama_fix24_repeat2.json",   PRE_JULY),
    "event_results_evaluatorA_repeat3.json":     ("event_results_llama_fix24_repeat3.json",   PRE_JULY),
}
UNTOUCHED = {"C3", "S2", "S3", "S4", "S5", "S6"}


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    fix_events = None
    problems = []

    for target, (src_name, a_src) in PLAN.items():
        src_path = CAMP / src_name
        tgt_path = CAMP / target
        print("=" * 92)
        print(target)
        if not src_path.exists():
            problems.append(f"{target}: source {src_name} missing")
            print(f"  SKIP -- {src_name} not found")
            continue

        src = {(r["event_id"], r["condition"]): r for r in load(src_path)}
        pending = [k for k, r in src.items() if r.get("evaluator_fallback_used")]
        if pending:
            problems.append(f"{target}: {len(pending)} unscored rows in {src_name}")
            print(f"  SKIP -- {len(pending)} rows still unscored: {sorted(u[0]+'_'+u[1] for u in pending)[:8]}")
            continue

        evs = sorted({e for e, c in src})
        if fix_events is None:
            fix_events = evs
        elif evs != fix_events:
            problems.append(f"{target}: event set differs from the other passes")

        a_rows = {(r["event_id"], r["condition"]): r for r in load(a_src)}
        tgt_rows = load(tgt_path)

        n_bc = n_a = n_kept = 0
        out = []
        for row in tgt_rows:
            e, c = row["event_id"], row["condition"]
            if e in UNTOUCHED:
                out.append(row)
                n_kept += 1
                continue
            if c in ("B", "C") and (e, c) in src:
                merged = dict(src[(e, c)])
                merged["repeat"] = row.get("repeat", 1)
                out.append(merged)
                n_bc += 1
            elif c == "A" and (e, c) in a_rows:
                restored = dict(a_rows[(e, c)])
                restored["condition_a_restored"] = "shared_nosim_reference_2026-08-16"
                out.append(restored)
                n_a += 1
            else:
                out.append(row)
                n_kept += 1

        print(f"  B/C replaced from {src_name}: {n_bc}")
        print(f"  Condition A restored from {a_src.name}: {n_a}")
        print(f"  rows left as-is (6 untouched events): {n_kept}")

        # post-merge invariants
        bad_ev = [r["unit_id"] for r in out
                  if r["condition"] in ("B", "C") and r["event_id"] not in UNTOUCHED
                  and not (r.get("evidence_text") or "")]
        bad_q = [r["unit_id"] for r in out if not (r.get("question") or "")]
        bad_a = [r["unit_id"] for r in out
                 if r["condition"] == "A" and str(r.get("simulation_executed")) != "False"]
        for label, lst in (("B/C rows with empty evidence", bad_ev),
                           ("rows with empty question", bad_q),
                           ("Condition A rows flagged simulation_executed", bad_a)):
            if lst:
                problems.append(f"{target}: {label}: {lst[:6]}")
                print(f"  FAIL -- {label}: {len(lst)}")
        if not (bad_ev or bad_q or bad_a):
            print("  invariants OK (no empty evidence, no empty question, A is No-Sim)")

        if args.dry_run:
            print("  [dry-run] not written")
            continue
        ARCHIVE.mkdir(exist_ok=True)
        backup = ARCHIVE / f"{target}.bak_fix24_{stamp}"
        shutil.copy2(tgt_path, backup)
        tgt_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  written; previous version saved to {backup.name}")

    print("=" * 92)
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("all six files consistent" + (" (dry-run)" if args.dry_run else " and written"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
