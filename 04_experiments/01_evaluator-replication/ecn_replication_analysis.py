"""ECN-BENCH: dual-evaluator replication analysis.

Dataset J = July 2026 campaigns, evaluator DeepSeek-R1-14B (local vLLM/Ollama).
            Canonical event_results.json (and the .bak_* snapshot it was restored
            from); reproduces each campaign summary.json exactly.
Dataset A = August 2026 re-evaluation of the SAME simulation transcripts by
            deepseek/deepseek-v4-flash-0731 via OpenRouter, in
            event_results_evaluatorB_openrouter.json, with every derived metric
            already recomputed from the August probabilities by
            ECN-HPC-DEPLOY/separate_evaluator_datasets.py.

Both files are read for `probabilities` only and rescored here with the pipeline's
own scoring functions, so the J/A comparison cannot be contaminated by a stale
stored metric.
"""
import json, math, random, sys
import statistics as st
from pathlib import Path

sys.path.insert(0, str(Path('MiroFish-Offline/backend').resolve()))
from app.benchmarks.scoring import brier_score
from app.benchmarks.statistics import ranked_probability_score, assign_probability_bracket

CAMPS = {
 "Llama-3.1-8B":  ("completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z",
                   "archive_pre_session_repairs/event_results.json.bak_20260813_192149"),
 "Mistral-7B":    ("completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z",
                   "archive_pre_session_repairs/event_results.json.bak_20260813_192149"),
 "Qwen2.5-7B":    ("completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z",
                   "archive_pre_session_repairs/event_results.json.bak_20260813_185718"),
 # Qwen2.5-14B has no event_results_evaluatorB_openrouter.json (README: "there is
 # no separate ... the way there is for the other three") -- it never had an
 # independent second evaluator pass, so it structurally can't take part in this
 # J-vs-A instrument-comparison script. It was already excluded from every
 # PAPER3-scoped analysis below; this just stops it crashing the loader too.
}
PAPER3 = ["Llama-3.1-8B", "Mistral-7B", "Qwen2.5-7B"]
CONDS = ["A", "B", "C"]


def metrics(row):
    """Recompute every derived metric from this row's probabilities."""
    p = row.get("probabilities") or {}
    gt = row.get("ground_truth")
    opts = row.get("options") or sorted(p.keys())
    if not p or not gt:
        return None
    out = {}
    out["brier"] = brier_score(p, gt)
    try:
        gtl = gt if gt in opts else next((l for l in opts if l.casefold() == gt.casefold()), gt)
        out["rps"] = ranked_probability_score(p, gtl, opts)
    except Exception:
        out["rps"] = None
    mx = max(p.values())
    tied = [k for k, v in p.items() if math.isclose(v, mx, abs_tol=1e-12)]
    out["dir_acc"] = float(tied[0].casefold() == str(gt).casefold()) if len(tied) == 1 else 0.5
    out["modal"] = mx
    k = len(p)
    out["k"] = k
    out["uniform"] = max(abs(v - 1.0 / k) for v in p.values()) < 0.005
    H = -sum(v * math.log(v) for v in p.values() if v > 0)
    out["entropy_norm"] = H / math.log(k) if k > 1 else 0.0
    out["calib_bracket"] = assign_probability_bracket(mx)
    out["calib_hit"] = int(any(t.casefold() == str(gt).casefold() for t in tied))
    out["wrs"] = ((row.get("validated_scales") or {}).get("scores") or {}).get("weighted_rubric_score")
    return out


def load(dataset):
    R = {}
    for model, (d, bak) in CAMPS.items():
        fn = bak if dataset == "J" else "event_results_evaluatorB_openrouter.json"
        rows = json.load(open(Path(d) / fn, encoding="utf-8"))
        R[model] = {}
        for r in rows:
            m = metrics(r)
            if m is None:
                continue
            R[model][(r["event_id"], r["condition"])] = m
    return R


def boot_ci(x, n=20000, seed=7):
    if not x:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    reps = sorted(st.mean(rng.choices(x, k=len(x))) for _ in range(n))
    return st.mean(x), reps[int(0.025 * n)], reps[int(0.975 * n)]


def pearson(x, y):
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else float("nan")


J, A = load("J"), load("A")
EV = sorted({e for (e, c) in J["Llama-3.1-8B"]})
print(f"Events: {len(EV)}   Models: {len(CAMPS)}   Units/model: {len(J['Llama-3.1-8B'])}")
print()

results = {"datasets": {}}

for tag, R, label in (("J", J, "JULY  evaluator = DeepSeek-R1-14B (local)"),
                      ("A", A, "AUGUST evaluator = deepseek-v4-flash-0731 (OpenRouter)")):
    print("=" * 78)
    print(f"DATASET {tag} -- {label}")
    print("=" * 78)
    ds = {}
    for model in CAMPS:
        cur = R[model]
        row = {}
        for c in CONDS:
            xs = [cur[(e, c)] for e in EV if (e, c) in cur]
            row[c] = {
                "n": len(xs),
                "brier": st.mean(v["brier"] for v in xs),
                "rps": st.mean(v["rps"] for v in xs if v["rps"] is not None),
                "dir_acc": st.mean(v["dir_acc"] for v in xs),
                "modal": st.mean(v["modal"] for v in xs),
                "entropy": st.mean(v["entropy_norm"] for v in xs),
                "uniform_n": sum(v["uniform"] for v in xs),
                "uniform_pct": 100.0 * sum(v["uniform"] for v in xs) / len(xs),
            }
        dB = [cur[(e, "A")]["brier"] - cur[(e, "B")]["brier"] for e in EV if (e, "A") in cur and (e, "B") in cur]
        dC = [cur[(e, "C")]["brier"] - cur[(e, "B")]["brier"] for e in EV if (e, "C") in cur and (e, "B") in cur]
        row["lift_AB"] = boot_ci(dB)
        row["susc_CB"] = boot_ci(dC)
        ds[model] = row

        print()
        print(model)
        print(f"  cond   n   Brier     RPS  DirAcc   Modal  Entropy      Uniform")
        for c in CONDS:
            v = row[c]
            print(f"  {c:4s} {v['n']:3d} {v['brier']:7.4f} {v['rps']:7.4f} {v['dir_acc']:7.4f} "
                  f"{v['modal']:7.4f} {v['entropy']:8.4f}   {v['uniform_n']:3d} ({v['uniform_pct']:4.1f}%)")
        m, lo, hi = row["lift_AB"]
        flag = "EXCLUDES 0" if (lo > 0 or hi < 0) else "spans 0"
        print(f"  lift A->B (BS_A - BS_B) = {m:+.4f}  95%CI [{lo:+.4f}, {hi:+.4f}]  {flag}")
        m, lo, hi = row["susc_CB"]
        flag = "EXCLUDES 0" if (lo > 0 or hi < 0) else "spans 0"
        print(f"  susc C-B  (BS_C - BS_B) = {m:+.4f}  95%CI [{lo:+.4f}, {hi:+.4f}]  {flag}")
    results["datasets"][tag] = ds
    print()

print("=" * 78)
print("HEADLINE CLAIM 1 -- degenerate (exactly uniform) forecasts, paper's 3 models")
print("=" * 78)
for tag, R in (("J", J), ("A", A)):
    simulated = [R[m][(e, c)] for m in PAPER3 for e in EV for c in ("B", "C") if (e, c) in R[m]]
    nosim = [R[m][(e, "A")] for m in PAPER3 for e in EV if (e, "A") in R[m]]
    su, nu = sum(v["uniform"] for v in simulated), sum(v["uniform"] for v in nosim)
    print(f"  Dataset {tag}: simulated {su}/{len(simulated)} = {100*su/len(simulated):.1f}%   "
          f"| No-Sim {nu}/{len(nosim)} = {100*nu/len(nosim):.1f}%")
    per = {m: sum(R[m][(e, 'B')]["uniform"] for e in EV if (e, 'B') in R[m]) for m in PAPER3}
    print("            Condition B by model: " + "  ".join(f"{m}={n}/30" for m, n in per.items()))
print()

print("=" * 78)
print("HEADLINE CLAIM 2 -- sharpness (mean modal probability), paper's 3 models")
print("=" * 78)
for tag, R in (("J", J), ("A", A)):
    a = st.mean(R[m][(e, "A")]["modal"] for m in PAPER3 for e in EV)
    bs = {m: st.mean(R[m][(e, "B")]["modal"] for e in EV) for m in PAPER3}
    print(f"  Dataset {tag}: No-Sim modal = {a:.4f}   With-Sim modal = "
          + ", ".join(f"{m}:{v:.4f}" for m, v in bs.items()))
print()

print("=" * 78)
print("HEADLINE CLAIM 3 -- difficulty/lift tautology")
print("=" * 78)
for tag, R in (("J", J), ("A", A)):
    BSA = [st.mean(R[m][(e, "A")]["brier"] for m in PAPER3) for e in EV]
    BSB = [st.mean(R[m][(e, "B")]["brier"] for m in PAPER3) for e in EV]
    L = [a - b for a, b in zip(BSA, BSB)]
    sa, sb = st.stdev(BSA), st.stdev(BSB)
    print(f"  Dataset {tag}: r(BS_A, lift) = {pearson(BSA, L):+.3f}   "
          f"mechanical expectation = {sa/math.sqrt(sa**2+sb**2):+.3f}   "
          f"non-tautological r(BS_A, BS_B) = {pearson(BSA, BSB):+.3f}")
print()

print("=" * 78)
print("NEW -- evaluator instrument agreement, J vs A (same transcripts)")
print("=" * 78)
# 2026-08-16: for Llama-3.1-8B the J/A premise no longer holds on the 24 events
# repaired that day -- J is the outage-corrupted July simulation, A is the
# OpenRouter re-simulation, so a J-vs-A difference there mixes "different
# evaluator" with "different transcript". Restrict Llama to the 6 events the
# outage never touched, where both passes really do read the same transcript.
SAME_TRANSCRIPT_ONLY = {"Llama-3.1-8B": {"C3", "S2", "S3", "S4", "S5", "S6"}}
for model in CAMPS:
    keep = SAME_TRANSCRIPT_ONLY.get(model)
    keys = [k for k in J[model] if k in A[model] and (keep is None or k[0] in keep)]
    if keep is not None:
        print(f"  [{model}: restricted to the {len(keep)} outage-free events -- the other 24 "
              f"were re-simulated 2026-08-16, so J and A do not share a transcript there]")
    bj = [J[model][k]["brier"] for k in keys]
    ba = [A[model][k]["brier"] for k in keys]
    dj = [J[model][k]["dir_acc"] for k in keys]
    da = [A[model][k]["dir_acc"] for k in keys]
    agree_dir = sum(1 for x, y in zip(dj, da) if x == y)
    print(f"  {model:14s} n={len(keys):3d}  r(Brier_J,Brier_A) = {pearson(bj,ba):+.3f}   "
          f"mean Brier {st.mean(bj):.4f} -> {st.mean(ba):.4f}   "
          f"dir agreement {agree_dir}/{len(keys)} ({100*agree_dir/len(keys):.0f}%)")
print()

print("=" * 78)
print("NEW -- evaluator non-determinism: Condition A is byte-identical across campaigns")
print("=" * 78)
for tag, R in (("J", J), ("A", A)):
    ident = 0
    spreads = []
    for e in EV:
        vals = [R[m][(e, "A")]["brier"] for m in PAPER3 if (e, "A") in R[m]]
        if len(vals) < 3:
            continue
        if max(vals) - min(vals) < 1e-9:
            ident += 1
        spreads.append(max(vals) - min(vals))
    print(f"  Dataset {tag}: identical Brier across 3 re-reads: {ident}/{len(spreads)}   "
          f"mean spread = {st.mean(spreads):.4f}   max spread = {max(spreads):.4f}")
print()

out = Path("ecn_replication_analysis.json")


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, float):
        return round(o, 6)
    return o


out.write_text(json.dumps(clean(results), indent=2), encoding="utf-8")
print(f"wrote {out}")
