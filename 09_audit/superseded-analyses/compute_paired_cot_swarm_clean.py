#!/usr/bin/env python3
"""Detailed paired statistical comparison: Single-Agent CoT vs Multi-Agent Swarm (Condition B).
"""
import json, os, math, random
import scipy.stats as stats
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

CLEAN17 = ["C1", "C5", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T9"]

with open(os.path.join(ROOT, 'single_agent_cot_baseline_results.json'), 'r', encoding='utf-8') as f:
    cot_raw = json.load(f)

# Load swarm data directly
CAMPS = {
    "Llama-3.1-8B":  "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
    "Mistral-7B":    "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z",
    "Qwen2.5-7B":    "completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z",
    "Qwen2.5-14B":   "completed_benches/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete",
}
A_READS = ["event_results_evaluatorB_openrouter.json",
           "event_results_evaluatorA_repeat1.json",
           "event_results_evaluatorA_repeat2.json",
           "event_results_evaluatorA_repeat3.json"]

KNOWN_GAPS = {
    ("Qwen2.5-7B",  "event_results_evaluatorA_repeat3.json"): {"T3_C_r1", "C9_A_r1", "C13_C_r1"},
    ("Qwen2.5-14B", "event_results_evaluatorA_repeat2.json"): {"T1_C_r1"},
}

def load_swarm_data(model):
    per = {}
    for fn in A_READS:
        path = os.path.join(ROOT, CAMPS[model], fn)
        if not os.path.exists(path):
            continue
        gaps = KNOWN_GAPS.get((model, fn), set())
        with open(path, encoding="utf-8") as fp:
            for r in json.load(fp):
                uid = r.get("unit") or "%s_%s_r1" % (r["event_id"], r["condition"])
                if uid in gaps:
                    continue
                pr, gt = r.get("probabilities") or {}, r.get("ground_truth")
                if pr and gt:
                    per.setdefault((r["event_id"], r["condition"]), []).append((pr, gt))
    out = {}
    for key, reads in per.items():
        opts = sorted(reads[0][0].keys())
        out[key] = {"probs": {o: st.mean(rd[0].get(o, 0.0) for rd in reads) for o in opts},
                    "gt": reads[0][1], "k": len(opts), "n_reads": len(reads)}
    return out

def hit_eval(rec):
    mx = max(rec["probs"].values())
    tied = [o for o, v in rec["probs"].items() if math.isclose(v, mx, abs_tol=1e-12)]
    gt = str(rec["gt"]).casefold()
    if len(tied) == 1:
        return 1.0 if tied[0].casefold() == gt else 0.0
    return 1.0 / len(tied) if any(t.casefold() == gt for t in tied) else 0.0

def brier_eval(rec):
    return sum((v - (1.0 if o == rec["gt"] else 0.0)) ** 2 for o, v in rec["probs"].items())

DATA_SWARM = {m: load_swarm_data(m) for m in CAMPS}

cot_grouped = {}
for r in cot_raw:
    if r.get('status') == 'success':
        cot_grouped.setdefault(r['model'], {}).setdefault(r['event_id'], []).append(r)

model_map = {
    "Llama-3.1-8B": ("Llama-3.1-8B", "Llama-3.1-8B"),
    "Mistral-8B": ("Mistral-8B", "Mistral-7B"),
    "Qwen2.5-7B": ("Qwen2.5-7B", "Qwen2.5-7B"),
    "Qwen3-14B": ("Qwen3-14B", "Qwen2.5-14B")
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

summary_rows = []

for cot_m, (cot_key, sw_key) in model_map.items():
    d_acc = []
    d_brier = []
    
    cot_hits_m = []
    cot_briers_m = []
    sw_hits_m = []
    sw_briers_m = []
    
    for eid in CLEAN17:
        # Swarm
        sw_rec = DATA_SWARM[sw_key][(eid, "B")]
        sw_h = hit_eval(sw_rec)
        sw_b = brier_eval(sw_rec)
        
        # CoT
        reps = cot_grouped[cot_key][eid]
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
            
        cot_hits_m.append(cot_h)
        cot_briers_m.append(cot_b)
        sw_hits_m.append(sw_h)
        sw_briers_m.append(sw_b)
        
        # Diff (Swarm - CoT)
        d_acc.append(sw_h - cot_h)
        # Brier diff: CoT - Swarm (positive = Swarm better)
        d_brier.append(cot_b - sw_b)
        
    pool_d_acc.extend(d_acc)
    pool_d_brier.extend(d_brier)
    
    mu_acc, lo_acc, hi_acc = boot_ci(d_acc)
    mu_br, lo_br, hi_br = boot_ci(d_brier)
    dm, dm_hln, p_val = dm_hln_test(d_brier)
    
    summary_rows.append({
        "model": cot_m,
        "cot_acc": st.mean(cot_hits_m),
        "sw_acc": st.mean(sw_hits_m),
        "cot_brier": st.mean(cot_briers_m),
        "sw_brier": st.mean(sw_briers_m),
        "delta_acc": [mu_acc, lo_acc, hi_acc],
        "delta_brier": [mu_br, lo_br, hi_br],
        "dm_hln": dm_hln,
        "p_2sided": p_val
    })
    
    print(f"Model: {cot_m} (vs Swarm {sw_key})")
    print(f"  Single CoT: Acc = {st.mean(cot_hits_m)*100:.1f}%, Brier = {st.mean(cot_briers_m):.4f}")
    print(f"  Swarm B:    Acc = {st.mean(sw_hits_m)*100:.1f}%, Brier = {st.mean(sw_briers_m):.4f}")
    print(f"  Delta Acc (Swarm - CoT): {mu_acc*100:+.1f}% [{lo_acc*100:+.1f}%, {hi_acc*100:+.1f}%]")
    print(f"  Delta Brier (CoT - Swarm): {mu_br:+.4f} [{lo_br:+.4f}, {hi_br:+.4f}]")
    print(f"  DM: {dm:.3f} | DM-HLN: {dm_hln:.3f} | 2-sided p (df=16): {p_val:.4f}\n")

# Pooled
mu_acc, lo_acc, hi_acc = boot_ci(pool_d_acc)
mu_br, lo_br, hi_br = boot_ci(pool_d_brier)
dm, dm_hln, p_val = dm_hln_test(pool_d_brier)

print("="*70)
print(f"POOLED (68 unit-pairs across all 4 models):")
print(f"  Pooled Single CoT: Acc = {st.mean([r['cot_acc'] for r in summary_rows])*100:.1f}%, Brier = {st.mean([r['cot_brier'] for r in summary_rows]):.4f}")
print(f"  Pooled Swarm B:    Acc = {st.mean([r['sw_acc'] for r in summary_rows])*100:.1f}%, Brier = {st.mean([r['sw_brier'] for r in summary_rows]):.4f}")
print(f"  Delta Accuracy (Swarm - CoT): {mu_acc*100:+.1f}% [{lo_acc*100:+.1f}%, {hi_acc*100:+.1f}%]")
print(f"  Delta Brier (CoT - Swarm):    {mu_br:+.4f} [{lo_br:+.4f}, {hi_br:+.4f}]")
print(f"  DM: {dm:.3f} | DM-HLN: {dm_hln:.3f} | 2-sided p (df=67): {p_val:.4f}")

with open(os.path.join(ROOT, 'paired_cot_swarm_detailed_stats.json'), 'w', encoding='utf-8') as f:
    json.dump({
        "models": summary_rows,
        "pooled": {
            "delta_acc": [mu_acc, lo_acc, hi_acc],
            "delta_brier": [mu_br, lo_br, hi_br],
            "dm": dm,
            "dm_hln": dm_hln,
            "p_2sided": p_val
        }
    }, f, indent=2)
