#!/usr/bin/env python3
"""Figure M: single-agent RAG+CoT baseline vs the multi-agent swarm on the contamination-clean events.

Panel A is a paired dumbbell (one row per arm, both arms' Brier on a common axis) rather
than side-by-side bars: the quantity of interest is the GAP within a row, and a dumbbell
encodes the gap as length instead of asking the reader to difference two bar heights.
Panel B is the forest plot of that gap with its interval, in the same idiom as Figure J.

Reads cot_baseline_analysis.json; writes figM_cot_vs_swarm.png.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(HERE, "cot_baseline_analysis.json"), encoding="utf-8"))

# same categorical order and hues as Figures F-L; validated for CVD separation
C = {"Llama-3.1-8B": "#2a78d6", "Mistral-8B": "#eb6834",
     "Qwen2.5-7B": "#1baf7a", "Qwen3-14B": "#8a5cd1"}
INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})

arms = res["arms"]
matched = [a for a in arms if a["identity_matched"]]
crossm = [a for a in arms if not a["identity_matched"]]
ordered = matched + crossm            # matched arms first, then the cross-model ones
VAR = "single"                        # primary: the expected cost of ONE CoT call

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.6))

# ------------------------------------------------------------------ PANEL A
ys = np.arange(len(ordered))[::-1].astype(float)
ys[len(matched):] -= 0.55             # visual gap between the two scopes

for y, a in zip(ys, ordered):
    col = C[a["cot_model"]]
    cot_b = a["variants"][VAR]["cot_brier"]
    sw_b = a["swarm_brier"]
    ax1.plot([cot_b, sw_b], [y, y], color=col, lw=2.0, alpha=0.5,
             solid_capstyle="round", zorder=2)
    ax1.plot([cot_b], [y], marker="o", ms=9, mfc="white", mec=col, mew=2.0, zorder=3)
    ax1.plot([sw_b], [y], marker="o", ms=9, mfc=col, mec="white", mew=1.4, zorder=3)
    lo, hi = (cot_b, sw_b) if cot_b < sw_b else (sw_b, cot_b)
    ax1.text(lo - 0.012, y, "%.3f" % lo, ha="right", va="center", fontsize=8.2, color=INK2)
    ax1.text(hi + 0.012, y, "%.3f" % hi, ha="left", va="center", fontsize=8.2, color=INK)

ax1.axhline(ys[len(matched) - 1] - 0.28, color=GRID, lw=0.9, zorder=1)
ax1.text(0.052, ys[0] + 0.42, "identity-matched", fontsize=8.0, color=INK2, style="italic")
ax1.text(0.052, ys[len(matched)] + 0.42, "cross-model (different checkpoint)",
         fontsize=8.0, color=INK2, style="italic")

ax1.set_yticks(ys)
ax1.set_yticklabels(["%s\n%s" % (a["cot_model"], "vs " + a["swarm_campaign"] + " swarm")
                     for a in ordered], fontsize=8.4)
ax1.set_ylim(ys[-1] - 1.85, ys[0] + 0.85)   # bottom band reserved for the legend
ax1.set_xlim(0.04, 0.66)
ax1.set_xlabel("Brier score on the %d clean events (lower = better)" % len(res["clean_events"]))
ax1.set_title("A.  One CoT call is not beaten by the swarm on any matched arm",
              fontsize=10, color=INK, pad=10, loc="left")
ax1.plot([], [], marker="o", ls="none", ms=8, mfc="white", mec=INK2, mew=1.8,
         label="single-agent RAG+CoT (one call)")
ax1.plot([], [], marker="o", ls="none", ms=8, mfc=INK2, mec="white",
         label="multi-agent swarm, Condition B ($N{=}300$, $R{=}60$)")
ax1.legend(frameon=False, fontsize=8.2, loc="lower left", handletextpad=0.4,
           borderaxespad=0.3)
for s in ("top", "right", "left"):
    ax1.spines[s].set_visible(False)
ax1.set_axisbelow(True)
ax1.xaxis.grid(True, color=GRID, lw=0.6)
ax1.tick_params(axis="y", length=0)
ax1.tick_params(axis="x", length=3)

# ------------------------------------------------------------------ PANEL B
rows = []
for a in matched:
    rows.append((a["cot_model"], C[a["cot_model"]], a["variants"], False))
pm_block = res["pooled"]["matched"]
pm = pm_block["variants"]
rows.append(("Pooled, matched\n(%d pairs / %d events)" %
             (pm_block["n_unit_pairs"], pm_block["n_event_clusters"]), INK, pm, True))
for a in crossm:
    rows.append((a["cot_model"] + " *", C[a["cot_model"]], a["variants"], False))
pa_block = res["pooled"]["all"]
pa = pa_block["variants"]
rows.append(("Pooled, all four *\n(%d pairs / %d events)" %
             (pa_block["n_unit_pairs"], pa_block["n_event_clusters"]), INK, pa, True))

ys2 = np.arange(len(rows))[::-1].astype(float)
ys2[3:] -= 0.5

for y, (label, col, var, is_pool) in zip(ys2, rows):
    mu, lo, hi = var[VAR]["delta_brier_cot_minus_swarm"]
    ax2.plot([lo, hi], [y, y], color=col, lw=2.0 if is_pool else 1.6,
             alpha=0.95 if is_pool else 0.75, solid_capstyle="round", zorder=3)
    ax2.plot([mu], [y], marker="o", ms=8.5 if is_pool else 7.5, mfc=col,
             mec="white", mew=1.3, zorder=4)
    ax2.plot([var["ens3"]["delta_brier_cot_minus_swarm"][0]], [y], marker="D", ms=5.0,
             mfc="none", mec=col, mew=1.1, zorder=4)
    ax2.text(0.30, y, "%+.3f [%+.3f, %+.3f]" % (mu, lo, hi), fontsize=8.0,
             va="center", color=INK if is_pool else INK2,
             fontweight="bold" if is_pool else "normal")

ax2.axvline(0, color=INK2, lw=1.0, ls="--", zorder=2)
ax2.axhline(ys2[2] - 0.25, color=GRID, lw=0.9, zorder=1)
ax2.set_yticks(ys2)
ax2.set_yticklabels([r[0] for r in rows], fontsize=8.3)
ax2.set_ylim(ys2[-1] - 1.85, ys2[0] + 0.7)  # bottom band reserved for the legend
ax2.set_xlim(-0.55, 0.63)
ax2.set_xticks([-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2])
ax2.set_xlabel(r"$BS_{\mathrm{CoT}} - BS_{\mathrm{swarm}}$   (positive $\Rightarrow$ swarm better)")
ax2.set_title("B.  No difference by the primary test; two intervals favour CoT",
              fontsize=10, color=INK, pad=10, loc="left")
ax2.plot([], [], marker="o", ls="none", ms=7.5, mfc=INK2, mec="white",
         label="one CoT call, 95% CI")
ax2.plot([], [], marker="D", ls="none", ms=5.0, mfc="none", mec=INK2,
         label="3-call CoT ensemble (point only)")
ax2.legend(frameon=False, fontsize=8.0, loc="lower left", handletextpad=0.4,
           borderaxespad=0.3)
for s in ("top", "right", "left"):
    ax2.spines[s].set_visible(False)
ax2.set_axisbelow(True)
ax2.xaxis.grid(True, color=GRID, lw=0.6)
ax2.tick_params(axis="y", length=0)
ax2.tick_params(axis="x", length=3)

fig.text(0.505, 0.005,
         "* cross-model arm: the CoT model is a different checkpoint from the campaign it "
         "is compared against, so it is not a paired contrast.",
         fontsize=7.6, color=INK2, ha="center")

fig.tight_layout(rect=(0, 0.035, 1, 1))
out = os.path.join(HERE, "figM_cot_vs_swarm.png")
fig.savefig(out, dpi=200)
print("wrote", out)
