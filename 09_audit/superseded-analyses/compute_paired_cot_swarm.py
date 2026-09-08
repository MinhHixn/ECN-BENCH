#!/usr/bin/env python3
"""Detailed paired statistical comparison: Single-Agent CoT vs Multi-Agent Swarm (Condition B).
"""
import json, os, math, random, sys
import scipy.stats as stats
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

CLEAN17 = ["C1", "C5", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T9"]

with open(os.path.join(ROOT, 'single_agent_cot_baseline_results.json'), 'r', encoding='utf-8') as f:
    cot_raw = json.load(f)

# Load evaluator A reads for swarm
from make_predictive_signal import load as load_swarm, CAMPS, hit as hit_sw, brier as brier_sw

DATA_SWARM = {m: load_swarm(m) for m in CAMPS}

cot_grouped = {}
for r in cot_raw:
    if r.get('status') == 'success':
        cot_grouped.setdefault(r['model'], {}).setdefault(r['event_id'], []).append(r)

model_map = {
    "Llama-3.1-8B": "Llama-3.1-8B",
    "Mistral-8B": "Mistral-7B",
    "Qwen2.5-7B": "Qwen2.5-7B",
    "Qwen3-14B": "Qwen2.5-14B"
}

def boot_ci(d, n=20000, seed=7):
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(n))
    return st.mean(d), reps[int(0.025 * n)], reps[int(0.975 * n)]

def dm_hln_test(d_series):
    n = len(d_series)
    d_bar = st.mean(d_series)
    s_d = st.stdev(d_series) if n > 1 else 1e-6
    dm = d_bar / (s_d / math.sqrt(n)) if s_d > 1e-9 else 0.0
    corr = math.sqrt((n - 1) / n)
    dm_hln = dm * corr
    p_2sided = 2.0 * (1.0 - stats.t.cdf(abs(dm_hln), df=n-1))
    return dm, dm_hln, p_2sided

print("=== STATISTICAL COMPARISON: SWARM CONDITION B vs SINGLE-AGENT CoT ===\n")

pool_d_acc = []
pool_d_brier = []

detailed_res = {}

for cot_m, sw_m in model_map.items():
    d_acc = []
    d_brier = []
    
    for eid in CLEAN17:
        # Swarm
        sw_rec = DATA_SWARM[sw_m][(eid, "B")]
        sw_h = hit_sw(sw_rec)
        sw_b = brier_sw(sw_rec)
        
        # CoT
        reps = cot_grouped[cot_m][eid]
        opts = reps[0]['options']
        avg_p = {o: st.mean(r['probabilities'].get(o, 0.0) for r in reps) for o in opts}
        gt = reps[0]['ground_truth']
        cot_b = sum((avg_p.get(o, 0.0) - (1.0 if o == gt else 0.0)) ** 2 for o in opts)
        
        mx = max(avg_p.values())
        tied = [o for o, v in avg_p.items() if abs(v - mx) < 1e-6]
        if len(tied) == 1:
            cot_h = 1.0 if tied[0].casefold() == str(gt).casefold() else 0.0
        else:
            cot_h = 1.0 / len(tied) if any(t.casefold() == str(gt).casefold() for t in tied) else 0.0
            
        # Diff (Swarm - CoT)
        d_acc.append(sw_h - cot_h)
        # Brier diff: CoT - Swarm (positive = Swarm better)
        d_brier.append(cot_b - sw_b)
        
    pool_d_acc.extend(d_acc)
    pool_d_brier.extend(d_brier)
    
    mu_acc, lo_acc, hi_acc = boot_ci(d_acc)
    mu_br, lo_br, hi_br = boot_ci(d_brier)
    dm, dm_hln, p_val = dm_hln_test(d_brier)
    
    print(f"Model: {cot_m} (vs {sw_m})")
    print(f"  Delta Accuracy (Swarm - CoT): {mu_acc*100:+.1f}% [{lo_acc*100:+.1f}%, {hi_acc*100:+.1f}%]")
    print(f"  Delta Brier (CoT - Swarm):    {mu_br:+.4f} [{lo_br:+.4f}, {hi_br:+.4f}]")
    print(f"  DM: {dm:.3f} | DM-HLN: {dm_hln:.3f} | 2-sided p (df=16): {p_val:.4f}\n")

# Pooled
mu_acc, lo_acc, hi_acc = boot_ci(pool_d_acc)
mu_br, lo_br, hi_br = boot_ci(pool_d_brier)
dm, dm_hln, p_val = dm_hln_test(pool_d_brier)

print("="*60)
print(f"POOLED (68 unit-pairs):")
print(f"  Delta Accuracy (Swarm - CoT): {mu_acc*100:+.1f}% [{lo_acc*100:+.1f}%, {hi_acc*100:+.1f}%]")
print(f"  Delta Brier (CoT - Swarm):    {mu_br:+.4f} [{lo_br:+.4f}, {hi_br:+.4f}]")
print(f"  DM: {dm:.3f} | DM-HLN: {dm_hln:.3f} | 2-sided p (df=67): {p_val:.4f}")
