#!/usr/bin/env python3
"""Single-agent RAG+CoT baseline vs the multi-agent swarm, on the 20 contamination-clean events.

This is the experiment the conference draft named as its own missing control: does the
simulation machinery beat one LLM call given the same evidence?

Three design points that the first pass at this analysis got wrong, and that this script
fixes explicitly:

  1. ARM MATCHING. Only two of the four CoT runs use the same model as the campaign they
     are compared against. `mistralai/ministral-8b-2512` is not Mistral-7B-Instruct-v0.1
     and `qwen/qwen3-14b` is not Qwen2.5-14B, so those two arms are a cross-model
     comparison, not a paired one. The primary pooled estimate is therefore the two
     identity-matched arms; the four-arm pool is reported separately and labelled.

  2. AGGREGATION SYMMETRY. Averaging the three CoT replicates into one probability vector
     gives the single-agent arm an ensembling advantage the swarm arm does not get: the
     swarm's four reads re-read ONE simulation, they do not re-run it. Since the headline
     runs against the swarm, that confound points the same way as the conclusion. We
     report three CoT variants -- `single` (mean of the per-replicate scores, the expected
     cost of one CoT call, and the primary), `ens3` (the 3-vector ensemble, an upper bound
     on what CoT can do at 3x the cost), and `t0` (replicate 1 alone, temperature 0).

  3. CLUSTERING. The 20 events recur across models, so pooled unit-pairs are not
     independent and a df = n-1 Diebold-Mariano test on them is anticonservative. Pooled
     inference here is a cluster bootstrap over events plus a cluster-robust t on the
     per-event means (df = 16 either way).

Swarm side uses the same loader as make_predictive_signal.py: the per-unit mean of the
available Evaluator A reads, so the Condition B numbers here are identical to
Table tab:predictive_signal by construction.

Writes cot_baseline_analysis.json.
"""
import json
import math
import os
import random
import statistics as st

import scipy.stats as stats

HERE = os.path.dirname(os.path.abspath(__file__))

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
# Updated 2026-08-21, matching make_predictive_signal.py: PENDING a rerun of
# run_single_agent_cot_baseline.py (240 tasks) before this actually covers 20
# events -- single_agent_cot_baseline_results.json on disk is still 17-event data,
# so running this script now silently limits back to 17 via the `in CLEAN17` /
# `e in cot_by` filters below rather than erroring.
CLEAN20 = ["C1", "C5", "C6", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T6", "T8", "T9"]
CLEAN17 = CLEAN20  # legacy alias so the rest of this file needs no other edits

# cot label -> (swarm campaign, identity-matched?, note)
ARMS = [
    ("Llama-3.1-8B", "Llama-3.1-8B", True,
     "meta-llama/llama-3.1-8b-instruct (OpenRouter, FP16) vs the same checkpoint "
     "served locally as AWQ-INT4 under vLLM"),
    ("Qwen2.5-7B", "Qwen2.5-7B", True,
     "qwen/qwen-2.5-7b-instruct (OpenRouter, FP16) vs the same checkpoint served "
     "locally as GGUF under Ollama"),
    ("Mistral-8B", "Mistral-7B", False,
     "mistralai/ministral-8b-2512 is a different model and a later generation than "
     "Mistral-7B-Instruct-v0.1; cross-model, not paired"),
    ("Qwen3-14B", "Qwen2.5-14B", False,
     "qwen/qwen3-14b is a different generation than Qwen2.5-14B; cross-model, not paired"),
]


# ----------------------------------------------------------------- swarm side
def load_swarm(model):
    per = {}
    for fn in A_READS:
        path = os.path.join(HERE, CAMPS[model], fn)
        if not os.path.exists(path):
            continue
        gaps = KNOWN_GAPS.get((model, fn), set())
        for r in json.load(open(path, encoding="utf-8")):
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


def hit_of(probs, gt):
    mx = max(probs.values())
    tied = [o for o, v in probs.items() if math.isclose(v, mx, abs_tol=1e-9)]
    g = str(gt).casefold()
    if len(tied) == 1:
        return 1.0 if tied[0].casefold() == g else 0.0
    return 1.0 / len(tied) if any(t.casefold() == g for t in tied) else 0.0


def brier_of(probs, gt):
    return sum((v - (1.0 if o == gt else 0.0)) ** 2 for o, v in probs.items())


# ------------------------------------------------------------------- CoT side
cot_raw = json.load(open(os.path.join(HERE, "single_agent_cot_baseline_results.json"),
                         encoding="utf-8"))
cot_by = {}
for r in cot_raw:
    if r.get("status") == "success":
        cot_by.setdefault(r["model"], {}).setdefault(r["event_id"], []).append(r)


def cot_variants(model, eid):
    """Return {'single': (hit, brier), 'ens3': (...), 't0': (...)} for one event."""
    reps = sorted(cot_by[model][eid], key=lambda r: r["repeat"])
    opts = reps[0]["options"]
    gt = reps[0]["ground_truth"]

    per_rep = [(hit_of({o: r["probabilities"].get(o, 0.0) for o in opts}, gt),
                brier_of({o: r["probabilities"].get(o, 0.0) for o in opts}, gt))
               for r in reps]
    ens = {o: st.mean(r["probabilities"].get(o, 0.0) for r in reps) for o in opts}
    t0 = [r for r in reps if r["repeat"] == 1][0]
    return {
        "single": (st.mean(h for h, _ in per_rep), st.mean(b for _, b in per_rep)),
        "ens3": (hit_of(ens, gt), brier_of(ens, gt)),
        "t0": (hit_of({o: t0["probabilities"].get(o, 0.0) for o in opts}, gt),
               brier_of({o: t0["probabilities"].get(o, 0.0) for o in opts}, gt)),
        "n_reps": len(reps),
    }


# ------------------------------------------------------------------ inference
def boot_ci(d, n=20000, seed=7):
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(d, k=len(d))) for _ in range(n))
    return st.mean(d), reps[int(0.025 * n)], reps[int(0.975 * n)]


def cluster_boot_ci(by_event, n=20000, seed=7):
    """by_event: {event: [d, d, ...]} -- resample EVENTS, keep all arms of a drawn event."""
    keys = list(by_event)
    rng = random.Random(seed)
    reps = []
    for _ in range(n):
        vals = []
        for k in rng.choices(keys, k=len(keys)):
            vals.extend(by_event[k])
        reps.append(st.mean(vals))
    reps.sort()
    flat = [v for k in keys for v in by_event[k]]
    return st.mean(flat), reps[int(0.025 * n)], reps[int(0.975 * n)]


def dm_hln(d):
    """Diebold-Mariano with the Harvey-Leybourne-Newbold small-sample correction."""
    n = len(d)
    if n < 2:
        return 0.0, 0.0, 1.0
    s = st.stdev(d)
    dm = st.mean(d) / (s / math.sqrt(n)) if s > 1e-12 else 0.0
    hln = dm * math.sqrt((n - 1) / n)
    return dm, hln, 2.0 * (1.0 - stats.t.cdf(abs(hln), df=n - 1))


def cluster_t(by_event):
    """Cluster-robust t on the per-event mean difference (df = #events - 1)."""
    means = [st.mean(v) for v in by_event.values()]
    return dm_hln(means)


def poisson_binomial_sf(k, ps):
    dist = [1.0]
    for p in ps:
        nd = [0.0] * (len(dist) + 1)
        for i, v in enumerate(dist):
            nd[i] += v * (1 - p)
            nd[i + 1] += v * p
        dist = nd
    return sum(dist[int(math.ceil(k - 1e-9)):])


# ---------------------------------------------------------------------- main
SWARM = {m: load_swarm(m) for m in CAMPS}
VARIANTS = ("single", "ens3", "t0")

res = {
    "description": __doc__.strip().split("\n")[0],
    "clean_events": CLEAN17,
    "chance_mean_inverse_k": None,
    "poisson_binomial_note": "Exact for the t0 and ens3 variants, whose hit counts are "
                             "integers. For `single` the hit count is a mean over 3 "
                             "replicates and therefore fractional; the survival function "
                             "is evaluated at ceil(count), so that p is approximate and "
                             "conservative. Quote the t0 figure when an exact test is needed.",
    "sign_convention": "Both deltas are oriented so that POSITIVE = the swarm is better: "
                       "delta_brier is BS_CoT - BS_swarm (Brier is a loss) and "
                       "delta_dir_acc is acc_swarm - acc_CoT.",
    "cot_variant_definitions": {
        "single": "mean over the 3 replicates of the per-replicate score; the expected "
                  "cost of ONE CoT call, and the primary basis",
        "ens3": "score of the mean of the 3 replicate probability vectors; a 3x-cost "
                "ensemble and an upper bound on the CoT arm",
        "t0": "replicate 1 only (seed 42, temperature 0); replicates 2 and 3 ran at "
              "temperature 0.7, so the three are not homogeneous draws",
    },
    "arms": [],
    "pooled": {},
}

ks = [SWARM["Mistral-7B"][(e, "B")]["k"] for e in CLEAN17]
res["chance_mean_inverse_k"] = round(st.mean(1.0 / k for k in ks), 4)

# per-arm differences, kept for the pooled cluster bootstrap
diffs = {v: {"matched": {}, "all": {}} for v in VARIANTS}      # variant -> scope -> event -> [d]
diffs_acc = {v: {"matched": {}, "all": {}} for v in VARIANTS}
# pooled directional-accuracy tallies, for the Poisson-binomial test against chance
tally = {sc: {"swarm": [], "chance": [], **{v: [] for v in VARIANTS}}
         for sc in ("matched", "all")}

for cot_key, sw_key, matched, note in ARMS:
    ev = [e for e in CLEAN17 if (e, "B") in SWARM[sw_key] and e in cot_by.get(cot_key, {})]
    sw_hits = [hit_of(SWARM[sw_key][(e, "B")]["probs"], SWARM[sw_key][(e, "B")]["gt"])
               for e in ev]
    sw_briers = [brier_of(SWARM[sw_key][(e, "B")]["probs"], SWARM[sw_key][(e, "B")]["gt"])
                 for e in ev]
    ps = [1.0 / SWARM[sw_key][(e, "B")]["k"] for e in ev]

    arm = {
        "cot_model": cot_key,
        "cot_slug": next(r["model_slug"] for r in cot_raw if r["model"] == cot_key),
        "swarm_campaign": sw_key,
        "identity_matched": matched,
        "note": note,
        "n_events": len(ev),
        "swarm_dir_acc": round(st.mean(sw_hits), 4),
        "swarm_brier": round(st.mean(sw_briers), 4),
        "swarm_poisson_binomial_p": poisson_binomial_sf(sum(sw_hits), ps),
        "variants": {},
    }

    for var in VARIANTS:
        cv = [cot_variants(cot_key, e)[var] for e in ev]
        c_hits = [h for h, _ in cv]
        c_briers = [b for _, b in cv]
        # positive = swarm better, in both metrics
        d_brier = [cb - sb for cb, sb in zip(c_briers, sw_briers)]
        d_acc = [sh - ch for sh, ch in zip(sw_hits, c_hits)]

        mb, lb, hb = boot_ci(d_brier)
        ma, la, ha = boot_ci(d_acc)
        _, hln_b, p_b = dm_hln(d_brier)
        _, hln_a, p_a = dm_hln(d_acc)

        arm["variants"][var] = {
            "cot_dir_acc": round(st.mean(c_hits), 4),
            "cot_brier": round(st.mean(c_briers), 4),
            "cot_poisson_binomial_p": poisson_binomial_sf(sum(c_hits), ps),
            "delta_brier_cot_minus_swarm": [round(mb, 4), round(lb, 4), round(hb, 4)],
            "delta_dir_acc_swarm_minus_cot": [round(ma, 4), round(la, 4), round(ha, 4)],
            "dm_hln_brier": round(hln_b, 3),
            "p_2sided_brier": round(p_b, 4),
            "dm_hln_dir_acc": round(hln_a, 3),
            "p_2sided_dir_acc": round(p_a, 4),
        }

        scopes = ["all"] + (["matched"] if matched else [])
        for sc in scopes:
            for e, db, da in zip(ev, d_brier, d_acc):
                diffs[var][sc].setdefault(e, []).append(db)
                diffs_acc[var][sc].setdefault(e, []).append(da)
            tally[sc][var].extend(c_hits)

    for sc in ["all"] + (["matched"] if matched else []):
        tally[sc]["swarm"].extend(sw_hits)
        tally[sc]["chance"].extend(ps)

    res["arms"].append(arm)

for sc, label in (("matched", "identity-matched arms only (PRIMARY)"),
                  ("all", "all four arms (two are cross-model; secondary)")):
    block = {"scope": label,
             "arms": [a["cot_model"] for a in res["arms"]
                      if (a["identity_matched"] or sc == "all")],
             "n_unit_pairs": sum(len(v) for v in diffs["single"][sc].values()),
             "n_event_clusters": len(diffs["single"][sc]),
             "chance": round(st.mean(tally[sc]["chance"]), 4),
             "swarm_dir_acc": round(st.mean(tally[sc]["swarm"]), 4),
             "swarm_poisson_binomial_p": poisson_binomial_sf(sum(tally[sc]["swarm"]),
                                                             tally[sc]["chance"]),
             "variants": {}}
    for var in VARIANTS:
        mb, lb, hb = cluster_boot_ci(diffs[var][sc])
        ma, la, ha = cluster_boot_ci(diffs_acc[var][sc])
        _, hln_b, p_b = cluster_t(diffs[var][sc])
        _, hln_a, p_a = cluster_t(diffs_acc[var][sc])
        naive = [d for v in diffs[var][sc].values() for d in v]
        _, hln_naive, p_naive = dm_hln(naive)
        block["variants"][var] = {
            "cot_dir_acc": round(st.mean(tally[sc][var]), 4),
            "cot_poisson_binomial_p": poisson_binomial_sf(sum(tally[sc][var]),
                                                          tally[sc]["chance"]),
            "delta_brier_cot_minus_swarm": [round(mb, 4), round(lb, 4), round(hb, 4)],
            "delta_dir_acc_swarm_minus_cot": [round(ma, 4), round(la, 4), round(ha, 4)],
            "cluster_t_brier": round(hln_b, 3),
            "p_2sided_brier_clustered": round(p_b, 4),
            "cluster_t_dir_acc": round(hln_a, 3),
            "p_2sided_dir_acc_clustered": round(p_a, 4),
            "p_2sided_brier_naive_unclustered": round(p_naive, 4),
        }
    res["pooled"][sc] = block

# how many events would it take to resolve the matched-pool effect? (paired t, per-event
# means, two-sided alpha = 0.05; reported so the paper does not have to assert a number)
pe = [st.mean(v) for v in diffs["single"]["matched"].values()]
n_pe, m_pe, s_pe = len(pe), st.mean(pe), st.stdev(pe)
dz = abs(m_pe) / s_pe


def paired_power(n, d):
    crit = stats.t.ppf(0.975, n - 1)
    nc = d * math.sqrt(n)
    return 1 - stats.nct.cdf(crit, n - 1, nc) + stats.nct.cdf(-crit, n - 1, nc)


need = {}
for target in (0.80, 0.90):
    for N in range(5, 2000):
        if paired_power(N, dz) >= target:
            need["n_for_%d_pct_power" % int(target * 100)] = N
            break
res["power_matched_pool"] = {
    "basis": "per-event mean of the matched-arm Brier differences, paired t, two-sided 0.05",
    "n_events": n_pe,
    "mean_diff": round(m_pe, 4),
    "sd_diff": round(s_pe, 4),
    "cohen_dz": round(dz, 4),
    "achieved_power_at_n": round(paired_power(n_pe, dz), 4),
    **need,
}

with open(os.path.join(HERE, "cot_baseline_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

# ------------------------------------------------------------------- console
print("chance (mean 1/K over the %d clean events) = %.4f\n" % (len(CLEAN20), res["chance_mean_inverse_k"]))
for a in res["arms"]:
    tag = "MATCHED" if a["identity_matched"] else "cross-model"
    print("%-14s vs swarm %-14s [%s], n=%d" % (a["cot_model"], a["swarm_campaign"], tag,
                                               a["n_events"]))
    print("   swarm B      acc %.3f  brier %.4f" % (a["swarm_dir_acc"], a["swarm_brier"]))
    for var in VARIANTS:
        v = a["variants"][var]
        print("   CoT %-6s   acc %.3f  brier %.4f | dBrier %+.4f [%+.4f, %+.4f] p=%.4f"
              % (var, v["cot_dir_acc"], v["cot_brier"],
                 *v["delta_brier_cot_minus_swarm"], v["p_2sided_brier"]))
    print()

for sc in ("matched", "all"):
    b = res["pooled"][sc]
    print("=" * 78)
    print("POOLED %s -- %d unit-pairs in %d event clusters"
          % (b["scope"], b["n_unit_pairs"], b["n_event_clusters"]))
    for var in VARIANTS:
        v = b["variants"][var]
        print("  CoT %-6s dBrier %+.4f [%+.4f, %+.4f]  clustered p=%.4f  (naive p=%.4f)"
              % (var, *v["delta_brier_cot_minus_swarm"],
                 v["p_2sided_brier_clustered"], v["p_2sided_brier_naive_unclustered"]))
        print("  %11s dAcc   %+.4f [%+.4f, %+.4f]  clustered p=%.4f"
              % ("", *v["delta_dir_acc_swarm_minus_cot"], v["p_2sided_dir_acc_clustered"]))
print("\nwrote cot_baseline_analysis.json")
