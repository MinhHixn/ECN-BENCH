#!/usr/bin/env python3
"""
Standalone Local Evaluator Runner for Single-Model Benchmark Evaluation.
Processes pre-existing simulation logs and updates event_results.json incrementally.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent / "MiroFish-Offline" / "backend"
sys.path.insert(0, str(backend_dir))

from app.benchmarks.evaluator import ProbabilityEvaluator
from app.benchmarks.router import BenchmarkRoleRouter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run local evaluation on single-model benchmark simulation logs."
    )
    parser.add_argument(
        "--event-results-path",
        type=str,
        required=True,
        help="Path to target event_results.json file to repair/evaluate.",
    )
    parser.add_argument(
        "--events-raw-path",
        type=str,
        default="data/events_raw.json",
        help="Path to events_raw.json file containing raw event questions & evidence.",
    )
    parser.add_argument(
        "--evaluator-base-url",
        type=str,
        default="http://localhost:11434/v1",
        help="Base URL for local OpenAI-compatible evaluator endpoint (e.g. Ollama or local vLLM).",
    )
    parser.add_argument(
        "--evaluator-model",
        type=str,
        default="deepseek-r1-14b",
        help="Model name for evaluator (e.g. deepseek-r1:14b or deepseek-r1-14b).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="EMPTY",
        help="API Key for evaluator endpoint.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Configure environment variables for BenchmarkRoleRouter & llm_client
    os.environ["BENCHMARK_ROLE_EVALUATOR_BASE_URL"] = args.evaluator_base_url
    os.environ["BENCHMARK_ROLE_EVALUATOR_MODEL"] = args.evaluator_model
    os.environ["BENCHMARK_ROLE_EVALUATOR_API_KEY"] = args.api_key
    os.environ["BENCHMARK_MODE"] = "True"
    os.environ["HEADLESS_MODE"] = "True"

    results_path = Path(args.event_results_path)
    if not results_path.exists():
        print(f"[ERROR] Target event_results.json not found: {results_path}")
        sys.exit(1)

    events_raw_path = Path(args.events_raw_path)
    if not events_raw_path.exists():
        # Try finding relative to project root
        events_raw_path = Path(__file__).resolve().parent / "data" / "events_raw.json"

    if not events_raw_path.exists():
        print(f"[ERROR] events_raw.json not found at {events_raw_path}")
        sys.exit(1)

    print(f"=== LOCAL EVALUATION RUNNER STARTED ===")
    print(f"Target file: {results_path}")
    print(f"Evaluator URL: {args.evaluator_base_url}")
    print(f"Evaluator Model: {args.evaluator_model}")

    # Load raw event definitions
    raw_events_list = json.loads(events_raw_path.read_text(encoding="utf-8"))
    events_by_id = {e["event_id"]: e for e in raw_events_list}

    # Initialize evaluator
    router = BenchmarkRoleRouter()
    evaluator = ProbabilityEvaluator(router)

    # Load target event_results.json
    data = json.loads(results_path.read_text(encoding="utf-8"))
    total_units = len(data)
    
    repaired_count = 0
    skipped_count = 0

    for idx, row in enumerate(data):
        unit_id = row.get("unit_id", f"unit_{idx}")
        event_id = row.get("event_id")
        condition = row.get("condition")
        is_fallback = row.get("evaluator_fallback_used", False)
        mcq = row.get("mcq_dimensions")
        micro = row.get("micro_epistemic_mapping")

        # Determine if unit needs evaluation/repair
        needs_eval = (
            is_fallback
            or not isinstance(mcq, dict)
            or len(mcq) < 7
            or not isinstance(micro, dict)
            or len(micro) < 1
        )

        if not needs_eval:
            skipped_count += 1
            continue

        print(f"\n[{idx+1}/{total_units}] Evaluating Unit: {unit_id} (Event: {event_id}, Condition: {condition})...")
        event_obj = events_by_id.get(event_id, {})
        event_q = event_obj.get("question", "What is the outcome?")
        evidence = event_obj.get("evidence", "")
        options = event_obj.get("options", ["YES", "NO"])
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

            # Update row in-place
            data[idx]["probabilities"] = eval_res.get("probabilities")
            data[idx]["mcq_dimensions"] = eval_res.get("mcq_dimensions")
            data[idx]["validated_scales"] = eval_res.get("validated_scales")
            data[idx]["micro_epistemic_mapping"] = eval_res.get("micro_epistemic_mapping")
            data[idx]["evaluator_fallback_used"] = False
            data[idx]["evaluation_status"] = "completed"

            repaired_count += 1
            print(f"  [SUCCESS] Unit {unit_id} evaluated!")
            print(f"    Probabilities: {eval_res.get('probabilities')}")
            print(f"    MCQ Dimensions: {eval_res.get('mcq_dimensions')}")

            # Incremental persistence after every evaluated unit
            results_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  [SAVED] Incremental save to {results_path}")

        except Exception as exc:
            print(f"  [ERROR] Failed evaluating Unit {unit_id}: {exc}")

    print(f"\n=== LOCAL EVALUATION COMPLETED ===")
    print(f"Total units: {total_units}")
    print(f"Units evaluated/repaired: {repaired_count}")
    print(f"Units skipped (already valid): {skipped_count}")


if __name__ == "__main__":
    main()
