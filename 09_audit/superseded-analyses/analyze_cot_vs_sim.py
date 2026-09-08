#!/usr/bin/env python3
"""Analyze Single-Agent RAG+CoT baseline vs Multi-Agent Swarm (Condition B) on 17 Clean Events.
"""
import json, os, math, random
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

CLEAN17 = ["C1", "C5", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T9"]

with open(os.path.join(ROOT, 'single_agent_cot_baseline_results.json'), 'r', encoding='utf-8') as f:
    cot_raw = json.load(f)

with open(os.path.join(ROOT, 'predictive_signal_analysis.json'), 'r', encoding='utf-8') as f:
    swarm_data = json.load(f)

# Group CoT by model and event
cot_grouped = {}
for r in cot_raw:
    if r.get('status') != 'success':
        continue
    m = r['model']
    eid = r['event_id']
    cot_grouped.setdefault(m, {}).setdefault(eid, []).append(r)

def poisson_binomial_sf(k, ps):
    dist = [1.0]
    for p in ps:
        nd = [0.0] * (len(dist) + 1)
        for i, v in enumerate(dist):
            nd[i] += v * (1 - p)
            nd[i + 1] += v * p
        dist = nd
    return sum(dist[int(math.ceil(k - 1e-9)):])

def boot_ci(d, n=20000, seed=7):
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(n))
    return st.mean(d), reps[int(0.025 * n)], reps[int(0.975 * n)]

analysis = {
    "models": {},
    "pooled": {}
}

all_cot_hits = []
all_cot_briers = []
all_ps = []

print("=== SINGLE-AGENT RAG+CoT VS MULTI-AGENT SWARM (17 CLEAN EVENTS) ===\n")
print(f"{'Model':<15} | {'Single CoT Acc':<14} | {'Swarm B Acc':<12} | {'Single CoT Brier':<16} | {'Swarm B Brier':<14} | {'Lift (Brier)':<14}")
print("-" * 95)

# Map model names if needed
model_map = {
    "Llama-3.1-8B": "Llama-3.1-8B",
    "Mistral-8B": "Mistral-7B", # In swarm it was Mistral-7B
    "Qwen2.5-7B": "Qwen2.5-7B",
    "Qwen3-14B": "Qwen2.5-14B" # In swarm it was Qwen2.5-14B
}

for cot_m, swarm_m in model_map.items():
    if cot_m not in cot_grouped:
        continue
    
    events_data = cot_grouped[cot_m]
    m_hits = []
    m_briers = []
    m_ps = []
    
    for eid in CLEAN17:
        reps = events_data.get(eid, [])
        if not reps:
            continue
        # Average probability across 3 repeats
        opts = reps[0]['options']
        avg_probs = {o: st.mean(r['probabilities'].get(o, 0.0) for r in reps) for o in opts}
        gt = reps[0]['ground_truth']
        
        # Brier
        br = sum((avg_probs.get(o, 0.0) - (1.0 if o == gt else 0.0)) ** 2 for o in opts)
        
        # Hit
        mx = max(avg_probs.values())
        tied = [o for o, v in avg_probs.items() if abs(v - mx) < 1e-6]
        if len(tied) == 1:
            hit = 1.0 if tied[0].casefold() == str(gt).casefold() else 0.0
        else:
            hit = 1.0 / len(tied) if any(t.casefold() == str(gt).casefold() for t in tied) else 0.0
            
        m_hits.append(hit)
        m_briers.append(br)
        m_ps.append(1.0 / len(opts))
        
    all_cot_hits.extend(m_hits)
    all_cot_briers.extend(m_briers)
    all_ps.extend(m_ps)
    
    cot_acc = st.mean(m_hits)
    cot_br = st.mean(m_briers)
    
    sw_acc = swarm_data['models'][swarm_m]['dir_acc_B']
    sw_br = swarm_data['models'][swarm_m]['brier_B']
    
    # Delta Brier = CoT_Brier - Swarm_Brier (positive means Swarm is better / lower error)
    delta_br = cot_br - sw_br
    
    p_cot = poisson_binomial_sf(sum(m_hits), m_ps)
    
    analysis["models"][cot_m] = {
        "cot_directional_accuracy": round(cot_acc, 4),
        "cot_brier": round(cot_br, 4),
        "cot_poisson_p": p_cot,
        "swarm_directional_accuracy": sw_acc,
        "swarm_brier": sw_br,
        "swarm_lift_over_cot_brier": round(delta_br, 4)
    }
    
    print(f"{cot_m:<15} | {cot_acc*100:>12.1f}% | {sw_acc*100:>10.1f}% | {cot_br:>16.4f} | {sw_br:>14.4f} | {delta_br:>+14.4f}")

# Pooled
pooled_cot_acc = sum(all_cot_hits) / len(all_cot_hits)
pooled_cot_br = st.mean(all_cot_briers)
pooled_sw_acc = swarm_data['pooled']['dir_acc_B']
# compute pooled swarm brier
pooled_sw_briers = [swarm_data['models'][m]['brier_B'] for m in swarm_data['models']]
pooled_sw_br = st.mean(pooled_sw_briers)
pooled_delta_br = pooled_cot_br - pooled_sw_br

p_pooled_cot = poisson_binomial_sf(sum(all_cot_hits), all_ps)

analysis["pooled"] = {
    "n_units": len(all_cot_hits),
    "pooled_cot_directional_accuracy": round(pooled_cot_acc, 4),
    "pooled_cot_brier": round(pooled_cot_br, 4),
    "pooled_cot_poisson_p": p_pooled_cot,
    "pooled_swarm_directional_accuracy": pooled_sw_acc,
    "pooled_swarm_brier": round(pooled_sw_br, 4),
    "pooled_swarm_lift_over_cot_brier": round(pooled_delta_br, 4)
}

print("-" * 95)
print(f"{'POOLED (68 units)':<15} | {pooled_cot_acc*100:>12.1f}% | {pooled_sw_acc*100:>10.1f}% | {pooled_cot_br:>16.4f} | {pooled_sw_br:>14.4f} | {pooled_delta_br:>+14.4f}")
print(f"\nSingle CoT Exact Poisson-binomial p-value: {p_pooled_cot:.2e}")

with open(os.path.join(ROOT, 'single_agent_cot_analysis_summary.json'), 'w', encoding='utf-8') as f:
    json.dump(analysis, f, indent=2)
print("Wrote single_agent_cot_analysis_summary.json")
