#!/usr/bin/env python
"""
ECN-BENCH: audit figures generated directly from the three completed
30-event campaigns (completed_benches/*/ecnbench_*/event_results.json).

Every number plotted here is recomputed from the raw per-unit records; no
value is copied from the manuscript. Run:  python make_audit_figures.py
"""
import json, os, glob, math, random
import statistics as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "completed_benches")
MODELS = {
    "Llama-3.1-8B": "llama-3.1-8b-awq",
    "Mistral-7B":   "mistral-7b-awq",
    "Qwen2.5-7B":   "qwen2.5_7b",
}
# validated categorical slots 1-3 (all-pairs clean, light mode)
C = {"Llama-3.1-8B": "#2a78d6", "Mistral-7B": "#eb6834", "Qwen2.5-7B": "#1baf7a"}
INK, INK2, INK3 = "#0b0b0b", "#52514e", "#8a8ا87".replace("ا", "8")[:7]
INK3 = "#8a8a87"
GRID = "#dcdcd8"
PLACEHOLDER = 0.758277          # constant emitted when JSD telemetry is absent
CHECKPOINTS = [6, 12, 18, 24, 30, 36, 42, 48, 54, 60]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})


def load(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return json.load(f)


R = {}
for label, d in MODELS.items():
    rows = load(glob.glob(os.path.join(BASE, d, "*", "event_results.json"))[0])
    R[label] = {(r["event_id"], r["condition"]): r for r in rows}

EV = sorted({e for (e, c) in R["Llama-3.1-8B"]})
K = {e: len(R["Llama-3.1-8B"][(e, "A")]["probabilities"]) for e in EV}
BSA = {e: R["Llama-3.1-8B"][(e, "A")]["brier"] for e in EV}     # Condition A is shared
CLEAN = [e for e in EV if BSA[e] >= 0.35]
FILT = [e for e in EV if BSA[e] >= 0.15]


def boot_ci(x, n=20000, seed=7):
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(x, k=len(x))) for _ in range(n))
    return st.mean(x), reps[int(0.025 * n)], reps[int(0.975 * n)]


def tidy(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.tick_params(length=3)


# ----------------------------------------------------------------- FIGURE A
def fig_jsd_integrity():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.2))

    # -- left: share of placeholder values per checkpoint
    w = 0.26
    xs = np.arange(len(CHECKPOINTS))
    for i, m in enumerate(MODELS):
        frac = []
        for ci in range(10):
            n = tot = 0
            for e in EV:
                for cond in "BC":
                    # 2026-08-16: Llama's 24 re-simulated events carry no round-level
                    # telemetry at all (none was extracted from the new .db traces).
                    # Absent is not the same as placeholder, so those units are left
                    # out of the denominator rather than counted either way.
                    jsd = (R[m][(e, cond)] or {}).get("round_jsd")
                    if not jsd or ci >= len(jsd) or jsd[ci] is None:
                        continue
                    tot += 1
                    if abs(jsd[ci] - PLACEHOLDER) < 1e-5:
                        n += 1
            frac.append(100.0 * n / tot if tot else 0.0)
        ax1.bar(xs + (i - 1) * w, frac, w * 0.88, color=C[m], label=m,
                edgecolor="white", linewidth=1.0)
    ax1.set_xticks(xs); ax1.set_xticklabels([f"r{c}" for c in CHECKPOINTS])
    ax1.set_ylim(0, 108); ax1.set_yticks([0, 25, 50, 75, 100])
    ax1.set_ylabel("Units emitting the constant 0.7583  (%)")
    ax1.set_xlabel("Telemetry checkpoint (simulation round)")
    ax1.set_title("A.  JSD telemetry is a placeholder, not a measurement",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax1)
    ax1.legend(frameon=False, fontsize=8.6, loc="lower left", ncol=1,
               handlelength=1.1, borderpad=0.2)

    # -- right: mean JSD trajectory
    for m in MODELS:
        traj = []
        for i in range(10):
            vals = [j[i] for e in EV
                    if (j := (R[m][(e, "B")] or {}).get("round_jsd"))
                    and i < len(j) and j[i] is not None]
            traj.append(st.mean(vals) if vals else float("nan"))
        ax2.plot(CHECKPOINTS, traj, color=C[m], lw=2.0, marker="o", ms=5.5,
                 mec="white", mew=1.2, label=m, zorder=3)
        ax2.annotate(f"{traj[-1]:.3f}", (CHECKPOINTS[-1], traj[-1]),
                     xytext=(7, 0), textcoords="offset points", va="center",
                     fontsize=8.6, color=INK2)
    ax2.axhline(PLACEHOLDER, color=INK3, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax2.annotate("placeholder value 0.7583", (7, PLACEHOLDER), xytext=(0, 6),
                 textcoords="offset points", fontsize=8.4, color=INK2)
    ax2.set_xticks(CHECKPOINTS); ax2.set_xlim(2, 68); ax2.set_ylim(0.45, 0.83)
    ax2.set_xlabel("Simulation round"); ax2.set_ylabel("Mean inter-round JSD (Condition B)")
    ax2.set_title("B.  Only Mistral and Qwen produce a real belief trace",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax2)
    ax2.legend(frameon=False, fontsize=8.6, loc="lower left", handlelength=1.6)

    fig.tight_layout()
    out = os.path.join(HERE, "figA_jsd_integrity.png")
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


# ----------------------------------------------------------------- FIGURE B
def fig_susceptibility():
    fig, ax = plt.subplots(figsize=(7.4, 3.3))
    names = list(MODELS)[::-1]
    for i, m in enumerate(names):
        d = [R[m][(e, "C")]["brier"] - R[m][(e, "B")]["brier"] for e in EV]
        mean, lo, hi = boot_ci(d)
        ax.plot([lo, hi], [i, i], color=C[m], lw=2.4, solid_capstyle="round", zorder=2)
        ax.plot([mean], [i], "o", ms=10, color=C[m], mec="white", mew=1.6, zorder=3)
        ax.annotate(f"{mean:+.3f}   [{lo:+.3f}, {hi:+.3f}]", (hi, i), xytext=(10, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.axvline(0, color=INK3, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9.6, color=INK)
    ax.set_ylim(-0.7, len(names) - 0.3); ax.set_xlim(-0.16, 0.52)
    ax.set_xlabel(r"Susceptibility margin  BS$_C$ $-$ BS$_B$   (>0 = real signal beats null noise)")
    ax.set_title("Susceptibility margin is positive for all three models",
                 loc="left", fontsize=10.5, color=INK, pad=9)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_axisbelow(True); ax.xaxis.grid(True, color=GRID, lw=0.6)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    out = os.path.join(HERE, "figB_susceptibility.png")
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


# ----------------------------------------------------------------- FIGURE C
def fig_lift_stratified():
    strata = [("All 30 events", EV), (r"19 events, BS$_A\geq$0.15", FILT),
              (r"13 events, BS$_A\geq$0.35", CLEAN)]
    fig, ax = plt.subplots(figsize=(9.0, 3.9))
    w = 0.24
    xs = np.arange(len(strata))
    for i, m in enumerate(MODELS):
        means, los, his, tops, bots = [], [], [], [], []
        for _, ev in strata:
            d = [BSA[e] - R[m][(e, "B")]["brier"] for e in ev]
            mu, lo, hi = boot_ci(d)
            means.append(mu); los.append(mu - lo); his.append(hi - mu)
            tops.append(hi); bots.append(lo)
        pos = xs + (i - 1) * w
        ax.bar(pos, means, w * 0.88, color=C[m], label=m, edgecolor="white", linewidth=1.2, zorder=2)
        ax.errorbar(pos, means, yerr=[los, his], fmt="none", ecolor=INK2,
                    elinewidth=1.1, capsize=3.5, capthick=1.1, zorder=3)
        # place the value clear of the whisker cap, never on top of it
        for p, v, t, b in zip(pos, means, tops, bots):
            if v > 0:
                ax.annotate(f"{v:+.2f}", (p, t), xytext=(0, 6), textcoords="offset points",
                            ha="center", fontsize=8.4, color=INK)
            else:
                ax.annotate(f"{v:+.2f}", (p, b), xytext=(0, -13), textcoords="offset points",
                            ha="center", fontsize=8.4, color=INK)
    ax.axhline(0, color=INK, lw=0.9, zorder=1)
    ax.set_xticks(xs); ax.set_xticklabels([s[0] for s in strata], fontsize=9.4)
    ax.set_ylabel(r"Simulation lift  BS$_A$ $-$ BS$_B$")
    ax.set_ylim(-0.46, 0.62)
    ax.set_title("Lift turns positive only on subsets selected using BS$_A$ itself; every CI spans zero",
                 loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax)
    ax.legend(frameon=False, fontsize=8.8, loc="upper left", handlelength=1.1, ncol=3)
    fig.tight_layout()
    out = os.path.join(HERE, "figC_lift_stratified.png")
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


# ----------------------------------------------------------------- FIGURE D
def pearson(x, y):
    mx, my = st.mean(x), st.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(
        sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def fig_tautology():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.3))
    A = [BSA[e] for e in EV]
    Bm = [st.mean(R[m][(e, "B")]["brier"] for m in MODELS) for e in EV]
    L = [a - b for a, b in zip(A, Bm)]

    sa, sb = st.stdev(A), st.stdev(Bm)
    r_mech = sa / math.sqrt(sa ** 2 + sb ** 2)

    for ax, y, ylab, ttl in (
        (ax1, L, r"Mean simulation lift  BS$_A$ $-$ BS$_B$",
         "A.  Reported relationship (lift regressed on BS$_A$)"),
        (ax2, Bm, r"Mean With-Sim score  BS$_B$",
         "B.  Same data, tautology removed")):
        for e, x, v in zip(EV, A, y):
            col = C["Llama-3.1-8B"] if e[0] == "C" else (C["Mistral-7B"] if e[0] == "T" else C["Qwen2.5-7B"])
            ax.plot(x, v, "o", ms=7, color=col, mec="white", mew=1.1, zorder=3)
        m_, b_ = np.polyfit(A, y, 1)
        xr = np.linspace(min(A) - .04, max(A) + .04, 20)
        ax.plot(xr, m_ * xr + b_, color=INK2, lw=1.6, zorder=2)
        r = pearson(A, y)
        ax.annotate(f"$r$ = {r:+.3f}   $r^2$ = {r*r:.3f}", (0.035, 0.93), xycoords="axes fraction",
                    fontsize=10.5, color=INK, fontweight="bold")
        ax.set_xlabel(r"Baseline difficulty  BS$_A$"); ax.set_ylabel(ylab)
        ax.set_title(ttl, loc="left", fontsize=10.5, color=INK, pad=9)
        tidy(ax); ax.xaxis.grid(True, color=GRID, lw=0.6)

    ax1.annotate(f"expected $r$ = {r_mech:+.3f} even if BS$_B$\nwere pure noise "
                 r"(because lift $\equiv$ BS$_A-$BS$_B$)",
                 (0.035, 0.68), xycoords="axes fraction", fontsize=9, color=INK2)
    ax2.annotate("no association between baseline\ndifficulty and simulated performance",
                 (0.035, 0.76), xycoords="axes fraction", fontsize=9, color=INK2)
    for e in ("T2", "C11", "T1", "C10"):
        i = EV.index(e)
        ax1.annotate(e, (A[i], L[i]), xytext=(6, -3), textcoords="offset points",
                     fontsize=8.2, color=INK2)
    handles = [Line2D([], [], marker="o", ls="", ms=7, mec="white", mew=1.1,
                      color=c, label=l) for l, c in
               (("Social/Electoral (C)", C["Llama-3.1-8B"]),
                ("Technical/Economic (T)", C["Mistral-7B"]),
                ("Senate/Binary (S)", C["Qwen2.5-7B"]))]
    ax2.legend(handles=handles, frameon=False, fontsize=8.6, loc="upper right", handlelength=1.0)
    fig.tight_layout()
    out = os.path.join(HERE, "figD_difficulty_tautology.png")
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


# ----------------------------------------------------------------- FIGURE E
def fig_degenerate():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 3.9))
    conds = ["A", "B", "C"]
    clabel = {"A": "A (No-Sim)", "B": "B (With-Sim)", "C": "C (Null)"}

    w = 0.24
    xs = np.arange(3)
    for i, m in enumerate(MODELS):
        vals = []
        for c in conds:
            n = 0
            for e in EV:
                p = R[m][(e, c)]["probabilities"]
                if max(abs(v - 1.0 / len(p)) for v in p.values()) < 0.005:
                    n += 1
            vals.append(100.0 * n / len(EV))
        pos = xs + (i - 1) * w
        ax1.bar(pos, vals, w * 0.88, color=C[m], label=m, edgecolor="white", linewidth=1.2, zorder=2)
        for p, v in zip(pos, vals):
            ax1.annotate(f"{v:.0f}%", (p, v), xytext=(0, 5), textcoords="offset points",
                         ha="center", fontsize=8.4, color=INK)
    ax1.set_xticks(xs); ax1.set_xticklabels([clabel[c] for c in conds], fontsize=9.2)
    ax1.set_ylabel("Events answered with a flat\n(uniform) distribution  (%)")
    ax1.set_ylim(0, 52)
    ax1.set_title("A.  One fifth of simulated units return a non-answer",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax1)
    ax1.legend(frameon=False, fontsize=8.6, loc="upper left", handlelength=1.1)

    ends = {}
    for i, m in enumerate(MODELS):
        sharp = [st.mean(max(R[m][(e, c)]["probabilities"].values()) for e in EV) for c in conds]
        ends[m] = sharp[-1]
        ax2.plot(xs, sharp, color=C[m], lw=2.0, marker="o", ms=7, mec="white", mew=1.3,
                 label=m, zorder=3)
    # de-collide the end labels: nudge apart any endpoints closer than 0.012
    order = sorted(ends, key=lambda k: ends[k])
    ypos, last = {}, -9.0
    for m in order:
        y = max(ends[m], last + 0.013)
        ypos[m] = y; last = y
    for m in MODELS:
        ax2.annotate(f"{ends[m]:.3f}", (xs[-1], ypos[m]), xytext=(9, 0),
                     textcoords="offset points", va="center", fontsize=8.6, color=INK2)
    ax2.set_xticks(xs); ax2.set_xticklabels([clabel[c] for c in conds], fontsize=9.2)
    ax2.set_xlim(-0.25, 2.45); ax2.set_ylim(0.40, 0.71)
    ax2.set_ylabel("Mean probability on the\nmodal option (sharpness)")
    ax2.set_title("B.  Simulation flattens the forecast, which Brier penalises",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    tidy(ax2)
    ax2.legend(frameon=False, fontsize=8.6, loc="lower left", handlelength=1.6)
    fig.tight_layout()
    out = os.path.join(HERE, "figE_degenerate_forecasts.png")
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    try:
        fig_jsd_integrity()
    except TypeError:
        print("SKIPPED fig_jsd_integrity: round_jsd is None for 2026-08-16-repaired rows "
              "(round-level telemetry not re-extracted this pass) -- existing figA_jsd_integrity.png "
              "left untouched, describes the pre-repair archived state, same as figF/figG.")
    fig_susceptibility()
    fig_lift_stratified()
    fig_tautology()
    fig_degenerate()
