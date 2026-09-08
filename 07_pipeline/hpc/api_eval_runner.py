#!/usr/bin/env python3
"""
Synchronous API-Based Evaluator Runner for Benchmark Scoring Across All 4 Models.
Connects directly to an external/remote LLM API (e.g. OpenRouter, DeepSeek API, OpenAI API)
to evaluate missing or fallback units for Llama-8B, Mistral-7B, Qwen-7B, and Qwen-14B.
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

DEFAULT_MODEL_PATHS = {
    "Llama-3.1-8B-AWQ": "ecnbench_workspace/simulation_logs/llama-3.1-8b-awq/ecnbench_20260811T211641407066Z/event_results.json",
    "Mistral-7B-AWQ": "ecnbench_workspace/simulation_logs/mistral-7b-awq/ecnbench_20260812T073651745891Z/event_results.json",
    "Qwen2.5-7B": "ecnbench_workspace/simulation_logs/qwen2.5_7b/ecnbench_20260812T085316759135Z/event_results.json",
    "Qwen2.5-14B": "ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/event_results.json",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run API-based synchronous evaluation across all 4 models."
    )
    parser.add_argument(
        "--api-base-url",
        type=str,
        required=True,
        help="Base URL for remote OpenAI-compatible API endpoint (e.g., https://openrouter.ai/api/v1 or https://api.deepseek.com/v1).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        required=True,
        help="API Key for the evaluator model service.",
    )
    parser.add_argument(
        "--evaluator-model",
        type=str,
        default="deepseek/deepseek-r1",
        help="Evaluator model identifier (e.g. deepseek/deepseek-r1 or deepseek-reasoner).",
    )
    parser.add_argument(
        "--events-raw-path",
        type=str,
        default="data/events_raw.json",
        help="Path to events_raw.json file.",
    )
    parser.add_argument(
        "--target-model",
        type=str,
        default="ALL",
        choices=["ALL", "Llama-3.1-8B-AWQ", "Mistral-7B-AWQ", "Qwen2.5-7B", "Qwen2.5-14B"],
        help="Target model to evaluate or ALL for all 4 models.",
    )
    parser.add_argument(
        "--base-workspace-dir",
        type=str,
        default=".",
        help="Base directory containing model event_results.json files.",
    )
    return parser.parse_args()


def process_model(model_name: str, rel_path: str, base_dir: Path, events_by_id: dict, evaluator: ProbabilityEvaluator):
    full_path = base_dir / rel_path
    if not full_path.exists():
        # Try absolute path fallback if base_dir relative fails
        waves_path = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr") / rel_path
        if waves_path.exists():
            full_path = waves_path
        else:
            print(f"[SKIP] Target file not found for {model_name}: {full_path}")
            return

    print(f"\n==================================================")
    print(f"PROCESSING MODEL: {model_name}")
    print(f"File: {full_path}")

    data = json.loads(full_path.read_text(encoding="utf-8"))
    total_units = len(data)
    repaired = 0

    for idx, row in enumerate(data):
        unit_id = row.get("unit_id", f"unit_{idx}")
        event_id = row.get("event_id")
        condition = row.get("condition")
        is_fallback = row.get("evaluator_fallback_used", False)
        mcq = row.get("mcq_dimensions")
        micro = row.get("micro_epistemic_mapping")

        needs_eval = (
            is_fallback
            or not isinstance(mcq, dict)
            or len(mcq) < 7
            or not isinstance(micro, dict)
            or len(micro) < 1
        )

        if not needs_eval:
            continue

        print(f"\n  [{idx+1}/{total_units}] Evaluating Unit: {unit_id} (Event: {event_id}, Condition: {condition})...")
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

            repaired += 1
            print(f"    [SUCCESS] Unit {unit_id} evaluated!")
            print(f"      Probabilities: {eval_res.get('probabilities')}")

            # Save after every unit for maximum reliability
            full_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"    [SAVED] Updated {full_path}")

        except Exception as exc:
            print(f"    [ERROR] Failed evaluating Unit {unit_id}: {exc}")

    print(f"\nModel {model_name} processing complete. Repaired {repaired} units.")


def main():
    args = parse_args()

    # Configure environment variables for API call
    os.environ["BENCHMARK_ROLE_EVALUATOR_BASE_URL"] = args.api_base_url
    os.environ["BENCHMARK_ROLE_EVALUATOR_MODEL"] = args.evaluator_model
    os.environ["BENCHMARK_ROLE_EVALUATOR_API_KEY"] = args.api_key
    os.environ["BENCHMARK_MODE"] = "True"
    os.environ["HEADLESS_MODE"] = "True"

    events_raw_path = Path(args.events_raw_path)
    if not events_raw_path.exists():
        events_raw_path = Path(__file__).resolve().parent / "data" / "events_raw.json"

    if not events_raw_path.exists():
        print(f"[ERROR] events_raw.json not found at {events_raw_path}")
        sys.exit(1)

    print("=== SYNCHRONOUS API EVALUATOR RUNNER STARTED ===")
    print(f"API Base URL: {args.api_base_url}")
    print(f"Evaluator Model: {args.evaluator_model}")
    print(f"Target Model(s): {args.target_model}")

    raw_events_list = json.loads(events_raw_path.read_text(encoding="utf-8"))
    events_by_id = {e["event_id"]: e for e in raw_events_list}

    router = BenchmarkRoleRouter()
    evaluator = ProbabilityEvaluator(router)
    base_dir = Path(args.base_workspace_dir)

    if args.target_model == "ALL":
        for m_name, rel_path in DEFAULT_MODEL_PATHS.items():
            process_model(m_name, rel_path, base_dir, events_by_id, evaluator)
    else:
        rel_path = DEFAULT_MODEL_PATHS[args.target_model]
        process_model(args.target_model, rel_path, base_dir, events_by_id, evaluator)

    print("\n=== ALL SYNCHRONOUS API EVALUATIONS COMPLETED ===")


if __name__ == "__main__":
    main()
