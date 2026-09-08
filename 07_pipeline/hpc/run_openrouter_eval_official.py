#!/usr/bin/env python3
"""
Official OpenRouter Evaluator Script for ECN-BENCH.
Targeted evaluation over specific missing/faulty event units across all 4 models,
with concurrent (thread-pooled) requests since each call is I/O-bound.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

backend_dir = Path(__file__).resolve().parent / "MiroFish-Offline" / "backend"
if not backend_dir.exists():
    backend_dir = Path(__file__).resolve().parent.parent / "MiroFish-Offline" / "backend"
sys.path.insert(0, str(backend_dir))

from app.benchmarks.evaluator import ProbabilityEvaluator
from app.benchmarks.role_router import BenchmarkRoleRouter

# Single source of truth for recomputing a row's probability-derived metrics, shared
# with the dataset reconciliation utility so both agree by construction.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from separate_evaluator_datasets import rescore  # noqa: E402

# Campaign directories, relative to --base-workspace-dir (pass the repo root,
# Claw-4-FUN). The results file inside each is chosen by --results-filename, which
# defaults to the August replication pass rather than event_results.json: the latter
# is the July pass reproducing each campaign's summary.json and is the primary data
# behind the manuscript, so re-evaluating into it would overwrite published results.
DEFAULT_MODEL_DIRS = {
    "Llama-3.1-8B-AWQ": "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
    "Mistral-7B-AWQ": "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z",
    "Qwen2.5-7B": "completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z",
    # 2026-08-14: repointed from the old ECN-HPC-DEPLOY/ecnbench_workspace/... path
    # (still on disk, kept as raw audit trail) to the cleaned, rescored campaign --
    # 72/90 units (24/30 events); 6 events (T3,T4,T5,T6,C6,T8) were excluded because
    # they were simulated against the wrong event topic (stale events_raw.json
    # catalogue collision). See completed_benches/qwen2.5-14b-awq/.../summary.json's
    # "_exclusion_note" and excluded_events_wrong_topic.json for details.
    "Qwen2.5-14B": "completed_benches/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete",
}

# event_results.json is write-protected here: overwriting it destroys the manuscript's
# primary data, and because this script updates `probabilities` without recomputing
# brier/rps/directional_*/calibration_*, the damage is silent -- the file stays
# well-formed and passes the pipeline's completeness checks while its stored metrics
# describe probability vectors the records no longer contain. Pass
# --allow-july-overwrite only with a deliberate reason.
PROTECTED_RESULTS_FILENAME = "event_results.json"

# Specific faulty/missing units summary for quick reference
FAULTY_UNITS_SUMMARY = {
    "Llama-3.1-8B-AWQ": ["S3_A_r1", "T1_A_r1", "C7_A_r1"],
    "Mistral-7B-AWQ": ["S3_A_r1", "S7_B_r1", "S7_C_r1", "T1_A_r1", "C7_A_r1"],
    "Qwen2.5-7B": ["S3_A_r1", "T1_A_r1", "C7_A_r1", "C8_B_r1"],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Official OpenRouter Evaluator Script for ECN-BENCH."
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("OPENROUTER_API_KEY", ""),
        help="OpenRouter API Key (sk-or-v1-...). Defaults to OPENROUTER_API_KEY env var.",
    )
    parser.add_argument(
        "--evaluator-model",
        type=str,
        default="deepseek/deepseek-r1",
        help="Evaluator model on OpenRouter (e.g. deepseek/deepseek-r1, deepseek/deepseek-chat, openai/gpt-4o-mini).",
    )
    parser.add_argument(
        "--target-model",
        type=str,
        default="ALL",
        choices=["ALL", "Llama-3.1-8B-AWQ", "Mistral-7B-AWQ", "Qwen2.5-7B", "Qwen2.5-14B"],
        help="Target model to evaluate.",
    )
    parser.add_argument(
        "--events",
        type=str,
        default="",
        help="Optional comma-separated list of specific event IDs to evaluate (e.g. 'S3,T1,C7,C8'). Leave empty for automatic faulty unit detection.",
    )
    parser.add_argument(
        "--events-raw-path",
        type=str,
        default="data/events_raw.json",
        help="Path to events_raw.json file.",
    )
    parser.add_argument(
        "--base-workspace-dir",
        type=str,
        default=".",
        help="Base directory containing model event_results.json files.",
    )
    parser.add_argument(
        "--results-filename",
        type=str,
        default="event_results_evaluatorB_openrouter.json",
        help="Results file to read and update inside each campaign directory. Defaults to "
        "the August replication pass. 'event_results.json' is refused unless "
        "--allow-july-overwrite is passed, since that file is the manuscript's primary data.",
    )
    parser.add_argument(
        "--allow-july-overwrite",
        action="store_true",
        help="Permit writing to event_results.json. Only for a deliberate re-scoring of the "
        "July pass; note this script does not recompute derived metrics for rows it rewrites "
        "unless --rescore is also on (it is on by default).",
    )
    parser.add_argument(
        "--no-rescore",
        action="store_true",
        help="Do not recompute brier/rps/directional_*/calibration_* for updated rows. Leaves "
        "the file internally inconsistent; use only to reproduce the pre-fix behaviour.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=6,
        help="Number of units to evaluate in parallel per model (thread pool). "
        "Each call is I/O-bound (network), so this is safe to raise; the "
        "underlying client already retries 429s/timeouts with backoff. Start "
        "around 6-10 and raise if you aren't seeing rate-limit errors.",
    )
    return parser.parse_args()


def process_model(
    model_name: str,
    rel_dir: str,
    results_filename: str,
    base_dir: Path,
    events_by_id: dict,
    evaluator: ProbabilityEvaluator,
    target_event_ids: set[str] | None,
    concurrency: int = 1,
    rescore_rows: bool = True,
):
    rel_path = f"{rel_dir}/{results_filename}"
    full_path = base_dir / rel_path
    if not full_path.exists():
        waves_path = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr") / rel_path
        if waves_path.exists():
            full_path = waves_path
        else:
            print(f"\n[SKIP] Target file not found for {model_name}: {full_path}")
            return

    print(f"\n==================================================")
    print(f"PROCESSING MODEL: {model_name}")
    print(f"Target File: {full_path}")

    data = json.loads(full_path.read_text(encoding="utf-8"))
    total_units = len(data)

    target_indices: list[int] = []
    for idx, row in enumerate(data):
        event_id = row.get("event_id")
        is_fallback = row.get("evaluator_fallback_used", False)
        mcq = row.get("mcq_dimensions")
        micro = row.get("micro_epistemic_mapping")

        # Check if unit is faulty/missing
        is_faulty = (
            is_fallback
            or not isinstance(mcq, dict)
            or len(mcq) < 7
            or not isinstance(micro, dict)
            or len(micro) < 1
        )

        # Apply specific event filter if requested
        if target_event_ids:
            if event_id not in target_event_ids:
                continue
        else:
            # If no explicit event filter, process only faulty/missing units
            if not is_faulty:
                continue

        target_indices.append(idx)

    print(f"Units to evaluate: {len(target_indices)}/{total_units} (concurrency={concurrency})")
    if not target_indices:
        print(f"\nModel {model_name} complete: Evaluated 0 units.")
        return

    def evaluate_one(idx: int):
        """Runs in a worker thread. Only reads `data[idx]` -- each idx is only ever
        touched by exactly one worker, and mutation happens later under save_lock,
        so this needs no locking of its own."""
        row = data[idx]
        unit_id = row.get("unit_id", f"unit_{idx}")
        event_id = row.get("event_id")
        condition = row.get("condition")
        event_obj = events_by_id.get(event_id, {})
        # Reuse the row's OWN stored, condition-specific evidence/question/options --
        # events_raw.json has no "evidence" field at all, so falling back to it would
        # silently score every unit against empty evidence.
        event_q = row.get("question") or event_obj.get("question", "What is the outcome?")
        evidence = row.get("evidence_text") or ""
        options = row.get("options") or event_obj.get("options", ["YES", "NO"])
        micro_qs = event_obj.get("micro_questions", [])
        try:
            eval_res = evaluator.evaluate(
                event_question=event_q,
                condition=condition,
                evidence_text=evidence,
                options=options,
                micro_questions=micro_qs,
                event=event_obj,
            )
            return idx, unit_id, event_id, condition, eval_res, None
        except Exception as exc:  # noqa: BLE001 - reported to the caller, not swallowed
            return idx, unit_id, event_id, condition, None, exc

    # save_lock serializes: (a) mutating the shared `data` list, (b) writing the
    # whole file to disk. Without it, two worker threads finishing at nearly the
    # same time could interleave writes and corrupt event_results.json, or one
    # completed unit's write could clobber another's.
    save_lock = threading.Lock()
    done = 0
    repaired = 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(evaluate_one, idx) for idx in target_indices]
        for future in as_completed(futures):
            idx, unit_id, event_id, condition, eval_res, exc = future.result()
            with save_lock:
                done += 1
                prefix = f"  [{done}/{len(target_indices)}]"
                if exc is not None:
                    print(f"{prefix} [ERROR] Unit {unit_id} (Event: {event_id}, Condition: {condition}): {exc}")
                    continue

                data[idx]["probabilities"] = eval_res.get("probabilities")
                data[idx]["mcq_dimensions"] = eval_res.get("mcq_dimensions")
                data[idx]["validated_scales"] = eval_res.get("validated_scales")
                data[idx]["micro_epistemic_mapping"] = eval_res.get("micro_epistemic_mapping")
                data[idx]["evaluator_fallback_used"] = False
                data[idx]["evaluation_status"] = "completed"

                # A new probability vector invalidates every metric derived from the old
                # one. Recomputing here keeps the row self-consistent; skipping it is what
                # previously left 82-88 of 90 units per campaign with a stored brier that
                # described a vector the record no longer held.
                if rescore_rows:
                    data[idx] = rescore(data[idx])

                repaired += 1

                print(f"{prefix} [SUCCESS OpenRouter] Unit {unit_id} (Event: {event_id}, Condition: {condition})")
                print(f"      Probabilities: {eval_res.get('probabilities')}")

                # Atomic incremental save, serialized by save_lock.
                full_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nModel {model_name} complete: Evaluated {repaired}/{len(target_indices)} units.")


def main():
    args = parse_args()

    if not args.api_key:
        print("[ERROR] OpenRouter API Key required. Pass --api-key sk-or-v1-... or set OPENROUTER_API_KEY env var.")
        sys.exit(1)

    if args.results_filename == PROTECTED_RESULTS_FILENAME and not args.allow_july_overwrite:
        print(
            f"[ERROR] Refusing to write to {PROTECTED_RESULTS_FILENAME}: it is the July "
            f"evaluator pass and the manuscript's primary data.\n"
            f"        Re-evaluate into the replication pass instead (the default), or pass\n"
            f"        --allow-july-overwrite if you really intend to rewrite the July results."
        )
        sys.exit(1)

    # Evaluator endpoint is wired directly into BenchmarkRoleRouter below (not via env
    # vars -- BenchmarkRoleRouter.from_config() reads OPENROUTER_*, not the
    # BENCHMARK_ROLE_EVALUATOR_* names this script used to set, so those never took effect).
    openrouter_url = "https://openrouter.ai/api/v1"
    os.environ["BENCHMARK_MODE"] = "True"
    os.environ["HEADLESS_MODE"] = "True"

    events_raw_path = Path(args.events_raw_path)
    if not events_raw_path.exists():
        # Repo-root data/events_raw.json, NOT the sibling ECN-HPC-DEPLOY/data/ copy:
        # that copy is a stale catalogue whose T3/T4/T6/C6/T8 entries hold entirely
        # different events under the same ids, so its micro_questions get attached to
        # the wrong event. Verified against the campaign records: repo-root agrees on
        # all 30 ground truths, the nested copy disagrees on 5.
        events_raw_path = Path(__file__).resolve().parent.parent / "data" / "events_raw.json"

    if not events_raw_path.exists():
        print(f"[ERROR] events_raw.json not found at {events_raw_path}")
        sys.exit(1)

    target_events = set(e.strip() for e in args.events.split(",") if e.strip()) if args.events else None

    print("=== OFFICIAL OPENROUTER EVALUATOR STARTED ===")
    print(f"OpenRouter URL: {openrouter_url}")
    print(f"Evaluator Model: {args.evaluator_model}")
    print(f"Target Model: {args.target_model}")
    if target_events:
        print(f"Target Specific Events: {target_events}")
    else:
        print(f"Target Mode: Automatic Fast Faulty/Missing Unit Repair")

    # events_raw.json is a nested dict (core_events -> category -> [events],
    # supplementary_events -> events -> [events]), keyed by "id" not "event_id".
    raw_events = json.loads(events_raw_path.read_text(encoding="utf-8"))
    events_by_id: dict = {}
    for category_events in raw_events.get("core_events", {}).values():
        for e in category_events:
            events_by_id[e["id"]] = e
    for e in raw_events.get("supplementary_events", {}).get("events", []):
        events_by_id[e["id"]] = e

    # graph_model/benchmark_model are required by BenchmarkRoleRouter's validation but
    # are never actually used here -- ProbabilityEvaluator only calls
    # client_for("evaluator"), so any non-empty placeholder is safe.
    router = BenchmarkRoleRouter(
        api_key=args.api_key,
        base_url=openrouter_url,
        graph_model=args.evaluator_model,
        benchmark_model=args.evaluator_model,
        evaluator_model=args.evaluator_model,
        evaluator_base_url=openrouter_url,
    )
    evaluator = ProbabilityEvaluator(router)
    base_dir = Path(args.base_workspace_dir)

    targets = (
        DEFAULT_MODEL_DIRS.items()
        if args.target_model == "ALL"
        else [(args.target_model, DEFAULT_MODEL_DIRS[args.target_model])]
    )
    for m_name, rel_dir in targets:
        process_model(
            m_name,
            rel_dir,
            args.results_filename,
            base_dir,
            events_by_id,
            evaluator,
            target_events,
            args.concurrency,
            rescore_rows=not args.no_rescore,
        )

    print("\n=== OPENROUTER EVALUATION RUN COMPLETED ===")


if __name__ == "__main__":
    main()
