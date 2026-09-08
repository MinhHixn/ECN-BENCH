#!/usr/bin/env python
"""Analyse the evidence-truncation grid and draw its figure.

The design is 2 (structured-output enforcement: off / on) x 4 (evidence length:
~2k / ~5k / ~8k / untruncated) over Mistral-7B's 60 simulated units, with the
evaluator model, prompt, temperature and transcript held fixed across every cell.
The enforced arm is run at the two endpoint lengths only: its prediction is that
degeneracy is flat in length, which two levels test.

Outcome of record is the flat rate -- the share of units returning a probability
vector within 0.005 of uniform -- because that is the quantity the paper's central
claim is about. Mean modal probability and mean Brier are reported alongside it.

Run:  python analyze_truncation_grid.py
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "MiroFish-Offline" / "backend"))
from app.benchmarks.scoring import brier_score  # noqa: E402

CAMPAIGN = HERE / "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z"
LEVELS = ["2k", "5k", "8k", "full"]
ARMS = ["q14b_unconstrained", "q14b_enforced", "unconstrained", "enforced"]
ARM_LABEL = {
    "q14b_unconstrained": "qwen3-14b, enforcement OFF (reproduces the failure)",
    "q14b_enforced":      "qwen3-14b, enforcement ON",
    "unconstrained":      "deepseek-r1, enforcement OFF (negative control)",
    "enforced":           "deepseek-r1, enforcement ON",
}
LEVEL_LABEL = {"2k": "~2k", "5k": "~5k", "8k": "~8k", "full": "untruncated\n(10.2-15.6k)"}


def flat(p: dict | None) -> bool:
    if not p:
        return False
    return max(abs(v - 1.0 / len(p)) for v in p.values()) < 0.005


def load(arm: str, level: str):
    p = CAMPAIGN / f"event_results_trunc_{level}_{arm}.json"
    if not p.exists():
        return None
    rows = json.loads(p.read_text(encoding="utf-8"))
    done = [r for r in rows if r.get("probabilities")]
    return rows, done


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- behaves sensibly at k=0 and k=n, unlike normal."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _boot(xs, n: int = 20000, seed: int = 7):
    r = random.Random(seed)
    reps = sorted(st.mean(r.choices(xs, k=len(xs))) for _ in range(n))
    return (reps[int(0.025 * n)], reps[int(0.975 * n)])


def cell_stats(arm: str, level: str) -> dict | None:
    got = load(arm, level)
    if not got:
        return None
    rows, done = got
    if not done:
        return {"arm": arm, "level": level, "n": 0, "total": len(rows)}
    k = sum(flat(r["probabilities"]) for r in done)
    modal = [max(r["probabilities"].values()) for r in done]
    # modal - 1/K: 0 for a uniform vector at any K, comparable across the mixed-K
    # catalogue in a way that raw modal probability is not.
    excess = [max(r["probabilities"].values()) - 1.0 / len(r["probabilities"])
              for r in done]
    briers = [brier_score(r["probabilities"], r["ground_truth"])
              for r in done if r.get("ground_truth")]
    chars = [len(r.get("evidence_text") or "") for r in done]
    lo, hi = wilson(k, len(done))
    return {
        "arm": arm, "level": level, "n": len(done), "total": len(rows),
        "flat": k, "flat_rate": k / len(done), "flat_ci": (lo, hi),
        "mean_modal": st.mean(modal),
        "mean_excess": st.mean(excess),
        "excess_ci": _boot(excess),
        "mean_brier": st.mean(briers) if briers else float("nan"),
        "median_chars": int(st.median(chars)),
    }


def fisher_exact_greater(a: int, b: int, c: int, d: int) -> float:
    """One-sided P(X >= a) for the 2x2 table [[a,b],[c,d]], hypergeometric."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    def logC(n_, k_):
        return math.lgamma(n_ + 1) - math.lgamma(k_ + 1) - math.lgamma(n_ - k_ + 1)
    tot = 0.0
    for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1):
        p = math.exp(logC(r1, x) + logC(n - r1, c1 - x) - logC(n, c1))
        if x >= a:
            tot += p
    return min(1.0, tot)


def main() -> int:
    print("=" * 82)
    print("EVIDENCE-TRUNCATION GRID -- Mistral-7B, 60 simulated units per cell")
    print("Within an arm the evaluator, prompt, temperature and transcript are fixed;")
    print("only how much of the transcript is shown varies.")
    print("=" * 82)
    table: dict[tuple[str, str], dict] = {}
    for arm in ARMS:
        print(f"\n{ARM_LABEL.get(arm, arm)}")
        print(f"  {'level':<6} {'n':>5} {'chars':>7} {'flat':>9} {'95% CI':>16} "
              f"{'modal':>7} {'modal-1/K [95% CI]':>26} {'Brier':>7}")
        for level in LEVELS:
            s = cell_stats(arm, level)
            if not s:
                continue
            table[(arm, level)] = s
            if not s["n"]:
                print(f"  {level:<6} {'--':>5}  (no scored units yet, {s['total']} pending)")
                continue
            lo, hi = s["flat_ci"]
            elo, ehi = s["excess_ci"]
            print(f"  {level:<6} {s['n']:>5} {s['median_chars']:>7} "
                  f"{s['flat']:>4}/{s['n']:<4} [{lo:.2f}, {hi:.2f}]".ljust(56)
                  + f"{s['mean_modal']:>7.3f}"
                  + f"   {s['mean_excess']:+.3f} [{elo:+.3f}, {ehi:+.3f}]".rjust(26)
                  + f" {s['mean_brier']:>7.3f}")

    print()
    for arm in ARMS:
        a2, af = table.get((arm, "2k")), table.get((arm, "full"))
        if not (a2 and af and a2["n"] and af["n"]):
            continue
        p = fisher_exact_greater(af["flat"], af["n"] - af["flat"],
                                 a2["flat"], a2["n"] - a2["flat"])
        print(f"  {ARM_LABEL.get(arm, arm):<52} untruncated {af['flat']}/{af['n']} "
              f"vs ~2k {a2['flat']}/{a2['n']}   one-sided Fisher p = {p:.4g}")

    out = HERE / "truncation_results.json"
    out.write_text(json.dumps(
        {f"{a}/{l}": v for (a, l), v in table.items()}, indent=2), encoding="utf-8")
    print(f"\nwrote {out.name}")

    complete = [v for v in table.values() if v.get("n")]
    if len(complete) < 4:
        print("(figure skipped -- fewer than four cells scored so far)")
        return 0
    draw(table)
    return 0


def draw(table) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
    STYLE = {
        "q14b_unconstrained": ("#c2410c", "-", "o", 2.2, "qwen3-14b, enforcement OFF"),
        "q14b_enforced":      ("#2a78d6", "-", "o", 2.2, "qwen3-14b, enforcement ON"),
        "unconstrained":      ("#d9a189", (0, (4, 2)), "s", 1.5,
                               "deepseek-r1, OFF (control)"),
        "enforced":           ("#9dbfe6", (0, (4, 2)), "s", 1.5,
                               "deepseek-r1, ON (control)"),
    }
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9.5,
        "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.3))
    xs = np.arange(len(LEVELS))

    for arm in ARMS:
        col, ls, mk, lw, lab = STYLE[arm]
        pts = [(i, table[(arm, l)]) for i, l in enumerate(LEVELS)
               if (arm, l) in table and table[(arm, l)].get("n")]
        if not pts:
            continue
        x = [i for i, _ in pts]
        y = [100 * s["flat_rate"] for _, s in pts]
        ax1.plot(x, y, ls=ls, marker=mk, color=col, ms=6.5, lw=lw, mec="white",
                 mew=1.1, label=lab, zorder=3)
        if arm.startswith("q14b"):
            lo = [100 * s["flat_ci"][0] for _, s in pts]
            hi = [100 * s["flat_ci"][1] for _, s in pts]
            ax1.fill_between(x, lo, hi, color=col, alpha=0.13, zorder=1)
            for xi, yi, (_, s) in zip(x, y, pts):
                ax1.annotate(f"{s['flat']}/{s['n']}", (xi, yi), xytext=(0, 8),
                             textcoords="offset points", ha="center",
                             fontsize=8.4, color=INK)
        ax2.plot(x, [s["mean_excess"] for _, s in pts], ls=ls, marker=mk, color=col,
                 ms=6.5, lw=lw, mec="white", mew=1.1, label=lab, zorder=3)
        if arm.startswith("q14b"):
            ax2.fill_between(x, [s["excess_ci"][0] for _, s in pts],
                             [s["excess_ci"][1] for _, s in pts],
                             color=col, alpha=0.13, zorder=1)

    for ax, ylab, title in (
        (ax1, "units returning an exactly flat\n(uniform) distribution  (%)",
         "A.  Assigning transcript length does not raise degeneracy;\n"
         "     the shortest condition is the worst one"),
        (ax2, "excess sharpness  (modal $-$ 1/$K$)",
         "B.  Sharpness is flat in length too, and enforcement\n"
         "     changes nothing within a model")):
        ax.set_xticks(xs)
        ax.set_xticklabels([LEVEL_LABEL[l] for l in LEVELS], fontsize=8.8)
        ax.set_xlabel("evidence shown to the evaluator (characters)")
        ax.set_ylabel(ylab)
        ax.set_title(title, loc="left", fontsize=10.5, color=INK, pad=9)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax1.set_ylim(-2, None)
    ax2.axhline(0.0, color=INK3, lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax2.annotate("exactly uniform, at any $K$", (0.02, 0.004),
                 xycoords=("axes fraction", "data"), fontsize=8.2, color=INK2)
    ax1.legend(frameon=False, fontsize=8.3, loc="upper left", handlelength=1.8)

    fig.tight_layout()
    out = HERE / "figL_truncation.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.name)


if __name__ == "__main__":
    raise SystemExit(main())
