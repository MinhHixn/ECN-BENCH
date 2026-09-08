
import json
p = "/scratch/waves/users/mhnguyn2025@ec-nantes.fr/ECN-HPC-DEPLOY/completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z/event_results_llama_23events_recovery.json"
d = json.load(open(p))
print("total rows:", len(d))
print("events:", len(set(r["event_id"] for r in d)))
print("fallback still true:", sum(1 for r in d if r.get("evaluator_fallback_used")))
print("missing ground_truth:", sum(1 for r in d if not r.get("ground_truth")))
print("brier is None:", sum(1 for r in d if r.get("brier") is None))
print("missing unit_id:", sum(1 for r in d if not r.get("unit_id")))
conds = {}
for r in d:
    conds.setdefault(r["event_id"], set()).add(r["condition"])
incomplete = [e for e, c in conds.items() if c != {"A","B","C"}]
print("events without all 3 conditions:", incomplete)
