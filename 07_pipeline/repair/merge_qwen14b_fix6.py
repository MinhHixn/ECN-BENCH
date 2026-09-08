#!/usr/bin/env python
"""Merge the 6 recovered Qwen2.5-14B events (T3, T4, T5, T6, C6, T8) into the
canonical 24-event campaign files, bringing each to the full 30 events (90 rows).

Root cause and recovery, briefly
---------------------------------
These 6 events were originally excluded because they were simulated against the
wrong topic (stale ECN-HPC-DEPLOY/data/events_raw.json catalogue collision). The
2026-08-20 re-simulation attempt reproduced the exact same bug (verified: T3 was
simulated as "Bitcoin $80k/$100k" instead of "2024 Taiwanese presidential
election"). Re-simulated 2026-08-21 with --events-raw pointed at
ecnbench_workspace/fix7_rootcat/data/ (the authoritative catalogue already staged
there during the 2026-08-16 Llama repair), split into two parallel SLURM jobs
(T3/T4/T5 and T6/C6/T8) to fit the 2-GPU-per-user QOS cap. All 18 units (6 events
x 3 conditions) completed 300 agents x 60 rounds with correct topics verified
against the root catalogue.

Scored 2026-08-21 in 5 passes mirroring the Llama fix24 recipe: primary
deepseek/deepseek-r1 (substitute for the unreachable local DeepSeek-R1-14B),
evaluatorA repeat1-3 deepseek/deepseek-v4-flash-0731, evaluatorC
openai/gpt-5.6-luna-pro. Unlike Llama, Condition A for these 6 events also needed
fresh scoring (not restoration) since it was invalid too, not merely overwritten.

Every target file is backed up to archive_pre_session_repairs/ before being
written. Use --dry-run first.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMP = HERE / "completed_benches/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete"
ARCHIVE = CAMP / "archive_pre_session_repairs"
DOWNLOADED = HERE / "scratch/qwen14b_fix6_downloaded"

RECOVERED_EVENTS = {"T3", "T4", "T5", "T6", "C6", "T8"}

# target file -> source of the 18 new rows
PLAN = {
    "event_results.json": "event_results_qwen14b_fix6_primary.json",
    "event_results_evaluatorA_repeat1.json": "event_results_qwen14b_fix6_repeat1.json",
    "event_results_evaluatorA_repeat2.json": "event_results_qwen14b_fix6_repeat2.json",
    "event_results_evaluatorA_repeat3.json": "event_results_qwen14b_fix6_repeat3.json",
    "event_results_evaluatorC_gptlunapro.json": "event_results_qwen14b_fix6_evaluatorC.json",
}


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    problems = []

    for target, src_name in PLAN.items():
        src_path = DOWNLOADED / src_name
        tgt_path = CAMP / target
        print("=" * 92)
        print(target)
        if not src_path.exists():
            problems.append(f"{target}: source {src_name} missing")
            print(f"  SKIP -- {src_name} not found")
            continue

        new_rows = load(src_path)
        if len(new_rows) != 18:
            problems.append(f"{target}: expected 18 new rows, got {len(new_rows)}")
        pending = [r["unit_id"] for r in new_rows if r.get("evaluator_fallback_used")]
        if pending:
            problems.append(f"{target}: {len(pending)} unscored rows in {src_name}: {pending}")
            print(f"  SKIP -- unscored rows: {pending}")
            continue
        new_events = sorted({r["event_id"] for r in new_rows})
        if set(new_events) != RECOVERED_EVENTS:
            problems.append(f"{target}: recovered event set mismatch: {new_events}")

        existing_rows = load(tgt_path)
        existing_events = sorted({r["event_id"] for r in existing_rows})
        overlap = RECOVERED_EVENTS & set(existing_events)
        if overlap:
            problems.append(f"{target}: recovered events already present in target: {overlap}")
            print(f"  SKIP -- already present: {overlap}")
            continue

        out = existing_rows + new_rows
        out.sort(key=lambda r: (r["event_id"], r["condition"], r.get("repeat", 1)))

        # post-merge invariants
        bad_ev = [r["unit_id"] for r in out
                  if r["condition"] in ("B", "C") and not (r.get("evidence_text") or "")]
        bad_q = [r["unit_id"] for r in out if not (r.get("question") or "")]
        bad_gt = [r["unit_id"] for r in out if not (r.get("ground_truth") or "")]
        bad_a = [r["unit_id"] for r in out
                 if r["condition"] == "A" and r.get("simulation_executed") is not False]
        bad_fallback = [r["unit_id"] for r in out if r.get("evaluator_fallback_used")]
        dupe_ids = [uid for uid in {r["unit_id"] for r in out}
                    if sum(1 for r in out if r["unit_id"] == uid) > 1]
        for label, lst in (
            ("B/C rows with empty evidence", bad_ev),
            ("rows with empty question", bad_q),
            ("rows with empty ground_truth", bad_gt),
            ("Condition A rows flagged simulation_executed", bad_a),
            ("rows still evaluator_fallback_used", bad_fallback),
            ("duplicate unit_ids", dupe_ids),
        ):
            if lst:
                problems.append(f"{target}: {label}: {lst[:6]}")
                print(f"  FAIL -- {label}: {len(lst)}")

        events_after = sorted({r["event_id"] for r in out})
        print(f"  existing rows: {len(existing_rows)} ({len(existing_events)} events)")
        print(f"  new rows added: {len(new_rows)} ({len(new_events)} events: {new_events})")
        print(f"  total after merge: {len(out)} rows ({len(events_after)} events)")
        if len(out) == 90 and len(events_after) == 30 and not (bad_ev or bad_q or bad_gt or bad_a or bad_fallback or dupe_ids):
            print("  invariants OK (90/90 rows, 30/30 events, no empty fields, A is No-Sim, no dupes)")

        if args.dry_run:
            print("  [dry-run] not written")
            continue
        ARCHIVE.mkdir(exist_ok=True)
        backup = ARCHIVE / f"{target}.bak_fix6_{stamp}"
        shutil.copy2(tgt_path, backup)
        tgt_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  written; previous version saved to {backup.name}")

    print("=" * 92)
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("all five files consistent" + (" (dry-run)" if args.dry_run else " and written"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
