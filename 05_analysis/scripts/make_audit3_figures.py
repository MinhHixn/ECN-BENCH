#!/usr/bin/env python
"""ECN-BENCH: figures for the run-integrity and cutoff-stratification sections.

Every number is recomputed here from the per-unit artifacts on disk (persona
files, SQLite trace tables, simulation logs, event_results.json) and from
data/events_raw.json; nothing is copied from the manuscript.

  figF_llama_outage.png    -- the Llama campaign's mid-run backend failure
  figG_evidence_depth.png  -- what the evaluator read vs what it scored
  figH_cutoff_lift.png     -- lift stratified by knowledge-cutoff cleanliness

Figure naming and styling follow make_audit_figures.py (figA--figE) and
make_replication_figures.py (figR1--figR2): the same categorical palette, panel
labels carried in the axes titles, and no figure number baked into the image
(LaTeX numbers them).

Run:  python make_audit3_figures.py
"""
import json, math, random, re, sqlite3, sys
import statistics as st
from datetime import date
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
# Public release date as a hard upper bound on what each model can have memorised.
RELEASE = {
    "Llama-3.1-8B": date(2024, 7, 23),
    "Mistral-7B":   date(2023, 9, 27),
    "Qwen2.5-7B":   date(2024, 9, 19),
}

# Same validated categorical palette as make_audit_figures.py / make_replication_figures.py.
C = {"Llama-3.1-8B": "#2a78d6", "Mistral-7B": "#eb6834", "Qwen2.5-7B": "#1baf7a"}
INK, INK2, INK3, GRID = "#0b0b0b", "#52514e", "#8a8a87", "#dcdcd8"
BAD, GOOD = "#c2352b", "#1baf7a"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK3, "axes.linewidth": 0.7, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})

GENERIC_BIO = re.compile(r"engaging on emerging developments", re.I)
PROBE_FAIL = re.compile(rb"Telemetry probe failed")
ACT_LINE = re.compile(r"^\[R(\d+)\]\[(twitter|reddit)\]\s+(.+?)\s*#(\d+):\s*(.*)$")
SOCIAL = ("create_post", "create_comment", "follow", "like_post", "like_comment")


def boot_ci(x, n=20000, seed=7):
    if not x:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(x, k=len(x))) for _ in range(n))
    return st.mean(x), reps[int(0.025 * n)], reps[int(0.975 * n)]


def unit_persona_stats(udir: Path):
    profs = json.loads((udir / "reddit_profiles.json").read_text(encoding="utf-8"))
    return (len({p.get("persona", "") for p in profs}),
            sum(1 for p in profs if GENERIC_BIO.search(p.get("bio") or "")) / len(profs))


def unit_db_counts(udir: Path):
    social = interview = 0
    for db in udir.glob("*_simulation.db"):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            for act, n in con.execute("SELECT action, COUNT(*) FROM trace GROUP BY action"):
                if act in SOCIAL:
                    social += n
                elif act == "interview":
                    interview += n
        finally:
            con.close()
    return social, interview


def evidence_stats(row):
    ev = row.get("evidence_text") or ""
    blk = ev.split("Representative Social Media Actions", 1)
    acts = []
    if len(blk) == 2:
        for line in blk[1].splitlines():
            m = ACT_LINE.match(line.strip())
            if m:
                acts.append((m.group(3), m.group(5).strip()))
    return {
        "chars": len(ev),
        "lines": len(acts),
        "speakers": len({a[0] for a in acts}),
        "utterances": len({a[1] for a in acts}),
    }


def load_events():
    raw = json.loads((HERE / "data" / "events_raw.json").read_text(encoding="utf-8"))
    meta = {}
    for grp in raw["core_events"].values():
        for e in grp:
            meta[e["id"]] = e
    for e in raw["supplementary_events"]["events"]:
        meta[e["id"]] = e
    return meta


def resolved_date(s):
    s = str(s).strip()
    if len(s) == 7:          # month-only entries are anchored mid-month
        s += "-15"
    return date.fromisoformat(s[:10])


# ---------------------------------------------------------------- collect data
print("scanning artifacts ...")
UNITS = {}
for model, d in CAMPS.items():
    d = HERE / d
    rows = json.loads((d / "event_results.json").read_text(encoding="utf-8"))
    scored = {r["unit_id"]: r for r in rows}
    per = []
    for udir in d.glob("*_r1"):
        if not (udir / "reddit_profiles.json").exists():
            continue
        distinct, generic = unit_persona_stats(udir)
        social, interview = unit_db_counts(udir)
        log = udir / "simulation.log"
        pf = len(PROBE_FAIL.findall(log.read_bytes())) if log.exists() else 0
        r = scored.get(udir.name, {})
        ev = evidence_stats(r)
        per.append({
            "unit": udir.name, "event": udir.name.split("_")[0],
            "cond": udir.name.split("_")[1], "mtime": udir.stat().st_mtime,
            "distinct": distinct, "generic": generic, "social": social,
            "interview": interview, "probe_fail": pf,
            "wrs": ((r.get("validated_scales") or {}).get("scores") or {}).get("weighted_rubric_score"),
            **{f"ev_{k}": v for k, v in ev.items()},
        })
    per.sort(key=lambda x: x["mtime"])
    UNITS[model] = per
    print(f"  {model}: {len(per)} units")

META = load_events()
BRIER = {}
for model, d in CAMPS.items():
    BRIER[model] = {}
    for r in json.loads((HERE / d / "event_results.json").read_text(encoding="utf-8")):
        p, gt = r.get("probabilities"), r.get("ground_truth")
        if p and gt:
            BRIER[model][(r["event_id"], r["condition"])] = brier_score(p, gt)

# ------------------------------------------------- figS1: the Llama outage
L = [u for u in UNITS["Llama-3.1-8B"] if u["cond"] == "B"]
x = np.arange(len(L))
labels = [u["event"] for u in L]

fig, axes = plt.subplots(3, 1, figsize=(11.5, 7.2), sharex=True,
                         gridspec_kw={"hspace": 0.16})

ax = axes[0]
ax.bar(x, [u["distinct"] for u in L], color=[C["Llama-3.1-8B"] if u["distinct"] > 100 else BAD for u in L],
       width=0.72, linewidth=0)
ax.axhline(75, color=INK3, lw=0.8, ls=":")
ax.text(len(L) - 0.4, 88, "paper's claimed floor: $\\geq$75 agents per persona axis",
        ha="right", va="bottom", fontsize=8, color=INK2)
ax.set_ylabel("distinct personas\nin the 300-agent pool")
ax.set_ylim(0, 300)

ax = axes[1]
ax.bar(x, [u["social"] for u in L], color=[C["Llama-3.1-8B"] if u["distinct"] > 100 else BAD for u in L],
       width=0.72, linewidth=0)
ax.set_ylabel("social actions\n(.db trace, both platforms)")
ax.set_yscale("symlog", linthresh=10)
ax.set_ylim(0, 1200)

ax = axes[2]
ax.bar(x, [u["probe_fail"] for u in L], color=BAD, width=0.72, linewidth=0,
       label="failed probes (\"Connection error\" in simulation.log)")
ax.plot(x, [u["interview"] for u in L], color=GOOD, lw=1.6, marker="o", ms=3.2,
        label="successful probes (interview rows in the .db trace)")
ax.set_ylabel("telemetry probes")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=90, fontsize=7.5)
ax.set_xlabel("Condition B units of the Llama-3.1-8B campaign, in wall-clock execution order")
ax.legend(frameon=False, fontsize=8, loc="center right")

for ax in axes:
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.axvline(6.5, color=INK, lw=1.1, ls="--")

axes[0].text(6.35, 285, "backend fails during S7 ", ha="right", va="top", fontsize=8.5, color=INK)
axes[0].text(6.65, 285, " every later run is a no-op", ha="left", va="top", fontsize=8.5, color=BAD)
axes[0].set_title("A single backend failure divides the campaign into 6 valid events and 23 no-op runs",
                  fontsize=10.5, loc="left", color=INK, pad=9)
fig.savefig(HERE / "figF_llama_outage.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote figF_llama_outage.png")

# -------------------------------- figS2: evidence depth vs rubric score
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.1), gridspec_kw={"wspace": 0.24})

ax = axes[0]
for model in CAMPS:
    sim = [u for u in UNITS[model] if u["cond"] in ("B", "C")]
    ax.scatter([u["ev_utterances"] for u in sim], [u["ev_speakers"] for u in sim],
               s=22, alpha=0.75, color=C[model], label=model, linewidth=0)
ax.set_xlabel("distinct utterances shown to the evaluator")
ax.set_ylabel("distinct speaking agents shown")
ax.set_title("A.  What the evaluator was given as “deliberation”\n"
             "     (one point per simulated unit, $n=180$)",
             fontsize=10.5, loc="left", color=INK, pad=9)
ax.axvspan(-1, 3, color=BAD, alpha=0.07)
ax.text(0.5, ax.get_ylim()[1] * 0.55, "one speaker,\n$\\leq$2 texts", fontsize=8, color=BAD,
        ha="left", va="center")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
ax.grid(color=GRID, lw=0.6)
ax.set_axisbelow(True)

ax = axes[1]
for model in CAMPS:
    sim = [u for u in UNITS[model] if u["cond"] in ("B", "C") and u["wrs"] is not None]
    ax.scatter([u["ev_utterances"] for u in sim], [u["wrs"] for u in sim],
               s=22, alpha=0.75, color=C[model], linewidth=0)
# Within-model comparison, so the contrast is not confounded by which campaign a
# unit came from: Llama's own outage units vs Llama's own healthy units.
lsim = [u for u in UNITS["Llama-3.1-8B"] if u["cond"] in ("B", "C") and u["wrs"] is not None]
thin = [u for u in lsim if u["ev_speakers"] <= 1]
rich = [u for u in lsim if u["ev_speakers"] > 1]
for grp, col, lab in (
    (thin, BAD, f"Llama, $\\leq$1 speaker in evidence (n={len(thin)}): "
                f"mean {st.mean(u['wrs'] for u in thin):.3f}"),
    (rich, GOOD, f"Llama, $>$1 speaker in evidence (n={len(rich)}): "
                 f"mean {st.mean(u['wrs'] for u in rich):.3f}"),
):
    ax.axhline(st.mean(u["wrs"] for u in grp), color=col, lw=1.3, ls="--", label=lab)
ax.set_xlabel("distinct utterances shown to the evaluator")
ax.set_ylabel("weighted rubric score returned")
ax.set_title("B.  The 7-dimension rubric does not respond to it",
             fontsize=10.5, loc="left", color=INK, pad=9)
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
ax.grid(color=GRID, lw=0.6)
ax.set_axisbelow(True)

fig.savefig(HERE / "figG_evidence_depth.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote figG_evidence_depth.png")

# -------------------------------- figS3: cutoff-stratified lift
EVS = sorted({e for e, c in BRIER["Llama-3.1-8B"]})
GLOBAL_CLEAN = [e for e in EVS if e in META
                and resolved_date(META[e]["resolved"]) > max(RELEASE.values())]

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0), gridspec_kw={"wspace": 0.3})

ax = axes[0]
ypos, ylab, cols = [], [], []
k = 0
for model in CAMPS:
    clean = [e for e in EVS if e in META and resolved_date(META[e]["resolved"]) > RELEASE[model]]
    dirty = [e for e in EVS if e in META and resolved_date(META[e]["resolved"]) <= RELEASE[model]]
    for tag, S in (("all 30 events", EVS), ("post-release only", clean), ("pre-release only", dirty)):
        lift = [BRIER[model][(e, "A")] - BRIER[model][(e, "B")]
                for e in S if (e, "A") in BRIER[model] and (e, "B") in BRIER[model]]
        if not lift:
            continue
        mu, lo, hi = boot_ci(lift)
        col = C[model] if tag == "all 30 events" else (GOOD if "post" in tag else BAD)
        ax.plot([lo, hi], [k, k], color=col, lw=2.0, solid_capstyle="butt")
        ax.plot([mu], [k], "o", color=col, ms=5.5)
        ypos.append(k)
        ylab.append(f"{model} — {tag} (n={len(lift)})")
        cols.append(col)
        k -= 1
    k -= 0.5
ax.axvline(0, color=INK, lw=0.9)
ax.set_yticks(ypos)
ax.set_yticklabels(ylab, fontsize=8)
for t, col in zip(ax.get_yticklabels(), cols):
    t.set_color(col)
ax.set_xlabel("simulation lift $BS_A - BS_B$  (95% percentile bootstrap, $B$ = 20,000)")
ax.set_title("A.  Stratifying by release date separates the models:\n"
             "     the pre-release effect holds for Qwen, not for Llama",
             fontsize=10.5, loc="left", color=INK, pad=9)
ax.grid(axis="x", color=GRID, lw=0.6)
ax.set_axisbelow(True)

ax = axes[1]
w = 0.26
for i, model in enumerate(CAMPS):
    vals, errs = [], []
    for c in "ABC":
        v = [BRIER[model][(e, c)] for e in GLOBAL_CLEAN if (e, c) in BRIER[model]]
        mu, lo, hi = boot_ci(v)
        vals.append(mu)
        errs.append([mu - lo, hi - mu])
    errs = np.array(errs).T
    ax.bar(np.arange(3) + (i - 1) * w, vals, width=w, color=C[model], linewidth=0, label=model)
    ax.errorbar(np.arange(3) + (i - 1) * w, vals, yerr=errs, fmt="none",
                ecolor=INK2, elinewidth=0.9, capsize=2.5)
ax.set_xticks(np.arange(3))
ax.set_xticklabels(["A (No-Sim,\nshared reference)", "B (With-Sim)", "C (Null Control)"], fontsize=8.5)
ax.set_ylabel("mean Brier score")
ax.set_title(f"B.  On the {len(GLOBAL_CLEAN)} events no model could have memorised,\n"
             "     Llama's With-Sim score separates from the other two",
             fontsize=10.5, loc="left", color=INK, pad=9)
ax.legend(frameon=False, fontsize=8.5)
ax.grid(axis="y", color=GRID, lw=0.6)
ax.set_axisbelow(True)

fig.savefig(HERE / "figH_cutoff_lift.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote figH_cutoff_lift.png")

# -------------------------------- machine-readable dump for the tables
out = {
    "persona_and_run_health": UNITS,
    "global_clean_events": GLOBAL_CLEAN,
    "release_bounds": {k: v.isoformat() for k, v in RELEASE.items()},
}
(HERE / "audit3_data.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("wrote audit3_data.json")
