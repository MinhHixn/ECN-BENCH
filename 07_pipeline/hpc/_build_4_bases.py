
import json
from pathlib import Path

TARGET_DIR = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z")
SRC = TARGET_DIR / "event_results_llama_23events_recovery.json"

base = json.loads(SRC.read_text(encoding="utf-8"))

RESET_KEYS = ["probabilities", "brier", "rps", "directional_accuracy", "directional_correct",
              "calibration_bracket", "calibration_predicted_probability", "calibration_hit",
              "yes_probability", "mcq_dimensions", "validated_scales", "micro_epistemic_mapping",
              "evaluator_dimension_labels", "evaluator_dimension_label_basis",
              "evaluator_reliability_status", "evaluator_noisy_dimensions"]

for dest_name in [
    "event_results_llama_23events_repeat1.json",
    "event_results_llama_23events_repeat2.json",
    "event_results_llama_23events_repeat3.json",
    "event_results_llama_23events_gptlunapro.json",
]:
    rows = []
    for row in base:
        r = dict(row)
        for k in RESET_KEYS:
            r[k] = None
        r["evaluator_fallback_used"] = True
        r["evaluator_fallback_reason"] = "pending_fresh_read"
        r["evaluator_fallback_source"] = None
        r["evaluation_status"] = "pending"
        rows.append(r)
    (TARGET_DIR / dest_name).write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} fresh-fallback rows to {dest_name}")
