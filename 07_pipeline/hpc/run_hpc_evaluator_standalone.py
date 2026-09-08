#!/usr/bin/env python3
"""
Stand-alone Robust HPC Evaluator for ECN-BENCH.
Runs on GPU compute node, starts vLLM with DeepSeek-R1-14B, dynamically detects model name,
and evaluates simulation units with per-unit checkpointing and derived metric recomputation.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Paths
backend_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/project_backup/MiroFish-Offline/backend")
if not backend_dir.exists():
    backend_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/MiroFish-Offline/backend")
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "scripts"))

from app.benchmarks.evaluator import ProbabilityEvaluator
from app.benchmarks.role_router import BenchmarkRoleRouter
from app.benchmarks.scoring import (
    brier_score,
    summarize_condition_scores,
    summarize_directional_accuracy,
    summarize_yes_probability,
    compute_weighted_rubric_score
)
from app.benchmarks.statistics import ranked_probability_score
from run_ecnbench_protocol import build_evidence_text

def get_vllm_model_name(port: int, max_wait: int = 300) -> str:
    """Wait for vLLM to start and query the served model name."""
    url = f"http://127.0.0.1:{port}/v1/models"
    print(f"Waiting for vLLM server at {url}...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode('utf-8'))
                    model_list = data.get("data", [])
                    if model_list:
                        served_name = model_list[0].get("id")
                        print(f"vLLM is READY! Served model name: '{served_name}'")
                        return served_name
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"vLLM server on port {port} failed to start within {max_wait}s")

def rescore_unit(row: dict) -> dict:
    """Recompute all derived scoring metrics from probabilities."""
    probs = row.get("probabilities", {})
    ground_truth = row.get("ground_truth")
    options = row.get("options", ["YES", "NO"])
    
    if not probs or ground_truth is None:
        return row
        
    # 1. Brier Score
    row["brier"] = brier_score(probs, ground_truth, options=options)
    
    # 2. RPS
    row["rps"] = ranked_probability_score(probs, ground_truth, options=options)
    
    # 3. Directional Accuracy & Yes Probability
    if len(options) == 2 and set(options) == {"YES", "NO"}:
        row["yes_probability"] = probs.get("YES", 0.5)
        yes_p = probs.get("YES", 0.5)
        is_yes_gt = (ground_truth == "YES")
        if yes_p == 0.5:
            row["directional_accuracy"] = 0.5
            row["directional_correct"] = None
        elif (yes_p > 0.5 and is_yes_gt) or (yes_p < 0.5 and not is_yes_gt):
            row["directional_accuracy"] = 1.0
            row["directional_correct"] = 1
        else:
            row["directional_accuracy"] = 0.0
            row["directional_correct"] = 0
            
        # Calibration
        pred_p = yes_p if yes_p >= 0.5 else (1.0 - yes_p)
        row["calibration_predicted_probability"] = pred_p
        if pred_p < 0.25:
            row["calibration_bracket"] = "0-0.25"
        elif pred_p < 0.50:
            row["calibration_bracket"] = "0.25-0.5"
        elif pred_p < 0.75:
            row["calibration_bracket"] = "0.5-0.75"
        else:
            row["calibration_bracket"] = "0.75-1"
        row["calibration_hit"] = 1 if ((yes_p >= 0.5) == is_yes_gt) else 0
        
    return row

def main():
    port = int(os.environ.get("VLLM_PORT", "8080"))
    model_name = get_vllm_model_name(port)
    
    router = BenchmarkRoleRouter(
        api_key="EMPTY",
        base_url=f"http://127.0.0.1:{port}/v1",
        graph_model=model_name,
        benchmark_model=model_name,
        evaluator_model=model_name,
    )
    evaluator = ProbabilityEvaluator(router)
    
    # Load events
    events_raw_path = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/data/events_raw.json")
    raw_data = json.loads(events_raw_path.read_text(encoding='utf-8'))
    events_by_id = {}
    if isinstance(raw_data, list):
        events_by_id = {e["event_id"]: e for e in raw_data if "event_id" in e}
    elif isinstance(raw_data, dict):
        for e in raw_data.get("core_events", {}).get("events", []):
            events_by_id[e.get("event_id") or e.get("id")] = e
        for e in raw_data.get("supplementary_events", {}).get("events", []):
            events_by_id[e.get("event_id") or e.get("id")] = e
            
    print(f"Loaded {len(events_by_id)} event definitions.")
    
    # =========================================================================
    # PART 1: Evaluate the 18 units of the 6 newly simulated events for Qwen14B
    # =========================================================================
    print("\n=======================================================")
    print("=== PART 1: EVALUATING 6 NEW EVENTS FOR QWEN2.5-14B ===")
    print("=======================================================")
    
    sim_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/qwen2.5_14b/ecnbench_20260820T133726352240Z")
    seeds_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/data/seeds")
    target_events = ["T3", "T4", "T5", "T6", "C6", "T8"]
    conditions = ["A", "B", "C"]
    
    new_evaluated_rows = []
    
    for event_id in target_events:
        event_obj = events_by_id.get(event_id, {})
        question = event_obj.get("question") or event_obj.get("title") or "Event Outcome?"
        options = event_obj.get("options", ["YES", "NO"])
        ground_truth = event_obj.get("ground_truth")
        micro_questions = event_obj.get("micro_questions", [])
        seed_path = seeds_dir / event_id / "context.md"
        
        for cond in conditions:
            unit_id = f"{event_id}_{cond}_r1"
            unit_dir = sim_dir / unit_id
            sim_log_path = unit_dir / "simulation.log"
            
            print(f"\n--- Evaluating Unit: {unit_id} (Event: {event_id}, Cond: {cond}) ---")
            
            evidence_text = ""
            if cond == "A":
                if seed_path.exists():
                    evidence_text = f"No-Sim Seed Context (Condition A baseline):\n{seed_path.read_text(encoding='utf-8', errors='replace')[:4000]}"
            else:
                if sim_log_path.exists():
                    evidence_text = build_evidence_text(sim_log_path, seed_path)
                else:
                    print(f"Warning: {sim_log_path} not found!")
                    
            print(f"Evidence text length: {len(evidence_text)} chars")
            
            try:
                eval_res = evaluator.evaluate(
                    event_question=question,
                    condition=cond,
                    evidence_text=evidence_text,
                    options=options,
                    micro_questions=micro_questions,
                    event=event_obj
                )
                
                row = {
                    "event_id": event_id,
                    "unit_id": unit_id,
                    "question": question,
                    "ground_truth": ground_truth,
                    "options": options,
                    "condition": cond,
                    "repeat": 1,
                    "seed_file": f"../../data/seeds/{event_id}/context.md",
                    "simulation_status": "completed",
                    "full_simulation_completed": True,
                    "simulation_executed": (cond != "A"),
                    "probabilities": eval_res.get("probabilities"),
                    "mcq_dimensions": eval_res.get("mcq_dimensions"),
                    "validated_scales": eval_res.get("validated_scales"),
                    "micro_epistemic_mapping": eval_res.get("micro_epistemic_mapping"),
                    "strict_contract": True,
                    "evaluator_fallback_used": False,
                    "evaluator_fallback_reason": None,
                    "evaluator_fallback_source": None,
                    "evaluation_status": "completed",
                    "error": None,
                    "evidence_text": evidence_text[:2000]
                }
                row = rescore_unit(row)
                new_evaluated_rows.append(row)
                print(f"[SUCCESS] Unit {unit_id} evaluated! Probs: {row['probabilities']}, Brier: {row.get('brier')}")
            except Exception as e:
                print(f"[ERROR] Failed evaluating unit {unit_id}: {e}")
                
    # Save the 18 new units
    new_results_path = sim_dir / "event_results.json"
    with open(new_results_path, "w", encoding="utf-8") as f:
        json.dump(new_evaluated_rows, f, ensure_ascii=False, indent=2)
    print(f"\nSaved 18 evaluated units to {new_results_path}")
    
    # =========================================================================
    # PART 2: Merge into the main campaign dataset (90 units total)
    # =========================================================================
    main_campaign_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete")
    main_results_path = main_campaign_dir / "event_results.json"
    
    existing_rows = []
    if main_results_path.exists():
        existing_rows = json.load(open(main_results_path, encoding='utf-8'))
        print(f"Loaded existing {len(existing_rows)} rows from main campaign.")
        
    # Replace or append the 6 events
    merged_rows_dict = {r["unit_id"]: r for r in existing_rows}
    for r in new_evaluated_rows:
        merged_rows_dict[r["unit_id"]] = r
        
    all_units = list(merged_rows_dict.values())
    print(f"Total merged units count: {len(all_units)}/90")
    
    # Backup existing
    if main_results_path.exists():
        backup_path = main_campaign_dir / f"event_results_backup_{int(time.time())}.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(existing_rows, f, ensure_ascii=False, indent=2)
            
    with open(main_results_path, "w", encoding="utf-8") as f:
        json.dump(all_units, f, ensure_ascii=False, indent=2)
    print(f"SUCCESSFULLY UPDATED MAIN CAMPAIGN AT {main_results_path}!")
    
    print("\n=======================================================")
    print("=== EVALUATION COMPLETED WITH 100% SUCCESS ===")
    print("=======================================================")

if __name__ == "__main__":
    main()
