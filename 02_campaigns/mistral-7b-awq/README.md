# Mistral-7B-Instruct-v0.1 campaign — file guide

> Historical campaign notes, retained for provenance. Numerical interpretations and inferential claims below are superseded by the September 2026 revision. See [current provenance](../../00_docs/PROVENANCE.md) and [offline reanalysis](../../05_analysis/README.md); stored source observations are unchanged.

30 events x 3 conditions = 90 units.

## Data files, in the order the paper uses them

- `event_results.json` — **Evaluator J** (July 2026, local DeepSeek-R1-14B, structured-output enforcement silently disabled — Section~\ref{sec:epistemic_mapping}). This is the manuscript's primary data; the pipeline refuses to overwrite it (`--allow-july-overwrite` required).
- `event_results_evaluatorB_openrouter.json` — **Evaluator A**, 1st read (August 2026, `deepseek/deepseek-v4-flash-0731` via OpenRouter, schema-enforced). This is the single pass reported in Section~\ref{sec:replication_central}/Table~\ref{tab:replication}.
- `event_results_evaluatorA_repeat1.json`, `repeat2.json`, `repeat3.json` — 3 further independent Evaluator A reads (same model/settings), added so every unit has 4 total Evaluator A reads. Used for the instrument-spread and robust (multi-read-mean) metrics in Section~\ref{sec:four_model_extension}.
- `event_results_evaluatorC_gptlunapro.json` — **Evaluator C**, `openai/gpt-5.6-luna-pro`, 1 independent read. Note: this model rejects the pipeline's strict JSON schema (`invalid_json_schema` on `validated_scales`) and falls back to unconstrained `json_object` mode for every call — same enforcement level as Evaluator A, not stronger.
- `summary.json` — campaign-level summary computed from `event_results.json` only (Evaluator J). Predates the reproducibility work below; still accurate for what it describes.
- `reproducibility_analysis.json` — **the new, saved analysis** backing Section~\ref{sec:four_model_extension} and Table~\ref{tab:four_model_clean}: instrument spread across the 4 Evaluator A reads, cross-evaluator agreement (A vs C), and condition-level Brier/accuracy/lift/susceptibility/flat-rate, computed three ways (all available events, the 20 globally-clean events, and the 17 clean events common to all 4 models). Regenerate with the script referenced in `/reproducibility_analysis_master.json` at the repo root.
- `run_manifest.json`, `traces/`, per-unit directories (`C1_A_r1/`, ...) — original HPC run artifacts, unrelated to the evaluator-replication work.
- `archive_pre_session_repairs/` — earlier, superseded repair attempts on `event_results.json` and `event_results_evaluatorB_openrouter.json` (`.bak_*`, `.hybrid_*`). Kept as audit trail only; not used by any current analysis.

## Known gaps

None — all 4 Evaluator A reads and the Evaluator C read are complete for all 90 units. (Mistral is the model whose apparent uncontrolled-data harm from simulation, lift $-0.224$, mostly disappears under contamination control, lift $-0.020$ on the 17 clean events — see Section~\ref{sec:four_model_extension}.)

## 2026-08-16 fix: `evaluator_dimension_labels` was stale in all 5 non-primary files

`run_openrouter_eval_official.py` refreshed `probabilities`/`mcq_dimensions`/`validated_scales` per read but never touched `evaluator_dimension_labels`, so all 90 units in `evaluatorA_repeat1/2/3`, `evaluatorB_openrouter`, and `evaluatorC_gptlunapro` carried the identical label set copied from `event_results.json`'s original pass, regardless of that file's own (genuinely different) `mcq_dimensions`. Not used by any current table (`build_reproducibility_analysis.py` only reads `probabilities`; `tab:kappa_summary` is sourced from `event_results.json`'s own internal run1/run2 pair, unaffected) — but misleading if read directly. Fixed in code, then backfilled locally from each file's already-stored, already-independent `mcq_dimensions` (no new evaluator calls). The field is now a single-read dominant-bucket label per dimension (`evaluator_dimension_label_basis: "single_read"`), not a run1/run2 pair — this script only ever makes one evaluator call per unit, so it can't honestly produce the latter. Pre-fix originals backed up under `figures_backup_pre_dimension_label_fix/evaluator_files/` at the repo root.
