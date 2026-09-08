"""Offline reanalysis of frozen ECN-BENCH observations for the revised paper."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

MODELS = {
    "Llama-3.1-8B": "llama-3.1-8b-awq",
    "Mistral-7B": "mistral-7b-awq",
    "Qwen2.5-7B": "qwen2.5_7b",
    "Qwen2.5-14B": "qwen2.5-14b-awq",
}
A_FILES = ["event_results_evaluatorB_openrouter.json"] + [
    f"event_results_evaluatorA_repeat{repeat}.json" for repeat in (1, 2, 3)
]
C_FILE = "event_results_evaluatorC_gptlunapro.json"
GAPS = {
    ("Qwen2.5-7B", A_FILES[3]): {"T3_C_r1", "C9_A_r1", "C13_C_r1"},
    ("Qwen2.5-14B", A_FILES[2]): {"T1_C_r1"},
}
POST_RELEASE_EVENTS = [
    "C1", "C5", "C6", "C8", "C9", "C11", "C13", "C14", "C15",
    "S2", "S3", "S4", "S5", "S6", "S7", "S9", "T2", "T6", "T8", "T9",
]
WRONG_INJECTIONS = {"C6", "T1", "T3", "T4", "T5", "T6", "T8"}
US_ELECTION_EVENTS = {"C1", "C5", "S2", "S3", "S4", "S5"}
LLAMA_PAIRED = {"C3", "S2", "S3", "S4", "S5", "S6"}
COT_ARMS = {
    "Llama-3.1-8B": ("Llama-3.1-8B", True),
    "Qwen2.5-7B": ("Qwen2.5-7B", True),
    "Mistral-8B": ("Mistral-7B", False),
    "Qwen3-14B": ("Qwen2.5-14B", False),
}
BOOTSTRAPS = 100000
SEED = 7
INPUT_HASHES = {}


def read_json(path, root):
    payload = path.read_bytes()
    INPUT_HASHES[path.relative_to(root).as_posix()] = hashlib.sha256(payload).hexdigest()
    return json.loads(payload.decode("utf-8-sig"))


def unit_id(row):
    return row.get("unit") or row.get("unit_id") or (
        f"{row['event_id']}_{row['condition']}_r{row.get('repeat', 1)}"
    )


def validate_row(row):
    probabilities = row.get("probabilities")
    if not probabilities:
        raise ValueError(f"Missing probabilities: {unit_id(row)}")
    if any(not isinstance(value, (int, float)) or not math.isfinite(value)
           or not 0 <= value <= 1 for value in probabilities.values()):
        raise ValueError(f"Invalid probability: {unit_id(row)}")
    if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-6):
        raise ValueError(f"Unnormalised probabilities: {unit_id(row)}")
    if row.get("ground_truth") not in probabilities:
        raise ValueError(f"Invalid ground truth: {unit_id(row)}")
    if set(row.get("options", probabilities)) != set(probabilities):
        raise ValueError(f"Options mismatch: {unit_id(row)}")


def brier(row):
    return sum((value - float(option == row["ground_truth"])) ** 2
               for option, value in row["probabilities"].items())


def hit(row):
    probabilities = row["probabilities"]
    maximum = max(probabilities.values())
    tied = [option for option, value in probabilities.items()
            if math.isclose(value, maximum, rel_tol=0, abs_tol=1e-12)]
    return 1.0 / len(tied) if row["ground_truth"] in tied else 0.0


def near_uniform(row, tolerance=0.005):
    values = list(row["probabilities"].values())
    deviation = max(abs(value - 1.0 / len(values)) for value in values)
    return deviation <= 1e-12 if tolerance == 0 else deviation < tolerance


def ensemble(rows):
    reference = rows[0]
    for row in rows:
        if (row["ground_truth"] != reference["ground_truth"]
                or set(row["probabilities"]) != set(reference["probabilities"])):
            raise ValueError("Cannot average incompatible outcomes")
        if row.get("evidence_text") != reference.get("evidence_text"):
            raise ValueError("Cannot average reads of different evidence")
        if row.get("question") != reference.get("question"):
            raise ValueError("Cannot average reads of different questions")
    return {
        "ground_truth": reference["ground_truth"],
        "probabilities": {
            option: mean(row["probabilities"][option] for row in rows)
            for option in reference["probabilities"]
        },
    }


def interval(by_event, grouping=None, draws=BOOTSTRAPS):
    """Equal-event estimand; retain all measurements of a sampled event."""
    if not by_event:
        raise ValueError("An interval requires observations")
    grouped = {}
    for event, values in sorted(by_event.items()):
        group = grouping.get(event, event) if grouping else event
        grouped.setdefault(group, []).append(mean(values))
    totals = np.array([sum(values) for values in grouped.values()])
    counts = np.array([len(values) for values in grouped.values()])
    generator = np.random.default_rng(SEED)
    sampled = generator.integers(0, len(grouped), size=(draws, len(grouped)))
    bootstrap = totals[sampled].sum(axis=1) / counts[sampled].sum(axis=1)
    limits = np.quantile(bootstrap, [0.025, 0.975])
    return {
        "mean": float(totals.sum() / counts.sum()),
        "low": float(limits[0]), "high": float(limits[1]),
        "n_events": len(by_event), "n_clusters": len(grouped),
    }


def load_campaigns(root):
    campaigns = {}
    record_count = 0
    for model, folder in MODELS.items():
        campaigns[model] = {}
        for filename in ["event_results.json", *A_FILES, C_FILE]:
            path = root / "02_campaigns" / folder / filename
            if not path.exists():
                if model == "Qwen2.5-14B" and filename == A_FILES[0]:
                    continue
                raise FileNotFoundError(path)
            rows = read_json(path, root)
            if len(rows) != 90 or len({unit_id(row) for row in rows}) != 90:
                raise ValueError(f"Expected 90 unique campaign units: {path}")
            for row in rows:
                validate_row(row)
            record_count += len(rows)
            campaigns[model][filename] = {
                (row["event_id"], row["condition"]): row for row in rows
                if unit_id(row) not in GAPS.get((model, filename), set())
            }
    return campaigns, record_count


def evaluator_views(campaigns):
    views = {"A_ensemble": {}, "A_mean_score": {}, "C_single": {}}
    for model, files in campaigns.items():
        for view in views.values():
            view[model] = {}
        for key, primary in files["event_results.json"].items():
            reads = [files[filename][key] for filename in A_FILES
                     if filename in files and key in files[filename]]
            if reads[0].get("evidence_text") != primary.get("evidence_text"):
                raise ValueError(f"Evaluator A evidence differs: {model} {key}")
            combined = ensemble(reads)
            views["A_ensemble"][model][key] = {
                "brier": brier(combined), "hit": hit(combined),
                "k": len(combined["probabilities"]),
            }
            views["A_mean_score"][model][key] = {
                "brier": mean(brier(row) for row in reads),
                "hit": mean(hit(row) for row in reads),
                "k": len(combined["probabilities"]),
            }
            independent = files[C_FILE][key]
            if independent.get("evidence_text") != primary.get("evidence_text"):
                raise ValueError(f"Evaluator C evidence differs: {model} {key}")
            views["C_single"][model][key] = {
                "brier": brier(independent), "hit": hit(independent),
                "k": len(independent["probabilities"]),
            }
    return views


def forecast_summary(view, events, grouping=None):
    per_model = {}
    brier_differences = {event: [] for event in events}
    accuracy_differences = {event: [] for event in events}
    for model, units in view.items():
        per_model[model] = {
            "brier_B": mean(units[event, "B"]["brier"] for event in events),
            "brier_C": mean(units[event, "C"]["brier"] for event in events),
            "accuracy_B": mean(units[event, "B"]["hit"] for event in events),
            "accuracy_C": mean(units[event, "C"]["hit"] for event in events),
        }
        for event in events:
            brier_differences[event].append(
                units[event, "C"]["brier"] - units[event, "B"]["brier"])
            accuracy_differences[event].append(
                units[event, "B"]["hit"] - units[event, "C"]["hit"])
    return {
        "events": events, "models": per_model,
        "accuracy_B": mean(values["accuracy_B"] for values in per_model.values()),
        "chance_reference": mean(1.0 / units[event, "B"]["k"]
                                 for units in view.values() for event in events),
        "delta_brier": interval(brier_differences, grouping),
        "delta_accuracy": interval(accuracy_differences, grouping),
        "event_brier_differences": brier_differences,
    }


def paired_audit(campaigns):
    rows, pooled_pairs = [], []
    for model in list(MODELS)[:3]:
        files, pairs = campaigns[model], []
        for key, original in files["event_results.json"].items():
            event, condition = key
            if condition not in ("B", "C"):
                continue
            if model == "Llama-3.1-8B" and event not in LLAMA_PAIRED:
                continue
            second = files[A_FILES[0]][key]
            for field in ("evidence_text", "question", "options", "ground_truth"):
                if original.get(field) != second.get(field):
                    raise ValueError(f"Paired input mismatch: {model} {key} {field}")
            pairs.append((original, second))
        rows.append({
            "model": model, "n": len(pairs),
            "J_near_uniform": sum(near_uniform(pair[0]) for pair in pairs),
            "A_near_uniform": sum(near_uniform(pair[1]) for pair in pairs),
        })
        pooled_pairs.extend(pairs)
    counts = {
        str(tolerance): {
            "J": sum(near_uniform(pair[0], tolerance) for pair in pooled_pairs),
            "A": sum(near_uniform(pair[1], tolerance) for pair in pooled_pairs),
        } for tolerance in (0, 0.005, 0.01, 0.02)
    }
    return {"models": rows, "n": len(pooled_pairs), "tolerance_sensitivity": counts,
            "verified_fields": ["evidence_text", "question", "options", "ground_truth"]}


def repeated_read_audit(campaigns):
    output = {}
    for model, files in campaigns.items():
        spreads, exact = [], 0
        for key in files["event_results.json"]:
            reads = [files[filename][key] for filename in A_FILES
                     if filename in files and key in files[filename]]
            ensemble(reads)
            scores = [brier(row) for row in reads]
            spreads.append(max(scores) - min(scores))
            exact += int(all(row["probabilities"] == reads[0]["probabilities"]
                             for row in reads[1:]))
        output[model] = {
            "n_units": len(spreads), "mean_brier_range": mean(spreads),
            "max_brier_range": max(spreads), "exact_vector_agreement": exact,
            "n_files": sum(filename in files for filename in A_FILES),
        }
    return output


def cot_summary(root, view):
    path = root / "04_experiments/04_single-agent-cot-baseline/single_agent_cot_baseline_results.json"
    rows = read_json(path, root)
    grouped = {}
    for row in rows:
        if row.get("status") == "success":
            validate_row(row)
            grouped.setdefault((row["model"], row["event_id"]), []).append(row)
    output = {"n_records": len(rows), "arms": {}, "pooled": {}}
    scopes = {scope: {event: [] for event in POST_RELEASE_EVENTS}
              for scope in ("identity_matched", "all_four")}
    for cot_model, (swarm_model, matched) in COT_ARMS.items():
        by_variant = {variant: {} for variant in ("single", "ensemble3", "temperature0")}
        accuracies = []
        for event in POST_RELEASE_EVENTS:
            repeats = sorted(grouped[cot_model, event], key=lambda row: row["repeat"])
            if [row["repeat"] for row in repeats] != [1, 2, 3]:
                raise ValueError(f"Missing CoT replicate: {cot_model} {event}")
            combined = ensemble(repeats)
            scores = {"single": mean(brier(row) for row in repeats),
                      "ensemble3": brier(combined), "temperature0": brier(repeats[0])}
            accuracies.append(mean(hit(row) for row in repeats))
            for variant, score in scores.items():
                by_variant[variant][event] = [score - view[swarm_model][event, "B"]["brier"]]
            difference = by_variant["single"][event][0]
            scopes["all_four"][event].append(difference)
            if matched:
                scopes["identity_matched"][event].append(difference)
        output["arms"][cot_model] = {
            "identity_matched": matched, "swarm_model": swarm_model,
            "single_accuracy": mean(accuracies),
            "variants": {variant: interval(values) for variant, values in by_variant.items()},
        }
    output["pooled"] = {scope: interval(values) for scope, values in scopes.items()}
    output["all_four_single_accuracy"] = mean(
        values["single_accuracy"] for values in output["arms"].values())
    return output


def truncation_summary(root):
    directory = root / "04_experiments/03_truncation-grid/scored_arms"
    cells, counts = {}, {}
    for arm in ("q14b_unconstrained", "q14b_enforced"):
        for level in ("2k", "5k", "8k", "full"):
            rows = read_json(directory / f"event_results_trunc_{level}_{arm}.json", root)
            scored = {}
            for row in rows:
                if row.get("probabilities"):
                    validate_row(row)
                    scored[(row["event_id"], row["condition"])] = row
            cells[arm, level] = scored
            counts[f"{arm}/{level}"] = {
                "attempted": len(rows), "scored": len(scored),
                "near_uniform": sum(near_uniform(row) for row in scored.values()),
            }
    contrasts = {}
    for label, first, second in (
        ("short_minus_full", ("q14b_unconstrained", "2k"), ("q14b_unconstrained", "full")),
        ("off_minus_on_full", ("q14b_unconstrained", "full"), ("q14b_enforced", "full")),
    ):
        left, right = cells[first], cells[second]
        differences, discordant = {}, [0, 0]
        for key in sorted(left.keys() & right.keys()):
            left_flag, right_flag = near_uniform(left[key]), near_uniform(right[key])
            differences.setdefault(key[0], []).append(float(left_flag) - float(right_flag))
            discordant[0] += int(left_flag and not right_flag)
            discordant[1] += int(right_flag and not left_flag)
        contrasts[label] = {
            "paired_units": sum(len(values) for values in differences.values()),
            "discordant_first_only": discordant[0], "discordant_second_only": discordant[1],
            "event_cluster_interval": interval(differences),
        }
    differences, paired_count = {}, 0
    for level in ("2k", "5k", "8k", "full"):
        left, right = cells["q14b_unconstrained", level], cells["q14b_enforced", level]
        for key in sorted(left.keys() & right.keys()):
            if left[key].get("evidence_text") != right[key].get("evidence_text"):
                raise ValueError(f"Enforcement arms have different evidence: {level} {key}")
            differences.setdefault(key[0], []).append(
                float(near_uniform(left[key])) - float(near_uniform(right[key])))
            paired_count += 1
    contrasts["off_minus_on_all_lengths"] = {
        "paired_units": paired_count, "event_cluster_interval": interval(differences),
    }
    return {"cells": counts, "contrasts": contrasts}


def transfer_summary(root, campaigns):
    observations = read_json(
        root / "04_experiments/02_degeneracy-transfer/degeneracy_transfer.json", root)["detail"]
    primary = campaigns["Mistral-7B"]["event_results.json"]
    output = {}
    for row in observations:
        model = row["model"]
        summary = output.setdefault(model, {
            "attempted": 0, "parsed": 0, "near_uniform": 0, "overlap_with_J": 0,
        })
        summary["attempted"] += 1
        if not row.get("parsed") or not row.get("probabilities"):
            continue
        summary["parsed"] += 1
        flag = near_uniform(row)
        summary["near_uniform"] += int(flag)
        original = primary[row["event_id"], row["condition"]]
        summary["overlap_with_J"] += int(flag and near_uniform(original))
    return output


def injection_summary(root):
    bank = read_json(root / "01_benchmark/injections/step30_injection_bank.json", root)["events"]
    ratios = [len(row["relevant_update"]["body"]) / len(row["null_update"]["body"]) for row in bank]
    return {
        "body_character_ratio_min": min(ratios),
        "body_character_ratio_median": float(np.median(ratios)),
        "body_character_ratio_max": max(ratios),
        "unique_null_bodies": len({row["null_update"]["body"] for row in bank}),
        "wrong_topic_ids_documented": sorted(WRONG_INJECTIONS),
    }


def estimate_text(estimate):
    return f"{estimate['mean']:+.3f} [{estimate['low']:+.3f}, {estimate['high']:+.3f}]"


def write_tables(result, output):
    commands = []
    def define(name, body):
        commands.append("\\newcommand{\\" + name + "}{" + body + "}")
    define("AuditRows", "\n".join(
        f"{row['model']} & {row['n']} & {row['J_near_uniform']} & {row['A_near_uniform']} \\\\"
        for row in result["paired_audit"]["models"]))
    define("ForecastRows", "\n".join(
        f"{model} & {values['accuracy_B']:.3f} & {values['accuracy_C']:.3f} & "
        f"{values['brier_B']:.3f} & {values['brier_C']:.3f} \\\\"
        for model, values in result["forecast"]["A_ensemble"]["models"].items()))
    define("SensitivityRows", "\n".join(
        f"{label} & {summary['delta_brier']['n_events']} & "
        f"$ {estimate_text(summary['delta_brier'])} $ \\\\"
        for label, summary in [
            ("Evaluator A, averaged vector", result["forecast"]["A_ensemble"]),
            ("Evaluator A, mean read score", result["forecast"]["A_mean_score"]),
            ("Evaluator C, single read", result["forecast"]["C_single"]),
            ("A, excluding input/gap events", result["sensitivity"]["exclude_input_and_gap"]),
            ("A, US election grouped", result["sensitivity"]["group_US_election"]),
            ("A, excluding US election", result["sensitivity"]["exclude_US_election"]),
        ]))
    define("NoiseRows", "\n".join(
        f"{model} & {values['n_files']} & {values['exact_vector_agreement']}/90 & "
        f"{values['mean_brier_range']:.3f} \\\\"
        for model, values in result["repeated_reads"].items()))
    define("CotRows", "\n".join(
        f"{model} & {'Yes' if values['identity_matched'] else 'No'} & "
        f"{values['single_accuracy']:.3f} & $ {estimate_text(values['variants']['single'])} $ \\\\"
        for model, values in result["cot"]["arms"].items()))
    define("TruncationRows", "\n".join(
        f"{level} & {result['truncation']['cells']['q14b_unconstrained/'+level]['near_uniform']}/"
        f"{result['truncation']['cells']['q14b_unconstrained/'+level]['scored']} & "
        f"{result['truncation']['cells']['q14b_enforced/'+level]['near_uniform']}/"
        f"{result['truncation']['cells']['q14b_enforced/'+level]['scored']} \\\\"
        for level in ("2k", "5k", "8k", "full")))
    for name, estimate in [
        ("PooledBrier", result["forecast"]["A_ensemble"]["delta_brier"]),
        ("EvaluatorCBrier", result["forecast"]["C_single"]["delta_brier"]),
        ("MatchedCotBrier", result["cot"]["pooled"]["identity_matched"]),
    ]:
        define(name, estimate_text(estimate))
    define("PooledAccuracy", f"{100*result['forecast']['A_ensemble']['accuracy_B']:.1f}")
    define("CotAccuracy", f"{100*result['cot']['all_four_single_accuracy']:.1f}")
    (output / "paper_tables.tex").write_text("\n\n".join(commands) + "\n", encoding="utf-8")


def write_figures(result, output):
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    rows = result["paired_audit"]["models"]
    positions = np.arange(len(rows))
    axes[0].bar(positions - 0.18, [row["J_near_uniform"]/row["n"] for row in rows],
                0.36, label="Evaluator J", color="#b45a3c")
    axes[0].bar(positions + 0.18, [row["A_near_uniform"]/row["n"] for row in rows],
                0.36, label="Evaluator A, one read", color="#3074aa")
    axes[0].set_xticks(positions, ["Llama\n(n=12)", "Mistral\n(n=60)", "Qwen-7B\n(n=60)"])
    axes[0].set_ylabel("Near-uniform fraction")
    axes[0].set_ylim(0, 1.12)
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].set_title("Fixed-evidence evaluator comparison")
    sensitivity = [
        ("A: averaged vector", result["forecast"]["A_ensemble"]["delta_brier"]),
        ("A: mean read score", result["forecast"]["A_mean_score"]["delta_brier"]),
        ("C: single read", result["forecast"]["C_single"]["delta_brier"]),
        ("A: input/gap exclusions", result["sensitivity"]["exclude_input_and_gap"]["delta_brier"]),
        ("A: US election grouped", result["sensitivity"]["group_US_election"]["delta_brier"]),
    ]
    for position, (label, estimate) in enumerate(sensitivity):
        axes[1].plot([estimate["low"], estimate["high"]], [position, position], color="#3074aa")
        axes[1].plot(estimate["mean"], position, "o", color="#3074aa")
    axes[1].set_yticks(range(len(sensitivity)), [label for label, _ in sensitivity])
    axes[1].invert_yaxis()
    axes[1].axvline(0, linestyle="--", color="gray")
    axes[1].set_xlabel("Brier difference: C minus B")
    axes[1].set_title("Exploratory cluster intervals")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
    figure.savefig(output / "fig_paper_audit.png", dpi=220)
    plt.close(figure)


def default_root():
    for directory in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        for candidate in (directory, directory / "ECNBENCH-RELEASE"):
            if (candidate / "02_campaigns").is_dir():
                return candidate
    raise FileNotFoundError("Specify --data-root pointing to ECNBENCH-RELEASE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    root = (arguments.data_root or default_root()).resolve()
    output = arguments.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    INPUT_HASHES.clear()
    campaigns, record_count = load_campaigns(root)
    views = evaluator_views(campaigns)
    forecast = {name: forecast_summary(view, POST_RELEASE_EVENTS) for name, view in views.items()}
    exclusions = WRONG_INJECTIONS | {"C9"}
    sensitivity = {
        "exclude_input_and_gap": forecast_summary(
            views["A_ensemble"], [event for event in POST_RELEASE_EVENTS if event not in exclusions]),
        "group_US_election": forecast_summary(
            views["A_ensemble"], POST_RELEASE_EVENTS,
            {event: "US_election_2024" for event in US_ELECTION_EVENTS}),
        "exclude_US_election": forecast_summary(
            views["A_ensemble"], [event for event in POST_RELEASE_EVENTS if event not in US_ELECTION_EVENTS]),
    }
    result = {
        "analysis_version": "2026-09-06",
        "scope": "Retrospective measurement audit; no simulation or API calls.",
        "inference": {
            "bootstrap_draws": BOOTSTRAPS, "seed": SEED,
            "unit": "event; all model readings retained together",
            "estimand": "equal-weight mean over events and the four fixed campaigns",
            "p_values": "not reported; no independent-unit or fractional-hit exact test",
            "limitations": "Exploratory percentile intervals; event dependence, selection, "
                           "and evaluator knowledge leakage remain unresolved.",
        },
        "campaign_records_validated": record_count,
        "stale_reads_excluded": sum(len(values) for values in GAPS.values()),
        "paired_audit": paired_audit(campaigns),
        "repeated_reads": repeated_read_audit(campaigns),
        "forecast": forecast, "sensitivity": sensitivity,
        "cot": cot_summary(root, views["A_ensemble"]),
        "truncation": truncation_summary(root),
        "transfer": transfer_summary(root, campaigns),
        "injections": injection_summary(root),
        "input_sha256": INPUT_HASHES,
    }
    (output / "paper_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_tables(result, output)
    write_figures(result, output)
    print(f"Validated {record_count} campaign rows; excluded four stale rereads.")
    print("Paired:", result["paired_audit"])
    for name, summary in forecast.items():
        print(name, estimate_text(summary["delta_brier"]))
    print("CoT matched:", estimate_text(result["cot"]["pooled"]["identity_matched"]))
    print(f"Generated paper_results.json, paper_tables.tex and fig_paper_audit.png in {output}")
    return result, output


if __name__ == "__main__":
    main()
