import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY")
BACKEND_DIR = PROJECT_ROOT / "MiroFish-Offline" / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

import run_ecnbench_protocol as protocol  # noqa: E402

RUN_DIR = PROJECT_ROOT / "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z"
rows = json.loads((RUN_DIR / "event_results.json").read_text(encoding="utf-8"))

summary = protocol.write_summary(RUN_DIR, rows)
print("Wrote summary.json")
print(json.dumps({
    "condition_mean_brier": summary.get("condition_mean_brier"),
    "lift": summary.get("lift"),
    "evaluator_reliability": summary.get("evaluator_reliability"),
}, indent=2))
