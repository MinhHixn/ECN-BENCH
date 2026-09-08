#!/usr/bin/env python
"""Does degenerate consensus transfer to other unconstrained evaluators?

Every row below scores Mistral-7B's 60 simulated units -- the same byte-identical
transcripts Evaluator J read -- with no `response_format` field at all, i.e. in the
identical unconstrained condition that the keyword-filter defect of
Section~\\ref{sec:epistemic_mapping} put the July instrument in. Mistral is used
because its campaign suffered no serving outage, so every unit carries a genuine
multi-speaker transcript.

Two quantities matter. The flat rate over all 60 units is the like-for-like
comparison with Evaluator J's 19/60. The flat rate restricted to the 19 units J
itself flattened asks the sharper question: when a second instrument fails, does it
fail on the same inputs?

Sources: degeneracy_transfer.json (the main run) and, for the pipeline's own rubric
prompt rather than our minimal one, event_results_trunc_full_unconstrained.json.

Run:  python analyze_degeneracy_transfer.py
"""
from __future__ import annotations

import json
import math
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z"


def flat(p) -> bool:
    return bool(p) and max(abs(v - 1.0 / len(p)) for v in p.values()) < 0.005


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _logC(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_greater(a: int, b: int, c: int, d: int) -> float:
    n, r1, c1 = a + b + c + d, a + b, a + c
    return min(1.0, sum(math.exp(_logC(r1, x) + _logC(n - r1, c1 - x) - _logC(n, c1))
                        for x in range(max(0, c1 - (n - r1)), min(r1, c1) + 1) if x >= a))


def collect() -> tuple[list[dict], dict]:
    july = {r["unit_id"]: r for r in
            json.loads((CAMPAIGN / "event_results.json").read_text(encoding="utf-8"))
            if r["condition"] in ("B", "C")}
    july_flat = {u for u, r in july.items() if flat(r.get("probabilities"))}

    rows: list[dict] = []
    det = json.loads((HERE / "degeneracy_transfer.json").read_text(encoding="utf-8"))["detail"]
    for model in sorted({r["model"] for r in det}):
        ok = [r for r in det if r["model"] == model and r.get("parsed")]
        sub = [r for r in ok if r["unit_id"] in july_flat]
        a = sum(r["flat"] for r in sub)
        c = sum(r["flat"] for r in ok if r["unit_id"] not in july_flat)
        rows.append({
            "label": model, "n": len(ok), "flat": a + c,
            "sub_n": len(sub), "sub_flat": a,
            "modal": st.mean(r["modal"] for r in ok) if ok else float("nan"),
            "p_overlap": (fisher_greater(a, len(sub) - a, c, len(ok) - len(sub) - c)
                          if a + c else None),
            "flat_chars": [len(july[r["unit_id"]]["evidence_text"]) for r in ok if r["flat"]],
            "sharp_chars": [len(july[r["unit_id"]]["evidence_text"])
                            for r in ok if not r["flat"]],
        })

    # the pipeline's own rubric prompt, run through the production evaluator class
    pipe = CAMPAIGN / "event_results_trunc_full_unconstrained.json"
    if pipe.exists():
        got = [r for r in json.loads(pipe.read_text(encoding="utf-8"))
               if r.get("probabilities")]
        sub = [r for r in got if r["unit_id"] in july_flat]
        rows.append({
            "label": "deepseek/deepseek-r1 (pipeline rubric prompt)",
            "n": len(got), "flat": sum(flat(r["probabilities"]) for r in got),
            "sub_n": len(sub), "sub_flat": sum(flat(r["probabilities"]) for r in sub),
            "modal": st.mean(max(r["probabilities"].values()) for r in got),
            "p_overlap": None, "flat_chars": [], "sharp_chars": [],
        })

    j = {"label": "DeepSeek-R1-14B, local (Evaluator J)", "n": len(july),
         "flat": len(july_flat), "sub_n": len(july_flat), "sub_flat": len(july_flat),
         "modal": st.mean(max(r["probabilities"].values()) for r in july.values()),
         "p_overlap": None,
         "flat_chars": [len(july[u]["evidence_text"]) for u in july_flat],
         "sharp_chars": [len(r["evidence_text"]) for u, r in july.items()
                         if u not in july_flat]}
    return rows, j


def main() -> int:
    rows, j = collect()
    print("=" * 100)
    print("DOES DEGENERATE CONSENSUS TRANSFER TO OTHER UNCONSTRAINED EVALUATORS?")
    print("All rows: Mistral-7B's 60 simulated units, no response_format, identical transcripts.")
    print("=" * 100)
    hdr = (f"{'evaluator':<46}{'flat, all units':>18}{'flat on J-flat 19':>20}"
           f"{'modal':>8}{'p(overlap)':>12}")
    print(hdr)
    print(f"{j['label']:<46}{j['flat']:>10}/{j['n']:<7}{j['sub_flat']:>13}/{j['sub_n']:<6}"
          f"{j['modal']:>8.3f}{'--':>12}")
    print("-" * 100)
    for r in rows:
        p = f"{r['p_overlap']:.4f}" if r["p_overlap"] is not None else "--"
        print(f"{r['label']:<46}{r['flat']:>10}/{r['n']:<7}{r['sub_flat']:>13}/{r['sub_n']:<6}"
              f"{r['modal']:>8.3f}{p:>12}")

    pooled_n = sum(r["n"] for r in rows if "pipeline" not in r["label"])
    pooled_f = sum(r["flat"] for r in rows if "pipeline" not in r["label"])
    print("-" * 100)
    print(f"{'pooled over the five comparison evaluators':<46}{pooled_f:>10}/{pooled_n:<7}")
    print()
    for r in rows + [j]:
        if r["flat_chars"] and r["sharp_chars"]:
            print(f"  {r['label']:<46} median evidence chars: "
                  f"flat {int(st.median(r['flat_chars']))} vs "
                  f"sharp {int(st.median(r['sharp_chars']))}")

    out = HERE / "degeneracy_transfer_summary.json"
    out.write_text(json.dumps(
        {"july_instrument": {k: v for k, v in j.items()
                             if k not in ("flat_chars", "sharp_chars")},
         "comparison": [{k: v for k, v in r.items()
                         if k not in ("flat_chars", "sharp_chars")} for r in rows]},
        indent=2), encoding="utf-8")
    print(f"\nwrote {out.name}")
    draw(rows, j)
    return 0


def draw(rows: list[dict], j: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
    C_JULY, C_DEGEN, C_CLEAN = "#c2410c", "#d97706", "#2a78d6"
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9.5,
        "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })

    series = [j] + rows
    labels, colors = [], []
    for r in series:
        lab = r["label"].replace(" (", "\n(")
        labels.append(lab)
        colors.append(C_JULY if r is j else (C_DEGEN if r["flat"] else C_CLEAN))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 0.66 * len(series) + 2.2),
                                   gridspec_kw={"width_ratios": [1.35, 1.0]})
    ys = np.arange(len(series))[::-1]

    for y, r, col in zip(ys, series, colors):
        rate = 100.0 * r["flat"] / r["n"] if r["n"] else 0.0
        lo, hi = wilson(r["flat"], r["n"])
        ax1.barh(y, rate, 0.62, color=col, zorder=3)
        ax1.plot([100 * lo, 100 * hi], [y, y], color=INK2, lw=1.3, zorder=4)
        ax1.annotate(f"{r['flat']}/{r['n']}", (max(rate, 100 * hi) + 1.6, y),
                     va="center", fontsize=8.6, color=INK)
    ax1.set_yticks(ys)
    ax1.set_yticklabels(labels, fontsize=8.2)
    ax1.set_xlim(0, 62)
    ax1.set_xlabel("units returning an exactly flat (uniform) vector  (%)")
    ax1.set_title("A.  Only one comparison evaluator degenerates,\n"
                  "     and it is the smallest reasoning model tested",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.set_axisbelow(True)
    ax1.xaxis.grid(True, color=GRID, lw=0.6)
    ax1.tick_params(axis="y", length=0)

    for y, r, col in zip(ys, series, colors):
        if not r["sub_n"]:
            continue
        rate = 100.0 * r["sub_flat"] / r["sub_n"]
        lo, hi = wilson(r["sub_flat"], r["sub_n"])
        ax2.barh(y, rate, 0.62, color=col, zorder=3)
        ax2.plot([100 * lo, 100 * hi], [y, y], color=INK2, lw=1.3, zorder=4)
        ax2.annotate(f"{r['sub_flat']}/{r['sub_n']}", (max(rate, 100 * hi) + 2.2, y),
                     va="center", fontsize=8.6, color=INK)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([])
    ax2.set_xlim(0, 128)
    ax2.set_xticks([0, 25, 50, 75, 100])
    ax2.set_xlabel("flat rate restricted to the 19 units Evaluator J flattened  (%)")
    ax2.set_title("B.  And when it fails, it fails on the same\n"
                  "     transcripts (Fisher $p$ = 0.012)",
                  loc="left", fontsize=10.5, color=INK, pad=9)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.set_axisbelow(True)
    ax2.xaxis.grid(True, color=GRID, lw=0.6)
    ax2.tick_params(axis="y", length=0)

    fig.tight_layout()
    out = HERE / "figK_degeneracy_transfer.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out.name)


if __name__ == "__main__":
    raise SystemExit(main())
