
import json, sys
from pathlib import Path

PROJECT_ROOT = Path("/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/project_backup/MiroFish-Offline/backend")
from separate_evaluator_datasets import rescore  # noqa: E402

target = PROJECT_ROOT / "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z/event_results_llama_23events_recovery.json"
events_raw_path = PROJECT_ROOT / "data" / "events_raw.json"

raw = json.loads(events_raw_path.read_text(encoding="utf-8"))
events_by_id = {}
for cat_events in raw.get("core_events", {}).values():
    for e in cat_events:
        events_by_id[e["id"]] = e
for e in raw.get("supplementary_events", {}).get("events", []):
    events_by_id[e["id"]] = e

import shutil, datetime
backup_path = target.with_suffix(f".pre_field_patch_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.json.bak")
shutil.copy2(target, backup_path)
print(f"Backed up to {backup_path}")

data = json.loads(target.read_text(encoding="utf-8"))
patched = 0
for row in data:
    needs_patch = not row.get("ground_truth") or not row.get("unit_id")
    if not needs_patch:
        continue
    event_id = row.get("event_id")
    condition = row.get("condition")
    repeat = row.get("repeat", 1)
    event_obj = events_by_id.get(event_id, {})
    if not row.get("ground_truth"):
        row["ground_truth"] = str(event_obj.get("outcome") or event_obj.get("answer") or "")
    if not row.get("unit_id"):
        row["unit_id"] = f"{event_id}_{condition}_r{repeat}"
    if not row.get("options"):
        row["options"] = event_obj.get("options", [])
    data[data.index(row)] = rescore(row)
    patched += 1

target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

missing_gt = sum(1 for r in data if not r.get("ground_truth"))
missing_uid = sum(1 for r in data if not r.get("unit_id"))
missing_brier = sum(1 for r in data if r.get("brier") is None)
print(f"Patched {patched} rows.")
print(f"After patch -- missing ground_truth: {missing_gt}, missing unit_id: {missing_uid}, brier still None: {missing_brier}")
