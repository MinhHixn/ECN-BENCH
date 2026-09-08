"""
Build the consolidated multi-pass, multi-evaluator reproducibility analysis
behind ecn_bench_paper.tex's Section~\\ref{sec:four_model_extension} and
Table~\\ref{tab:four_model_clean}.

Reads each model's event_results_evaluator*.json files (the original pass
plus repeated Evaluator A reads and one Evaluator C read), and writes:
  - completed_benches/<model>/.../reproducibility_analysis.json (per model)
  - reproducibility_analysis_master.json (repo root, rollup of all four)

Run from anywhere; paths are resolved relative to the repo root (this file's
grandparent directory).
"""
import json
import statistics
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "completed_benches"

# The 20 events resolving after every model's public release date (Section~\cutoff).
# Until 2026-08-21, Qwen2.5-14B was missing 6 events (T3, T4, T5, T6, C6, T8) to a
# stale-catalogue wrong-topic bug, which knocked T6/C6/T8 out of the 20 -> a "clean
# 17" common set. Those 6 were re-simulated against the correct root catalogue and
# rescored 2026-08-21 (5 evaluator passes); Qwen2.5-14B is now 30/30 like the other
# 3 models, so all 20 CLEAN_20 events are common to all 4 models again -- verified
# T6/C6/T8 present with sane, diverse probabilities in all 4 campaigns'
# event_results.json. Renamed CLEAN_17_COMMON -> CLEAN_20_COMMON and the JSON key
# clean_17_events_common_to_all_4_models -> clean_20_events_common_to_all_4_models
# throughout (no other script reads the old key programmatically -- checked) so a
# stale "17" never sits next to a 20-element set.
CLEAN_20 = {'C1', 'C11', 'C13', 'C14', 'C15', 'C5', 'C6', 'C8', 'C9', 'S2', 'S3', 'S4',
            'S5', 'S6', 'S7', 'S9', 'T2', 'T6', 'T8', 'T9'}
CLEAN_20_COMMON = CLEAN_20

MODELS = {
    "Llama-3.1-8B": {
        "dir": BENCH / "llama-3.1-8b-awq" / "ecnbench_20260714T173650169846Z",
        "deepseek_files": ["event_results_evaluatorB_openrouter.json",
                            "event_results_evaluatorA_repeat1.json",
                            "event_results_evaluatorA_repeat2.json",
                            "event_results_evaluatorA_repeat3.json"],
        "gpt_file": "event_results_evaluatorC_gptlunapro.json",
    },
    "Mistral-7B": {
        "dir": BENCH / "mistral-7b-awq" / "ecnbench_20260715T080203247382Z",
        "deepseek_files": ["event_results_evaluatorB_openrouter.json",
                            "event_results_evaluatorA_repeat1.json",
                            "event_results_evaluatorA_repeat2.json",
                            "event_results_evaluatorA_repeat3.json"],
        "gpt_file": "event_results_evaluatorC_gptlunapro.json",
    },
    "Qwen2.5-7B": {
        "dir": BENCH / "qwen2.5_7b" / "ecnbench_20260717T154127454597Z",
        "deepseek_files": ["event_results_evaluatorB_openrouter.json",
                            "event_results_evaluatorA_repeat1.json",
                            "event_results_evaluatorA_repeat2.json",
                            "event_results_evaluatorA_repeat3.json"],
        "gpt_file": "event_results_evaluatorC_gptlunapro.json",
    },
    "Qwen2.5-14B": {
        "dir": BENCH / "qwen2.5-14b-awq" / "ecnbench_20260727_qwen14b_complete",
        "deepseek_files": ["event_results_evaluatorA_repeat1.json",
                            "event_results_evaluatorA_repeat2.json",
                            "event_results_evaluatorA_repeat3.json"],
        "gpt_file": "event_results_evaluatorC_gptlunapro.json",
    },
}

# Units that permanently failed to re-evaluate (hung against OpenRouter across 3
# independent retry attempts) but still hold a stale, never-overwritten copy of an
# earlier pass's row rather than being absent from the file. Must be excluded
# explicitly, or the stale copy gets double-counted as a genuine independent read.
KNOWN_GAPS = {
    "Qwen2.5-7B": {
        "event_results_evaluatorA_repeat3.json": ["T3_C_r1", "C9_A_r1", "C13_C_r1"],
    },
    "Qwen2.5-14B": {
        "event_results_evaluatorA_repeat2.json": ["T1_C_r1"],
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def brier(probs, truth):
    if not isinstance(probs, dict) or not probs:
        return None
    truth_key = truth if truth in probs else next(
        (k for k in probs if k.casefold() == str(truth).casefold()), None)
    if truth_key is None:
        return None
    return sum((p - (1.0 if k == truth_key else 0.0)) ** 2 for k, p in probs.items())


def is_flat(probs):
    if not isinstance(probs, dict) or not probs:
        return None
    vals = list(probs.values())
    return max(vals) - min(vals) < 1e-9


def compute_model_analysis(model, cfg):
    d = cfg["dir"]
    gaps_for_model = KNOWN_GAPS.get(model, {})
    deepseek_datasets = []
    for fn in cfg["deepseek_files"]:
        p = d / fn
        if p.exists():
            data = {r["unit_id"]: r for r in load(p)}
            for bad_uid in gaps_for_model.get(fn, []):
                data.pop(bad_uid, None)
            deepseek_datasets.append((fn, data))
    gpt_path = d / cfg["gpt_file"]
    gpt_data = {r["unit_id"]: r for r in load(gpt_path)} if gpt_path.exists() else {}

    unit_ids = set()
    for _, ds in deepseek_datasets:
        unit_ids |= set(ds.keys())

    per_unit = {}
    for uid in unit_ids:
        row_ref = None
        for _, ds in deepseek_datasets:
            if uid in ds:
                row_ref = ds[uid]
                break
        gt = row_ref.get("ground_truth")
        eid = row_ref.get("event_id")
        cond = row_ref.get("condition")

        d_briers, d_flats = [], []
        for _, ds in deepseek_datasets:
            row = ds.get(uid)
            if row is None:
                continue
            b = brier(row.get("probabilities"), gt)
            if b is not None:
                d_briers.append(b)
            f = is_flat(row.get("probabilities"))
            if f is not None:
                d_flats.append(f)

        gpt_row = gpt_data.get(uid)
        gpt_b = brier(gpt_row.get("probabilities"), gt) if gpt_row else None
        gpt_f = is_flat(gpt_row.get("probabilities")) if gpt_row else None

        avg_probs = defaultdict(float)
        n_valid = 0
        for _, ds in deepseek_datasets:
            row = ds.get(uid)
            if row and isinstance(row.get("probabilities"), dict):
                for k, v in row["probabilities"].items():
                    avg_probs[k] += v
                n_valid += 1
        avg_probs = {k: v / n_valid for k, v in avg_probs.items()} if n_valid else {}

        per_unit[uid] = {
            "event_id": eid, "condition": cond, "ground_truth": gt,
            "n_deepseek_reads": len(d_briers), "deepseek_briers": d_briers,
            "deepseek_flat_votes": d_flats, "gpt_brier": gpt_b, "gpt_flat": gpt_f,
            "avg_probs": dict(avg_probs),
        }

    def summarize(event_filter):
        by_cond_b, by_cond_acc, by_cond_gpt = defaultdict(list), defaultdict(list), defaultdict(list)
        flat_reads = defaultdict(lambda: [0, 0])
        gpt_flat, gpt_total = 0, 0
        events_seen = set()
        for uid, u in per_unit.items():
            if event_filter is not None and u["event_id"] not in event_filter:
                continue
            events_seen.add(u["event_id"])
            c = u["condition"]
            if u["deepseek_briers"]:
                by_cond_b[c].append(statistics.mean(u["deepseek_briers"]))
            if u["gpt_brier"] is not None:
                by_cond_gpt[c].append(u["gpt_brier"])
                gpt_total += 1
                if u["gpt_flat"]:
                    gpt_flat += 1
            for f in u["deepseek_flat_votes"]:
                flat_reads[c][1] += 1
                if f:
                    flat_reads[c][0] += 1
            ap = u["avg_probs"]
            if ap:
                peak = max(ap.values())
                tied = [k for k, v in ap.items() if abs(v - peak) < 1e-9]
                if len(tied) == 1:
                    by_cond_acc[c].append(int(tied[0].casefold() == str(u["ground_truth"]).casefold()))
        out = {"n_events": len(events_seen), "by_condition": {}}
        for c in ["A", "B", "C"]:
            if c in by_cond_b:
                fl = flat_reads[c]
                out["by_condition"][c] = {
                    "n_units": len(by_cond_b[c]),
                    "deepseek_robust_mean_brier": round(statistics.mean(by_cond_b[c]), 4),
                    "directional_accuracy": round(statistics.mean(by_cond_acc[c]), 4) if by_cond_acc.get(c) else None,
                    "gpt_lunapro_mean_brier": round(statistics.mean(by_cond_gpt[c]), 4) if by_cond_gpt.get(c) else None,
                    "deepseek_flat_read_rate": round(fl[0] / fl[1], 4) if fl[1] else None,
                }
        b = out["by_condition"]
        if "A" in b and "B" in b:
            out["lift_A_to_B"] = round(b["A"]["deepseek_robust_mean_brier"] - b["B"]["deepseek_robust_mean_brier"], 4)
        if "B" in b and "C" in b:
            out["susceptibility_C_minus_B"] = round(b["C"]["deepseek_robust_mean_brier"] - b["B"]["deepseek_robust_mean_brier"], 4)
        out["gpt_lunapro_flat_rate_all_conditions"] = round(gpt_flat / gpt_total, 4) if gpt_total else None
        return out

    spreads = [max(u["deepseek_briers"]) - min(u["deepseek_briers"])
               for u in per_unit.values() if len(u["deepseek_briers"]) >= 2]
    cross_eval_pairs = [(statistics.mean(u["deepseek_briers"]), u["gpt_brier"])
                         for u in per_unit.values() if u["deepseek_briers"] and u["gpt_brier"] is not None]
    pearson_r = None
    if len(cross_eval_pairs) >= 2:
        xs = [p[0] for p in cross_eval_pairs]
        ys = [p[1] for p in cross_eval_pairs]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        cov = sum((x - mx) * (y - my) for x, y in cross_eval_pairs)
        sx = sum((x - mx) ** 2 for x in xs) ** 0.5
        sy = sum((y - my) ** 2 for y in ys) ** 0.5
        pearson_r = round(cov / (sx * sy), 4) if sx > 0 and sy > 0 else None

    return {
        "model": model,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "deepseek_v4_flash_0731_reads": [fn for fn, _ in deepseek_datasets],
            "gpt_5_6_luna_pro_read": cfg["gpt_file"] if gpt_path.exists() else None,
        },
        "known_permanent_gaps": KNOWN_GAPS.get(model, {}),
        "instrument_spread": {
            "n_units_with_2plus_reads": len(spreads),
            "mean_spread_brier": round(statistics.mean(spreads), 4) if spreads else None,
            "median_spread_brier": round(statistics.median(spreads), 4) if spreads else None,
            "max_spread_brier": round(max(spreads), 4) if spreads else None,
            "pct_units_reproducing_within_0.01": round(sum(1 for s in spreads if s < 0.01) / len(spreads), 4) if spreads else None,
        },
        "cross_evaluator_agreement": {
            "n_units": len(cross_eval_pairs),
            "pearson_r_deepseek_mean_vs_gpt_lunapro": pearson_r,
        },
        "all_available_events": summarize(None),
        "clean_20_events_where_available": summarize(CLEAN_20),
        "clean_20_events_common_to_all_4_models": summarize(CLEAN_20_COMMON),
    }


def main():
    master = {}
    for model, cfg in MODELS.items():
        analysis = compute_model_analysis(model, cfg)
        master[model] = analysis
        out_path = cfg["dir"] / "reproducibility_analysis.json"
        out_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {out_path}")

    master_out = {
        "description": "Master rollup of the multi-pass, multi-evaluator reproducibility "
                        "analysis underlying Section 8 (Evaluator Replication) and "
                        "Table tab:four_model_clean of ecn_bench_paper.tex.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": master,
    }
    master_path = ROOT / "reproducibility_analysis_master.json"
    master_path.write_text(json.dumps(master_out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {master_path}")

    print("\n=== Table tab:four_model_clean values (20 common clean events) ===")
    for model in MODELS:
        c17 = master[model]["clean_20_events_common_to_all_4_models"]
        b = c17["by_condition"]
        print(f"{model}: lift={c17.get('lift_A_to_B')}, "
              f"accB={b.get('B', {}).get('directional_accuracy')}, "
              f"accC={b.get('C', {}).get('directional_accuracy')}, "
              f"susceptibility={c17.get('susceptibility_C_minus_B')}, "
              f"flatC={b.get('C', {}).get('deepseek_flat_read_rate')}")


if __name__ == "__main__":
    main()
