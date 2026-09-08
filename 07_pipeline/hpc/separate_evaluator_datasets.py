#!/usr/bin/env python3
"""Split the hybrid event_results.json files back into two internally consistent datasets.

Background
----------
The July 2026 campaigns scored every unit with a local DeepSeek-R1-14B evaluator and
wrote `probabilities` together with the derived metrics computed from them
(brier/rps/directional_*/calibration_*). The August 2026 OpenRouter re-evaluation
(run_openrouter_eval_official.py) overwrote `probabilities`, `mcq_dimensions`,
`validated_scales` and `micro_epistemic_mapping` but left every derived metric at its
July value. The result is a file where `brier` no longer corresponds to
`probabilities` in the same record (82-88 of 90 units per campaign).

This script restores a clean separation:

  event_results.json                      <- Dataset J: the pristine July campaign
                                             (byte-restored from the .bak snapshot;
                                             reproduces summary.json exactly)
  event_results_evaluatorB_openrouter.json <- Dataset A: the August re-evaluation with
                                             every derived metric RECOMPUTED from the
                                             August probabilities using the pipeline's
                                             own scoring functions
  event_results.json.hybrid_<ts>          <- the inconsistent hybrid, kept for audit

Nothing is deleted. Run with --dry-run first to see what would change.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "MiroFish-Offline" / "backend"))

from app.benchmarks.scoring import brier_score  # noqa: E402
from app.benchmarks.statistics import (  # noqa: E402
    assign_probability_bracket,
    ranked_probability_score,
)

# campaign dir -> the .bak snapshot holding the pristine July data
CAMPAIGNS = {
    "Llama-3.1-8B-AWQ": (
        "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
        "event_results.json.bak_20260813_192149",
    ),
    "Mistral-7B-AWQ": (
        "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z",
        "event_results.json.bak_20260813_192149",
    ),
    "Qwen2.5-7B": (
        "completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z",
        "event_results.json.bak_20260813_185718",
    ),
    "Qwen2.5-14B": (
        "ECN-HPC-DEPLOY/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete",
        "event_results.json.bak_20260813_192149",
    ),
}


def rescore(row: dict) -> dict:
    """Return a copy of `row` with every probability-derived metric recomputed.

    Uses the same functions the HPC protocol runner uses, so the numbers are
    directly comparable with the July campaign rather than an independent
    reimplementation.
    """
    out = dict(row)
    probs = row.get("probabilities")
    gt = row.get("ground_truth")
    if not isinstance(probs, dict) or not probs or not gt:
        # Nothing to score against (e.g. Qwen2.5-14B units carry no ground_truth):
        # blank the derived fields rather than leave July values that describe a
        # different probability vector.
        for key in (
            "brier", "rps", "directional_accuracy", "directional_correct",
            "calibration_bracket", "calibration_predicted_probability",
            "calibration_hit", "yes_probability",
        ):
            out[key] = None
        return out

    options = row.get("options") or sorted(probs.keys())
    out["brier"] = brier_score(probs, gt)

    try:
        gt_label = gt if gt in options else next(
            (o for o in options if o.casefold() == str(gt).casefold()), gt
        )
        out["rps"] = ranked_probability_score(probs, gt_label, options)
    except ValueError:
        out["rps"] = None

    peak = max(probs.values())
    tied = [k for k, v in probs.items() if math.isclose(v, peak, abs_tol=1e-12)]
    if len(tied) == 1:
        correct = int(tied[0].casefold() == str(gt).casefold())
        out["directional_correct"] = correct
        out["directional_accuracy"] = float(correct)
        out["calibration_hit"] = correct
    else:
        # A tie is not a prediction: the protocol runner records 0.5 and leaves
        # directional_correct unset.
        out["directional_correct"] = None
        out["directional_accuracy"] = 0.5
        out["calibration_hit"] = int(any(t.casefold() == str(gt).casefold() for t in tied))

    out["calibration_predicted_probability"] = peak
    out["calibration_bracket"] = assign_probability_bracket(peak)

    scores = (row.get("validated_scales") or {}).get("scores") or {}
    if "weighted_rubric_score" in scores:
        out["weighted_rubric_score"] = scores["weighted_rubric_score"]

    yes = probs.get("YES", probs.get("Yes", probs.get("yes")))
    out["yes_probability"] = float(yes) if isinstance(yes, (int, float)) else None

    return out


def consistency(rows: list[dict]) -> tuple[int, int]:
    """(consistent, scorable) — does stored brier match brier(probabilities)?"""
    ok = total = 0
    for r in rows:
        p, gt = r.get("probabilities"), r.get("ground_truth")
        if not p or not gt or r.get("brier") is None:
            continue
        total += 1
        if abs(brier_score(p, gt) - r["brier"]) < 1e-6:
            ok += 1
    return ok, total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verb = "WOULD" if args.dry_run else "will"

    for name, (rel, bak) in CAMPAIGNS.items():
        d = REPO / rel
        current, backup = d / "event_results.json", d / bak
        print(f"=== {name} ===")
        if not backup.exists():
            print(f"  SKIP: July snapshot missing ({bak})")
            continue

        july = json.loads(backup.read_text(encoding="utf-8"))
        hybrid = json.loads(current.read_text(encoding="utf-8"))

        jok, jtot = consistency(july)
        hok, htot = consistency(hybrid)
        print(f"  July snapshot   : {jok}/{jtot} units internally consistent")
        print(f"  Current (hybrid): {hok}/{htot} units internally consistent")

        # Dataset A = August probabilities + freshly recomputed derived metrics.
        rescored = [rescore(r) for r in hybrid]
        aok, atot = consistency(rescored)
        print(f"  Rescored dataset A: {aok}/{atot} units internally consistent")

        out_a = d / "event_results_evaluatorB_openrouter.json"
        keep = d / f"event_results.json.hybrid_{stamp}"
        print(f"  {verb} keep hybrid   -> {keep.name}")
        print(f"  {verb} write dataset A-> {out_a.name}")
        print(f"  {verb} restore July   -> event_results.json")

        if not args.dry_run:
            shutil.copy2(current, keep)
            out_a.write_text(json.dumps(rescored, ensure_ascii=False, indent=2), encoding="utf-8")
            shutil.copy2(backup, current)
        print()

    print("Done." if not args.dry_run else "Dry run complete - nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
