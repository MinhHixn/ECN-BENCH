"""
event_results.json's 72 resimulated Llama rows have real, independent
probabilities/mcq_dimensions (run1) but no run1/run2 dimension-label pair,
because they came through run_openrouter_eval_official.py's single-call path.
The kappa reliability table needs a genuine second independent read per row
to reconstruct that pair, matching _evaluate_row's original dual-call design
-- run2's probabilities are discarded, only its mcq_dimensions bucket labels
are used for the reliability comparison.
"""
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "MiroFish-Offline" / "backend"))

from app.benchmarks.evaluator import ProbabilityEvaluator
from app.benchmarks.role_router import BenchmarkRoleRouter
from app.benchmarks.reliability import dominant_bucket_label

TARGET = PROJECT_ROOT / "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z/event_results.json"
EVENTS_RAW = PROJECT_ROOT / "data" / "events_raw.json"
API_KEY = "REDACTED_SET_OPENROUTER_API_KEY"

raw = json.loads(EVENTS_RAW.read_text(encoding="utf-8"))
events_by_id = {}
for cat_events in raw.get("core_events", {}).values():
    for e in cat_events:
        events_by_id[e["id"]] = e
for e in raw.get("supplementary_events", {}).get("events", []):
    events_by_id[e["id"]] = e

router = BenchmarkRoleRouter(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    graph_model="deepseek/deepseek-v4-flash-0731",
    benchmark_model="deepseek/deepseek-v4-flash-0731",
    evaluator_model="deepseek/deepseek-v4-flash-0731",
    evaluator_base_url="https://openrouter.ai/api/v1",
)
evaluator = ProbabilityEvaluator(router)

data = json.loads(TARGET.read_text(encoding="utf-8"))
targets = [i for i, r in enumerate(data) if r.get("resimulated_via") and not r.get("evaluator_dimension_labels")]
print(f"Rows needing a run2 read: {len(targets)}", flush=True)

save_lock = threading.Lock()
done = 0


def fetch_run2(idx):
    row = data[idx]
    event_id = row.get("event_id")
    condition = row.get("condition")
    event_obj = events_by_id.get(event_id, {})
    question = row.get("question") or event_obj.get("question", "")
    evidence = row.get("evidence_text") or ""
    options = row.get("options") or event_obj.get("options", [])
    micro_qs = event_obj.get("micro_questions", [])
    try:
        run2 = evaluator.evaluate(
            event_question=question,
            condition=condition,
            evidence_text=evidence,
            options=options,
            micro_questions=micro_qs,
            event=event_obj,
        )
        return idx, run2, None
    except Exception as exc:
        return idx, None, exc


with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(fetch_run2, idx) for idx in targets]
    for future in as_completed(futures):
        idx, run2, exc = future.result()
        row = data[idx]
        with save_lock:
            done += 1
            if exc is not None:
                print(f"  [{done}/{len(targets)}] [ERROR] {row.get('unit_id')}: {exc}", flush=True)
                continue

            mcq_run1 = row.get("mcq_dimensions") or {}
            mcq_run2 = run2.get("mcq_dimensions") or {}
            labels = {}
            reliability_dims = 0
            for dim, buckets1 in mcq_run1.items():
                try:
                    l1 = dominant_bucket_label(buckets1)
                except ValueError:
                    continue
                reliability_dims += 1
                buckets2 = mcq_run2.get(dim)
                if not isinstance(buckets2, dict):
                    continue
                try:
                    l2 = dominant_bucket_label(buckets2)
                except ValueError:
                    continue
                labels[dim] = {"run1": l1, "run2": l2}

            status = "complete"
            if reliability_dims == 0 or not mcq_run2 or not labels:
                status = "absent"
            elif len(labels) < reliability_dims:
                status = "partial"

            row["evaluator_dimension_labels"] = labels or None
            row["evaluator_reliability_status"] = status
            row["evaluator_dimension_label_basis"] = "run1_run2_pair"
            print(f"  [{done}/{len(targets)}] [SUCCESS] {row.get('unit_id')} -> {status}", flush=True)

            TARGET.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Done. {done}/{len(targets)} rows processed.", flush=True)
