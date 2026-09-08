#!/usr/bin/env python3
"""Figure I -- evidence volume as the trigger for flat forecasts, and the evaluator
as their locus.

Panel A: flat-forecast rate by evidence_text length tercile, Mistral-7B, Evaluator J.
         Mistral is the clean test: no serving outage, so all 60 simulated units carry
         a real deliberation transcript and length varies without a confound.
Panel B: the same physical transcripts re-scored by every available pass. The units
         that drove Panel A stop being flat when only the instrument changes.

Writes figI_volume_mechanism.png next to this script.
"""
import json
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "completed_benches")
CAMPS = {
    "Llama-3.1-8B": "llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
    "Mistral-7B":   "mistral-7b-awq/ecnbench_20260715T080203247382Z",
}
C = {"Llama-3.1-8B": "#2a78d6", "Mistral-7B": "#eb6834", "Qwen2.5-7B": "#1baf7a"}
INK, INK2, INK3 = "#0b0b0b", "#52514e", "#8a8a87"
GRID = "#dcdcd8"
HEALTHY = {"C3", "S2", "S3", "S4", "S5", "S6"}   # Llama's six pre-outage events

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})

PASSES = [
    ("Evaluator J\n(July)",  "event_results.json"),
    ("Eval A\nread 1",       "event_results_evaluatorB_openrouter.json"),
    ("Eval A\nread 2",       "event_results_evaluatorA_repeat1.json"),
    ("Eval A\nread 3",       "event_results_evaluatorA_repeat2.json"),
    ("Eval A\nread 4",       "event_results_evaluatorA_repeat3.json"),
    ("Evaluator C\n(luna-pro)", "event_results_evaluatorC_gptlunapro.json"),
]

ED = json.load(open(os.path.join(HERE, "evidence_depth.json"), encoding="utf-8"))


def tidy(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.tick_params(length=3)


def is_flat(p):
    k = len(p)
    return max(abs(v - 1.0 / k) for v in p.values()) < 0.005


def flags(model, fname):
    path = os.path.join(BASE, CAMPS[model], fname)
    if not os.path.exists(path):
        return None
    out = {}
    for r in json.load(open(path, encoding="utf-8")):
        pr = r.get("probabilities") or {}
        if pr:
            uid = r.get("unit") or "%s_%s_r1" % (r["event_id"], r["condition"])
            out[uid] = is_flat(pr)
    return out


fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.6, 4.3))

# ----------------------------------------------------------------- PANEL A
evm = {r["unit"]: r for r in ED["Mistral-7B"]}
fj = flags("Mistral-7B", "event_results.json")
sim = sorted((evm[u]["ev_len"], u) for u in evm if evm[u]["cond"] in ("B", "C"))
n = len(sim)
terciles = [sim[:n // 3], sim[n // 3:2 * n // 3], sim[2 * n // 3:]]
labels, rates, notes = [], [], []
for lab, ch in zip(("shortest third", "middle third", "longest third"), terciles):
    fl = sum(1 for _, u in ch if fj.get(u))
    med = st.median(v for v, _ in ch)
    labels.append("%s\nmedian %s chars" % (lab, format(int(med), ",")))
    rates.append(100.0 * fl / len(ch))
    notes.append("%d/%d" % (fl, len(ch)))

xs = np.arange(3)
axA.bar(xs, rates, width=0.55, color=C["Mistral-7B"], edgecolor="none", zorder=3)
for x, r, nt in zip(xs, rates, notes):
    axA.text(x, r + 2.2, "%s\n%.0f%%" % (nt, r), ha="center", va="bottom",
             fontsize=9, color=INK)
axA.set_xticks(xs)
axA.set_xticklabels(labels, fontsize=8.5)
axA.set_ylim(0, 82)
axA.set_ylabel("Flat forecasts (% of units)")
axA.set_title("A.  Mistral-7B, Evaluator J: longer transcript, flatter output",
              fontsize=10, color=INK, pad=10, loc="left")
tidy(axA)

# ----------------------------------------------------------------- PANEL B
evl = {r["unit"]: r for r in ED["Llama-3.1-8B"]}
llama_hi = sorted(u for u, r in evl.items()
                  if r["cond"] in ("B", "C") and r["event"] in HEALTHY)
mistral_hi = [u for _, u in terciles[2]]

series = {
    "Llama-3.1-8B: 12 high-volume units": ("Llama-3.1-8B", llama_hi, C["Llama-3.1-8B"]),
    "Mistral-7B: 20 longest units":       ("Mistral-7B", mistral_hi, C["Mistral-7B"]),
}
w = 0.36
xs = np.arange(len(PASSES))
for i, (lab, (model, units, col)) in enumerate(series.items()):
    vals = []
    for _, fn in PASSES:
        f = flags(model, fn)
        got = [u for u in units if u in f] if f else []
        vals.append(100.0 * sum(1 for u in got if f[u]) / len(got) if got else np.nan)
    off = (i - 0.5) * w
    axB.bar(xs + off, vals, width=w, color=col, edgecolor="none",
            label=lab, zorder=3)
    for x, v in zip(xs + off, vals):
        if not np.isnan(v):
            axB.text(x, v + 2.2, "%.0f" % v, ha="center", va="bottom",
                     fontsize=8, color=INK2)

axB.set_xticks(xs)
axB.set_xticklabels([p[0] for p in PASSES], fontsize=8.5)
axB.set_ylim(0, 112)
axB.set_ylabel("Flat forecasts (% of those units)")
axB.set_title("B.  Same transcripts, different instrument", fontsize=10,
              color=INK, pad=10, loc="left")
axB.legend(frameon=False, fontsize=8.5, loc="upper right")
tidy(axB)

fig.tight_layout()
out = os.path.join(HERE, "figI_volume_mechanism.png")
fig.savefig(out, dpi=200)
print("wrote", out)
