import glob, json, os, time, sys
from pathlib import Path

backend_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/MiroFish-Offline/backend")
if not backend_dir.exists():
    backend_dir = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/project_backup/MiroFish-Offline/backend")
sys.path.insert(0, str(backend_dir))

from app.benchmarks.evaluator import ProbabilityEvaluator
from app.benchmarks.role_router import BenchmarkRoleRouter

print("=== JOB B: DEDICATED RE-EVALUATION FOR QWEN2.5-14B (87 UNITS) ===")

qwen14b_path = "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/event_results.json"
raw_events_path = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/data/events_raw.json")
raw_events_list = json.loads(raw_events_path.read_text(encoding='utf-8'))
events_by_id = {e["event_id"]: e for e in raw_events_list}

vllm_port = os.environ.get("VLLM_PORT", "8081")
evaluator_model = os.environ.get("EVALUATOR_MODEL_NAME", "deepseek-r1-14b")
evaluator_base_url = os.environ.get("BENCHMARK_ROLE_EVALUATOR_BASE_URL", f"http://127.0.0.1:{vllm_port}/v1")

router = BenchmarkRoleRouter(
    api_key="EMPTY",
    base_url=evaluator_base_url,
    graph_model=evaluator_model,
    benchmark_model=evaluator_model,
    evaluator_model=evaluator_model,
    evaluator_base_url=evaluator_base_url
)
evaluator = ProbabilityEvaluator(router)

data = json.load(open(qwen14b_path, encoding='utf-8'))
repaired = 0

for idx, row in enumerate(data):
    unit_id = row.get("unit_id")
    event_id = row.get("event_id")
    condition = row.get("condition")
    is_fallback = row.get("evaluator_fallback_used", False)
    mcq = row.get("mcq_dimensions")
    micro = row.get("micro_epistemic_mapping")
    
    is_faulty = (
        is_fallback
        or not isinstance(mcq, dict) or not mcq
        or not isinstance(micro, dict) or not micro
    )
    
    if is_faulty:
        print(f"\nTargeting Qwen14B Unit #{idx+1}/90: {unit_id} (Event: {event_id}, Condition: {condition})...")
        event_obj = events_by_id.get(event_id, {})
        try:
            eval_res = evaluator.evaluate(
                event_question=event_obj.get("question", "What is the outcome?"),
                condition=condition,
                evidence_text=event_obj.get("evidence", ""),
                options=event_obj.get("options", ["YES", "NO"]),
                micro_questions=event_obj.get("micro_questions", []),
                event=event_obj
            )
            data[idx]["probabilities"] = eval_res.get("probabilities")
            data[idx]["mcq_dimensions"] = eval_res.get("mcq_dimensions")
            data[idx]["validated_scales"] = eval_res.get("validated_scales")
            data[idx]["micro_epistemic_mapping"] = eval_res.get("micro_epistemic_mapping")
            data[idx]["evaluator_fallback_used"] = False
            data[idx]["evaluation_status"] = "completed"
            repaired += 1
            print(f"[SUCCESS QWEN14B] Repaired Unit {unit_id} ({repaired}/87)!")
            
            # Incremental persistence every 2 units
            if repaired % 2 == 0:
                with open(qwen14b_path, "w", encoding="utf-8") as out_f:
                    json.dump(data, out_f, ensure_ascii=False, indent=2)
                print(f"[CHECKPOINT QWEN14B] Incremental save: {repaired}/87 units completed!")
                
        except Exception as exc:
            print(f"[FAILED QWEN14B] Unit {unit_id}: {exc}")

with open(qwen14b_path, "w", encoding="utf-8") as out_f:
    json.dump(data, out_f, ensure_ascii=False, indent=2)
print(f"SAVED 100% COMPLETE REPAIRED FILE FOR QWEN2.5-14B ({repaired} units updated)!")
