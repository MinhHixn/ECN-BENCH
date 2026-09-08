#!/usr/bin/env python3
"""Predictive-signal analysis for ECN-BENCH Section sec:predictive_signal.

Asks the one question the benchmark can answer affirmatively: do the simulated
forecasts carry information about how these social events actually resolved?

Two tests, both on the 20 contamination-clean events common to all four campaigns,
both using the per-unit mean of the available Evaluator A reads (the same basis as
Table tab:four_model_clean, not a single pass):

  1. Is Condition B directional accuracy above chance? Chance is 1/K per event and
     K ranges 2-9 here, so the null is a Poisson binomial, not a coin flip.
  2. Is the swarm sensitive to the CONTENT of what it deliberates over? Condition C
     runs the identical machinery on structurally matched but topically unrelated
     evidence, so B - C isolates the contribution of relevant information and never
     touches the shared Condition A record.

Writes predictive_signal_analysis.json and figJ_predictive_signal.png.
"""
import json
import math
import os
import random
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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
# permanently-failed OpenRouter reads that left a stale copy of an earlier pass in
# place rather than being absent; counting them would deflate spread (see manifest)
KNOWN_GAPS = {
    ("Qwen2.5-7B",  "event_results_evaluatorA_repeat3.json"): {"T3_C_r1", "C9_A_r1", "C13_C_r1"},
    ("Qwen2.5-14B", "event_results_evaluatorA_repeat2.json"): {"T1_C_r1"},
}
# Updated 2026-08-21: Qwen2.5-14B's 6 wrong-topic exclusions (T3,T4,T5,T6,C6,T8)
# were re-simulated against the correct root catalogue and rescored, bringing it
# to 30/30 like the other 3 models. That restores T6, C6, T8 (part of the 20
# release-date-clean events, CLEAN_20 in build_reproducibility_analysis.py) to the
# set common to all four campaigns, so the "clean 17" grows to the full clean 20.
CLEAN20 = ["C1", "C5", "C6", "C8", "C9", "C11", "C13", "C14", "C15",
           "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T6", "T8", "T9"]

C = {"Llama-3.1-8B": "#2a78d6", "Mistral-7B": "#eb6834",
     "Qwen2.5-7B": "#1baf7a", "Qwen2.5-14B": "#8a5cd1"}
INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def load(model):
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


def hit(rec):
    mx = max(rec["probs"].values())
    tied = [o for o, v in rec["probs"].items() if math.isclose(v, mx, abs_tol=1e-12)]
    gt = str(rec["gt"]).casefold()
    if len(tied) == 1:
        return 1.0 if tied[0].casefold() == gt else 0.0
    return 1.0 / len(tied) if any(t.casefold() == gt for t in tied) else 0.0


def brier(rec):
    return sum((v - (1.0 if o == rec["gt"] else 0.0)) ** 2 for o, v in rec["probs"].items())


def poisson_binomial_sf(k, ps):
    """P(X >= k), X = sum of independent Bernoulli(ps[i]). Exact."""
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


DATA = {m: load(m) for m in CAMPS}
res = {"description": __doc__.strip().split("\n")[0],
       "clean_events": CLEAN20, "models": {}, "pooled": {}}

pool_hits, pool_ps, pool_dbr, pool_dda = [], [], [], []
for m in CAMPS:
    ev = [e for e in CLEAN20 if (e, "B") in DATA[m] and (e, "C") in DATA[m]]
    hb = [hit(DATA[m][(e, "B")]) for e in ev]
    hc = [hit(DATA[m][(e, "C")]) for e in ev]
    ha = [hit(DATA[m][(e, "A")]) for e in ev if (e, "A") in DATA[m]]
    ps = [1.0 / DATA[m][(e, "B")]["k"] for e in ev]
    dbr = [brier(DATA[m][(e, "C")]) - brier(DATA[m][(e, "B")]) for e in ev]
    dda = [b - c for b, c in zip(hb, hc)]
    pool_hits += hb; pool_ps += ps; pool_dbr += dbr; pool_dda += dda
    mb, lb, hbb = boot_ci(dbr)
    md, ld, hd = boot_ci(dda)
    res["models"][m] = {
        "n_events": len(ev),
        "dir_acc_B": round(st.mean(hb), 4),
        "dir_acc_C": round(st.mean(hc), 4),
        "dir_acc_A": round(st.mean(ha), 4) if ha else None,
        "chance": round(st.mean(ps), 4),
        "exact_poisson_binomial_p_B_vs_chance": poisson_binomial_sf(sum(hb), ps),
        "brier_B": round(st.mean(brier(DATA[m][(e, "B")]) for e in ev), 4),
        "brier_C": round(st.mean(brier(DATA[m][(e, "C")]) for e in ev), 4),
        "delta_brier_C_minus_B": [round(mb, 4), round(lb, 4), round(hbb, 4)],
        "delta_dir_acc_B_minus_C": [round(md, 4), round(ld, 4), round(hd, 4)],
    }

mb, lb, hbb = boot_ci(pool_dbr)
md, ld, hd = boot_ci(pool_dda)
res["pooled"] = {
    "n_units": len(pool_hits),
    "dir_acc_B": round(sum(pool_hits) / len(pool_hits), 4),
    "chance": round(st.mean(pool_ps), 4),
    "exact_poisson_binomial_p": poisson_binomial_sf(sum(pool_hits), pool_ps),
    "delta_brier_C_minus_B": [round(mb, 4), round(lb, 4), round(hbb, 4)],
    "delta_dir_acc_B_minus_C": [round(md, 4), round(ld, 4), round(hd, 4)],
    "events_all_four_models_correct": [
        e for e in CLEAN20
        if all(hit(DATA[m][(e, "B")]) == 1.0 for m in CAMPS if (e, "B") in DATA[m])],
    "events_all_four_models_wrong": [
        e for e in CLEAN20
        if all(hit(DATA[m][(e, "B")]) == 0.0 for m in CAMPS if (e, "B") in DATA[m])],
}

with open(os.path.join(HERE, "predictive_signal_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)
print("wrote predictive_signal_analysis.json")

# ------------------------------------------------------------------ FIGURE
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.3))

models = list(CAMPS)
xs = np.arange(len(models))
w = 0.36
accB = [res["models"][m]["dir_acc_B"] * 100 for m in models]
accC = [res["models"][m]["dir_acc_C"] * 100 for m in models]
ax1.bar(xs - w/2, accB, width=w, color=[C[m] for m in models], zorder=3,
        label="Condition B (relevant evidence)")
ax1.bar(xs + w/2, accC, width=w, color=[C[m] for m in models], alpha=0.42, zorder=3,
        label="Condition C (unrelated evidence)")
ax1.axhline(res["pooled"]["chance"] * 100, color=INK2, ls="--", lw=1.1, zorder=4,
            label="chance (mean $1/K$) = %.1f%%" % (res["pooled"]["chance"] * 100))
for x, v in zip(xs - w/2, accB):
    ax1.text(x, v + 1.6, "%.0f" % v, ha="center", fontsize=8.5, color=INK)
for x, v in zip(xs + w/2, accC):
    ax1.text(x, v + 1.6, "%.0f" % v, ha="center", fontsize=8.5, color=INK2)
ax1.set_xticks(xs)
ax1.set_xticklabels([m.replace("-", "-\n", 1) for m in models], fontsize=8.5)
ax1.set_ylim(0, 108)
ax1.set_ylabel("Directional accuracy (%)")
ax1.set_title("A.  The swarm identifies the realised outcome far above chance",
              fontsize=10, color=INK, pad=10, loc="left")
ax1.legend(frameon=False, fontsize=8.2, loc="lower left", ncol=1)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)
ax1.set_axisbelow(True); ax1.yaxis.grid(True, color=GRID, lw=0.6); ax1.tick_params(length=3)

rows = models + ["Pooled (%d units)" % res["pooled"]["n_units"]]
ys = np.arange(len(rows))[::-1]
for y, m in zip(ys, rows):
    d = res["pooled"] if m.startswith("Pooled") else res["models"][m]
    mu, lo, hi = d["delta_brier_C_minus_B"]
    col = INK if m.startswith("Pooled") else C[m]
    ax2.plot([lo, hi], [y, y], color=col, lw=2.4, solid_capstyle="round", zorder=3)
    ax2.plot([mu], [y], "o", color=col, ms=7, zorder=4)
    ax2.text(hi + 0.012, y, "%+.3f [%+.3f, %+.3f]" % (mu, lo, hi),
             va="center", fontsize=8.5, color=INK2)
ax2.axvline(0, color=INK2, lw=1.0, ls="--", zorder=2)
ax2.set_yticks(ys); ax2.set_yticklabels(rows, fontsize=9)
ax2.set_xlim(-0.16, 0.62)
ax2.set_xlabel(r"Brier gained from relevant evidence:  BS$_C$ $-$ BS$_B$")
ax2.set_title("B.  Content sensitivity, 95% bootstrap CI", fontsize=10,
              color=INK, pad=10, loc="left")
for s in ("top", "right", "left"):
    ax2.spines[s].set_visible(False)
ax2.set_axisbelow(True); ax2.xaxis.grid(True, color=GRID, lw=0.6); ax2.tick_params(length=3)

fig.tight_layout()
out = os.path.join(HERE, "figJ_predictive_signal.png")
fig.savefig(out, dpi=200)
print("wrote", out)
