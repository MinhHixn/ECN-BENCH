#!/usr/bin/env python3
"""Generate publication-quality figure: Single-Agent CoT Baseline vs Multi-Agent Swarm on 17 Clean Events.
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

with open(os.path.join(ROOT, 'paired_cot_swarm_detailed_stats.json'), 'r') as f:
    data = json.load(f)

INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.3))

models = ["Llama-3.1-8B", "Mistral-8B", "Qwen2.5-7B", "Qwen-14B", "Pooled"]
m_labels = ["Llama-3.1\n8B", "Mistral\n8B", "Qwen2.5\n7B", "Qwen\n14B", "Pooled\n(68 pairs)"]

# Directional Accuracy
cot_acc = [r["cot_acc"] * 100 for r in data["models"]]
sw_acc = [r["sw_acc"] * 100 for r in data["models"]]
cot_acc.append(np.mean([r["cot_acc"] for r in data["models"]]) * 100)
sw_acc.append(np.mean([r["sw_acc"] for r in data["models"]]) * 100)

xs = np.arange(len(models))
w = 0.36

ax1.bar(xs - w/2, cot_acc, width=w, color="#4a90e2", label="Single-Agent CoT + RAG", zorder=3)
ax1.bar(xs + w/2, sw_acc, width=w, color="#8a5cd1", label="Multi-Agent Swarm (N=300, R=60)", zorder=3)
ax1.axhline(34.6, color=INK2, ls="--", lw=1.1, zorder=4, label="Chance baseline (34.6%)")

for x, v in zip(xs - w/2, cot_acc):
    ax1.text(x, v + 1.5, "%.1f" % v, ha="center", fontsize=8.2, color=INK)
for x, v in zip(xs + w/2, sw_acc):
    ax1.text(x, v + 1.5, "%.1f" % v, ha="center", fontsize=8.2, color=INK)

ax1.set_xticks(xs)
ax1.set_xticklabels(m_labels, fontsize=8.5)
ax1.set_ylim(0, 110)
ax1.set_ylabel("Directional Accuracy (%)")
ax1.set_title("A. Directional Accuracy: Single-Agent CoT vs Multi-Agent Swarm", fontsize=9.8, pad=10, loc="left")
ax1.legend(frameon=False, fontsize=8.0, loc="lower left")
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)
ax1.set_axisbelow(True); ax1.yaxis.grid(True, color=GRID, lw=0.6)

# Brier Scores
cot_br = [r["cot_brier"] for r in data["models"]]
sw_br = [r["sw_brier"] for r in data["models"]]
cot_br.append(np.mean([r["cot_brier"] for r in data["models"]]))
sw_br.append(np.mean([r["sw_brier"] for r in data["models"]]))

ax2.bar(xs - w/2, cot_br, width=w, color="#4a90e2", alpha=0.85, label="Single-Agent CoT Brier", zorder=3)
ax2.bar(xs + w/2, sw_br, width=w, color="#8a5cd1", alpha=0.85, label="Multi-Agent Swarm Brier", zorder=3)

for x, v in zip(xs - w/2, cot_br):
    ax2.text(x, v + 0.015, "%.3f" % v, ha="center", fontsize=8.0, color=INK)
for x, v in zip(xs + w/2, sw_br):
    ax2.text(x, v + 0.015, "%.3f" % v, ha="center", fontsize=8.0, color=INK)

ax2.set_xticks(xs)
ax2.set_xticklabels(m_labels, fontsize=8.5)
ax2.set_ylim(0, 0.65)
ax2.set_ylabel("Brier Score (lower = better calibration)")
ax2.set_title("B. Brier Calibration Error (Lower is Better)", fontsize=9.8, pad=10, loc="left")
ax2.legend(frameon=False, fontsize=8.0, loc="upper right")
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)
ax2.set_axisbelow(True); ax2.yaxis.grid(True, color=GRID, lw=0.6)

fig.tight_layout()
out = os.path.join(ROOT, "figK_cot_vs_swarm.png")
fig.savefig(out, dpi=200)
print(f"Wrote {out}")
