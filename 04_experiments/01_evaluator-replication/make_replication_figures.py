#!/usr/bin/env python
"""ECN-BENCH: figures for the evaluator-replication section.

Every number is recomputed here from the per-unit records of the two datasets;
nothing is copied from the manuscript.

  Dataset J -- event_results.json                          (July, DeepSeek-R1-14B)
  Dataset A -- event_results_evaluatorB_openrouter.json     (Aug, deepseek-v4-flash-0731)

Run:  python make_replication_figures.py
"""
import json, math, os, sys
import statistics as st
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "MiroFish-Offline" / "backend"))
from app.benchmarks.scoring import brier_score  # noqa: E402

CAMPS = {
    "Llama-3.1-8B": "completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
    "Mistral-7B":   "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z",
    "Qwen2.5-7B":   "completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z",
}
# FILE_J points at the frozen 2026-08-13 archive, not the live event_results.json:
# Llama's live file now contains the 2026-08-16 outage repair (Section~\ref{sec:outage})
# for 24/30 events, sourced from the same deepseek-v4-flash-0731/OpenRouter pass as
# FILE_A. Reading live event_results.json as "J" for those events would compare A
# against a near-copy of itself rather than against the original DeepSeek-R1-14B pass.
FILE_J_PER_MODEL = {
    "Llama-3.1-8B": "archive_pre_session_repairs/event_results.json.bak_20260813_192149",
    "Mistral-7B":   "archive_pre_session_repairs/event_results.json.bak_20260813_192149",
    "Qwen2.5-7B":   "archive_pre_session_repairs/event_results.json.bak_20260813_185718",
}
FILE_A = "event_results_evaluatorB_openrouter.json"

# Same validated categorical palette as make_audit_figures.py, so the two figure
# sets read as one system.
C = {"Llama-3.1-8B": "#2a78d6", "Mistral-7B": "#eb6834", "Qwen2.5-7B": "#1baf7a"}
INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
C_J, C_A = "#8a8a87", "#2a78d6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def unit_metrics(row):
    p, gt = row.get("probabilities") or {}, row.get("ground_truth")
    if not p or not gt:
        return None
    k = len(p)
    return {
        "brier": brier_score(p, gt),
        "modal": max(p.values()),
        "uniform": max(abs(v - 1.0 / k) for v in p.values()) < 0.005,
    }


def load(fname_or_per_model):
    R = {}
    for model, d in CAMPS.items():
        fname = fname_or_per_model[model] if isinstance(fname_or_per_model, dict) else fname_or_per_model
        rows = json.loads((HERE / d / fname).read_text(encoding="utf-8"))
        R[model] = {}
        for r in rows:
            m = unit_metrics(r)
            if m:
                R[model][(r["event_id"], r["condition"])] = m
    return R


J, A = load(FILE_J_PER_MODEL), load(FILE_A)
EV = sorted({e for (e, c) in J["Llama-3.1-8B"]})

# Scope separation (see the replication table in the paper).  The J-vs-A contrast is an
# instrument comparison only where both passes read byte-identical text.  That holds
# for all 30 events of Mistral and Qwen, but for Llama only on the six events the
# backend outage never touched; its other 24 were re-simulated 2026-08-16 and have no
# July scoring at all.
PAIRED_LLAMA = ["C3", "S2", "S3", "S4", "S5", "S6"]
PAIRED = {"Llama-3.1-8B": PAIRED_LLAMA, "Mistral-7B": EV, "Qwen2.5-7B": EV}
RECOVERY = [e for e in EV if e not in PAIRED_LLAMA]          # Llama's 24 re-simulated
OR_LLAMA = A["Llama-3.1-8B"]                                  # v4-flash on those 24


def boot_ci(xs, n=20000, seed=7):
    import random
    r = random.Random(seed)
    reps = sorted(st.mean(r.choices(xs, k=len(xs))) for _ in range(n))
    return st.mean(xs), reps[int(0.025 * n)], reps[int(0.975 * n)]


def tidy(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.tick_params(length=3)


# --------------------------------------------------------------- FIGURE R1
def fig_replication():
    """Panel A: the instrument, at fixed input.  Panel B: the model, at fixed instrument."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.4))

    # -- Panel A: flat-forecast counts per condition, PAIRED scope only
    conds = ["A", "B", "C"]
    clabel = {"A": "A (No-Sim)", "B": "B (With-Sim)", "C": "C (Null)"}
    xs = np.arange(3)
    w = 0.34
    n_units = sum(len(PAIRED[m]) for m in CAMPS)
    for i, (R, col, lab) in enumerate(
        ((J, C_J, "Evaluator J  DeepSeek-R1-14B (Jul, unconstrained)"),
         (A, C_A, "Evaluator A  deepseek-v4-flash (Aug, JSON-enforced)"))):
        vals = [sum(R[m][(e, c)]["uniform"] for m in CAMPS for e in PAIRED[m]) for c in conds]
        pos = xs + (i - 0.5) * w
        ax1.bar(pos, vals, w * 0.9, color=col, label=lab, edgecolor="white",
                linewidth=1.2, zorder=2)
        for p_, v in zip(pos, vals):
            ax1.annotate(f"{v}/{n_units}", (p_, v), xytext=(0, 5), textcoords="offset points",
                         ha="center", fontsize=8.6, color=INK)
    ax1.set_xticks(xs)
    ax1.set_xticklabels([clabel[c] for c in conds], fontsize=9.2)
    ax1.set_ylabel("Units returning an exactly flat\n(uniform) distribution")
    ax1.set_ylim(0, 24)
    ax1.set_title("A.  Same transcripts, different evaluator: the flat forecasts vanish",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    ax1.annotate("paired scope: Mistral and Qwen over 30 events each, Llama over its 6\n"
                 f"outage-free events — {n_units} units per condition, both passes "
                 "reading byte-identical text",
                 (0.0, -0.20), xycoords="axes fraction", fontsize=8.1, color=INK2, va="top")
    tidy(ax1)
    ax1.legend(frameon=False, fontsize=8.4, loc="upper left", handlelength=1.1)

    # -- Panel B: per-event susceptibility on Llama's 24 re-simulated events
    marg = [(e, OR_LLAMA[(e, "C")]["brier"] - OR_LLAMA[(e, "B")]["brier"]) for e in RECOVERY]
    # bootstrap on the event-sorted order, so the interval matches the paper's table
    mean, lo, hi = boot_ci([v for _, v in marg])
    marg.sort(key=lambda t: t[1])
    ys = np.arange(len(marg))
    vals = [v for _, v in marg]
    cols = [C["Llama-3.1-8B"] if v > 0 else "#c2410c" for v in vals]
    ax2.barh(ys, vals, 0.74, color=cols, edgecolor="white", linewidth=0.8, zorder=2)
    ax2.axvline(0, color=INK3, lw=0.9, zorder=3)
    ax2.axvspan(lo, hi, color=INK, alpha=0.07, zorder=0)
    ax2.axvline(mean, color=INK, lw=1.4, ls=(0, (4, 2)), zorder=4)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([e for e, _ in marg], fontsize=7.2)
    ax2.set_ylim(-0.8, len(marg) - 0.2)
    ax2.set_xlabel("Susceptibility margin  $BS_C - BS_B$   (positive = the null injection hurt)")
    ax2.set_title("B.  The recovery scope: no detectable sensitivity to what was injected",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    ax2.annotate(f"mean {mean:+.3f}   95% CI [{lo:+.3f}, {hi:+.3f}]\n"
                 f"{sum(v > 0 for v in vals)}/{len(vals)} events positive",
                 (0.03, 0.965), xycoords="axes fraction", fontsize=9, color=INK, va="top")
    ax2.annotate("recovery scope: Llama-3.1-8B, 24 re-simulated events, all three\n"
                 "conditions scored by deepseek-v4-flash-0731",
                 (0.0, -0.20), xycoords="axes fraction", fontsize=8.1, color=INK2, va="top")
    for sp in ("top", "right"):
        ax2.spines[sp].set_visible(False)
    ax2.set_axisbelow(True)
    ax2.xaxis.grid(True, color=GRID, lw=0.6)
    ax2.tick_params(axis="y", length=0)

    fig.tight_layout()
    out = HERE / "figR1_evaluator_replication.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.name)


# --------------------------------------------------------------- FIGURE R2
def fig_instrument_noise():
    """How much of the measured signal is the instrument?"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.3))

    # -- left: per-unit Brier, J vs A
    for m in CAMPS:
        keys = [k for k in J[m] if k in A[m] and k[0] in PAIRED[m]]
        ax1.plot([J[m][k]["brier"] for k in keys], [A[m][k]["brier"] for k in keys],
                 "o", ms=5, color=C[m], mec="white", mew=0.8, alpha=0.85, label=m, zorder=3)
    lim = [0, 2.05]
    ax1.plot(lim, lim, color=INK3, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax1.annotate("perfect agreement", (1.45, 1.52), fontsize=8.4, color=INK2, rotation=37)
    allk = [(m, k) for m in CAMPS for k in J[m] if k in A[m] and k[0] in PAIRED[m]]
    bj = [J[m][k]["brier"] for m, k in allk]
    ba = [A[m][k]["brier"] for m, k in allk]
    mx, my = st.mean(bj), st.mean(ba)
    r = (sum((a - mx) * (b - my) for a, b in zip(bj, ba))
         / math.sqrt(sum((a - mx) ** 2 for a in bj) * sum((b - my) ** 2 for b in ba)))
    ax1.annotate(f"$r$ = {r:+.3f}   $n$ = {len(allk)}", (0.04, 0.93), xycoords="axes fraction",
                 fontsize=10.5, color=INK, fontweight="bold")
    ax1.set_xlim(lim); ax1.set_ylim(lim)
    ax1.set_xlabel("Per-unit Brier, evaluator J (July)")
    ax1.set_ylabel("Per-unit Brier, evaluator A (Aug)")
    ax1.set_title("A.  Two evaluators, byte-identical input: only moderate agreement",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax1); ax1.xaxis.grid(True, color=GRID, lw=0.6)
    ax1.legend(frameon=False, fontsize=8.5, loc="lower right", handlelength=1.0)

    # -- right: Condition A is byte-identical across campaigns -> triplicate re-read
    spreads = []
    for e in EV:
        vals = [A[m][(e, "A")]["brier"] for m in CAMPS if (e, "A") in A[m]]
        if len(vals) == 3:
            spreads.append((e, max(vals) - min(vals)))
    spreads.sort(key=lambda t: t[1])
    ys = np.arange(len(spreads))
    ax2.barh(ys, [s for _, s in spreads], 0.72, color=C_A, edgecolor="white",
             linewidth=0.8, zorder=2)
    ident = sum(1 for _, s in spreads if s < 1e-9)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([e for e, _ in spreads], fontsize=7.4)
    ax2.set_xlabel("Brier spread across three re-reads of byte-identical input")
    ax2.set_title("B.  The same evaluator, same input, temperature 0: not reproducible",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    ax2.annotate(f"{ident}/{len(spreads)} events reproduced exactly\n"
                 f"mean spread {st.mean(s for _, s in spreads):.3f}   "
                 f"max {max(s for _, s in spreads):.3f}",
                 (0.35, 0.10), xycoords="axes fraction", fontsize=9, color=INK)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.set_axisbelow(True); ax2.xaxis.grid(True, color=GRID, lw=0.6)
    ax2.tick_params(axis="y", length=0)
    ax2.set_ylim(-0.8, len(spreads) - 0.2)

    fig.tight_layout()
    out = HERE / "figR2_instrument_noise.png"
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out.name)


if __name__ == "__main__":
    fig_replication()
    fig_instrument_noise()
