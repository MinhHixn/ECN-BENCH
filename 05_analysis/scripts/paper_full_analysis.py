"""Extended offline tables for the full ECN-BENCH technical report."""
import argparse
import json
from pathlib import Path
from statistics import mean

import paper_analysis as audit


def tex(value):
    value = str(value).replace("\u2013", "--").replace("\u2014", "---")
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
                     "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"}
    return "".join(substitutions.get(character, character) for character in str(value))


def event_order(event):
    return event[0], int(event[1:])


def table(caption, label, columns, headings, rows):
    return "\n".join([
        r"\begin{table*}[!htbp]", r"\centering\small",
        r"\caption{" + caption + "}", r"\label{" + label + "}",
        r"\begin{tabular}{" + columns + "}", r"\toprule",
        " & ".join(headings) + r" \\", r"\midrule",
        *[" & ".join(row) + r" \\" for row in rows],
        r"\bottomrule", r"\end{tabular}", r"\end{table*}", "",
    ])


def extended_results(root):
    audit.INPUT_HASHES.clear()
    campaigns, count = audit.load_campaigns(root)
    views = audit.evaluator_views(campaigns)
    records = {}
    question_mismatches = []
    catalog = {}
    for model, files in campaigns.items():
        records[model] = {}
        for key, primary in files["event_results.json"].items():
            event, condition = key
            reads = [files[filename][key] for filename in audit.A_FILES
                     if filename in files and key in files[filename]]
            combined = audit.ensemble(reads)
            for reading in [*reads, files[audit.C_FILE][key]]:
                for field in ("question", "options", "ground_truth", "evidence_text"):
                    if reading.get(field) != primary.get(field):
                        raise ValueError(f"Within-unit input mismatch: {model} {key} {field}")
            records[model][event + "/" + condition] = {
                "event": event, "condition": condition,
                "primary_brier": audit.brier(primary),
                "primary_accuracy": audit.hit(primary),
                "ensemble_brier": audit.brier(combined),
                "ensemble_accuracy": audit.hit(combined),
                "ensemble_max_probability": max(combined["probabilities"].values()),
                "ensemble_uniform": audit.near_uniform(combined),
                "n_A_reads": len(reads),
                "C_evaluator_brier": audit.brier(files[audit.C_FILE][key]),
                "C_evaluator_accuracy": audit.hit(files[audit.C_FILE][key]),
                "evidence_characters": len(primary.get("evidence_text", "")),
            }
            previous = catalog.setdefault(event, {
                "question": primary["question"], "options": primary["options"],
                "outcome": primary["ground_truth"],
                "post_release": event in audit.POST_RELEASE_EVENTS,
                "wrong_injection": event in audit.WRONG_INJECTIONS,
            })
            if previous["question"] != primary["question"]:
                if model != "Qwen2.5-14B" or event != "T1":
                    raise ValueError(f"Unexpected question mismatch: {model} {key}")
                question_mismatches.append({
                    "model": model, "event": event, "condition": condition,
                    "expected": previous["question"], "observed": primary["question"],
                })
            if (previous["options"] != primary["options"]
                    or previous["outcome"] != primary["ground_truth"]):
                raise ValueError(f"Catalogue mismatch: {model} {key}")
    events = sorted(catalog, key=event_order)
    aligned_events = [event for event in events if event != "T1"]
    summaries = {name: audit.forecast_summary(view, aligned_events) for name, view in views.items()}
    bins = {}
    for model, units in records.items():
        bins[model] = []
        for lower, upper in [(0, .25), (.25, .5), (.5, .75), (.75, 1.0)]:
            selected = [row for row in units.values()
                        if row["condition"] == "B" and row["event"] != "T1"
                        and lower <= row["ensemble_max_probability"]
                        and (row["ensemble_max_probability"] < upper
                             or upper == 1.0 and row["ensemble_max_probability"] == 1.0)]
            bins[model].append({
                "lower": lower, "upper": upper, "count": len(selected),
                "mean_confidence": mean(row["ensemble_max_probability"] for row in selected) if selected else None,
                "tie_aware_accuracy": mean(row["ensemble_accuracy"] for row in selected) if selected else None,
            })
        assert sum(row["count"] for row in bins[model]) == 29
    return {
        "analysis_version": "2026-09-06-full",
        "scope": "Additional descriptive tables; no new model observations.",
        "campaign_records_validated": count,
        "catalog": catalog, "units": records, "aligned_event_summaries": summaries,
        "aligned_events": aligned_events, "question_mismatches": question_mismatches,
        "modal_calibration_bins": bins,
        "input_sha256": dict(audit.INPUT_HASHES),
    }


def write_tables(result, output):
    sections = []
    events = sorted(result["catalog"], key=event_order)
    sections.append(r"\subsection{Complete question and outcome register}")
    sections.append("Recorded outcomes are reproduced for audit, not independently adjudicated. "
                    "Post-release denotes the retained date-based subset, not freedom from evaluator knowledge. "
                    "Wrong injection identifies the known stale-bank topic mismatch.")
    for event in events:
        record = result["catalog"][event]
        sections.extend([
            r"\paragraph*{" + tex(event) + "} " + tex(record["question"]),
            r"\begin{itemize}",
            r"\item Recorded outcome: " + tex(record["outcome"]) + ".",
            r"\item Ordered options: " + "; ".join(tex(option) for option in record["options"]) + ".",
            r"\item Post-release subset: " + ("yes" if record["post_release"] else "no")
            + "; wrong-topic injection: " + ("yes" if record["wrong_injection"] else "no") + ".",
            r"\end{itemize}",
        ])
    sections.append(r"\clearpage\subsection{Question-aligned summaries and prefix diagnostics}")
    sections.append("T1 is excluded from every campaign in aggregate comparisons: "
                    "Qwen2.5-14B T1 asks about a Fed decision rather than the UAW contract question. "
                    "The options and recorded outcome coincide, so vector validation alone misses it. "
                    "Per-event tables retain all 30 stored IDs, explicitly including this invalid pairing. "
                    "The primary 20-event post-release subset never includes T1.")
    aligned = result["aligned_events"]
    rows = []
    for model, units in result["units"].items():
        selected = [units[event + "/B"] for event in aligned]
        rows.append([tex(model),
                     f"{mean(units[event + '/A']['ensemble_brier'] for event in aligned):.3f}",
                     f"{mean(row['ensemble_brier'] for row in selected):.3f}",
                     f"{mean(units[event + '/C']['ensemble_brier'] for event in aligned):.3f}",
                     f"{mean(row['ensemble_accuracy'] for row in selected):.3f}",
                     str(sum(row["ensemble_uniform"] for row in selected))])
    sections.append(table(
        "The 29 question-aligned events under Evaluator A's averaged vector. T1 is excluded across campaigns. The A-condition column is a rereading "
        "of shared reference evidence, not an independently executed baseline for each model.",
        "tab:full_ensemble_summary", "lrrrrr",
        ["Campaign", "BS A", "BS B", "BS C", "Acc. B", "Uniform B"], rows))
    rows = []
    for model, units in result["units"].items():
        for prefix in "CST":
            selected = [units[event + "/B"] for event in aligned if event.startswith(prefix)]
            rows.append([tex(model), prefix, str(len(selected)),
                         f"{mean(row['ensemble_brier'] for row in selected):.3f}",
                         f"{mean(row['ensemble_accuracy'] for row in selected):.3f}"])
    sections.append(table(
        "Descriptive prefix groups under A's averaged vector, Condition B. C/S/T are record "
        "identifiers, not a validated domain taxonomy. Campaign identities and serving remain confounded.",
        "tab:full_prefix", "llrrr", ["Campaign", "Prefix", "Events", "BS B", "Acc. B"], rows))
    sections.append(r"\clearpage\subsection{Modal confidence and empirical accuracy}")
    sections.append("These are top-label confidence bins: confidence is the maximum forecast probability, "
                    "and accuracy uses the same tie credit as the main analysis. Confidence is not the "
                    "probability assigned to the known ground-truth option. Small bin counts, reuse of events "
                    "and retrospective evaluator exposure preclude population calibration claims. "
                    "No probability recalibration was fitted to these outcomes.")
    rows = []
    for model, bins in result["modal_calibration_bins"].items():
        for cell in bins:
            rows.append([tex(model), f"{cell['lower']:.2f}--{cell['upper']:.2f}", str(cell["count"]),
                         "---" if cell["mean_confidence"] is None else f"{cell['mean_confidence']:.3f}",
                         "---" if cell["tie_aware_accuracy"] is None else f"{cell['tie_aware_accuracy']:.3f}"])
    sections.append(table(
        "Condition B modal-confidence bins over 29 aligned events per campaign (T1 excluded), Evaluator A averaged vectors. "
        "Bins are left-closed/right-open except the final bin, which includes one.",
        "tab:full_calibration", "llrrr",
        ["Campaign", "Confidence bin", "Events", "Mean confidence", "Tie-aware accuracy"], rows))
    for model, units in result["units"].items():
        sections.append(r"\clearpage\subsection{" + tex(model) + ": full per-event records}")
        rows = []
        for event in events:
            unit_a, unit_b, unit_c = [units[event + "/" + condition] for condition in "ABC"]
            rows.append([event,
                         f"{unit_a['ensemble_brier']:.4f}", f"{unit_b['ensemble_brier']:.4f}",
                         f"{unit_c['ensemble_brier']:.4f}",
                         f"{unit_c['ensemble_brier'] - unit_b['ensemble_brier']:+.4f}",
                         f"{unit_b['ensemble_accuracy']:.3f}", str(unit_b["n_A_reads"]),
                         f"{unit_b['C_evaluator_brier']:.4f}"])
        suffix = model.lower().replace(".", "").replace("-", "")
        sections.append(table(
            tex(model) + ": all 30 stored event IDs; Qwen2.5-14B T1 is a different question and is not a valid cross-campaign pair. BS A/B/C and accuracy use Evaluator A's averaged vector. "
            "Last column uses the single Evaluator C reading of Condition B. These are two different "
            "extraction budgets. Read count is for B; stale exclusions in other conditions remain applied.",
            "tab:full_events_" + suffix, "lrrrrrrr",
            ["Event", "BS A", "BS B", "BS C", "C minus B", "Acc. B", "Reads B", "Eval. C BS B"], rows))
        rows = []
        for event in events:
            unit_b, unit_c = units[event + "/B"], units[event + "/C"]
            rows.append([event, f"{unit_b['primary_brier']:.4f}", f"{unit_c['primary_brier']:.4f}",
                         str(unit_b["evidence_characters"]), str(unit_c["evidence_characters"]),
                         f"{unit_b['ensemble_max_probability']:.3f}",
                         "yes" if unit_b["ensemble_uniform"] else "no"])
        sections.append(table(
            tex(model) + ": primary-file Brier and surviving evidence size. Primary-file readings are "
            "instrument-mixed for recovered Llama and Qwen2.5-14B units and must not all be called "
            "Evaluator J. Last two columns describe A's averaged Condition B vector. Character count "
            "describes scored evidence, not all generated discussion.",
            "tab:full_primary_" + suffix, "lrrrrrl",
            ["Event", "Primary BS B", "Primary BS C", "Chars B", "Chars C", "A max prob.", "A uniform"], rows))
    (output / "paper_full_tables.tex").write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    root = (arguments.data_root or audit.default_root()).resolve()
    output = arguments.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = extended_results(root)
    (output / "paper_full_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_tables(result, output)
    print(f"Extended tables: {len(result['catalog'])} events, four campaigns, all 360 units.")
    print("No model or simulation calls.")


if __name__ == "__main__":
    main()
