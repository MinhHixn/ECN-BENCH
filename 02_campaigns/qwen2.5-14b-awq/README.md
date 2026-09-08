# Qwen2.5-14B — 4th campaign (recovered 2026-08-14, completed 30/30 2026-08-21)

> Historical campaign notes, retained for provenance. Numerical interpretations and inferential claims below are superseded by the September 2026 revision. See [current provenance](../../00_docs/PROVENANCE.md) and [offline reanalysis](../../05_analysis/README.md); stored source observations are unchanged.

**This is the canonical stored Qwen2.5-14B campaign: 30 event IDs and 90 units.** Use this directory, not the older paths below. The September 2026 full-register audit found that all three T1 units ask about the November 2024 Fed meeting rather than the UAW contract event used by the other campaigns. T1 is retained unchanged but excluded from the extended 29-event question-aligned aggregates; the primary 20-event analysis is unaffected. Thus 30 stored IDs must not be described as 30 cross-model matched questions.

## What's here

- `event_results.json` — 90 rows (30 events × 3 conditions). The original 72 rows
  (24 events) were rescored via the same `rescore()` used for the other 3 models'
  campaigns, using whatever evaluator ran on the original HPC job. The 18 rows for
  the 6 recovered events (T3, T4, T5, T6, C6, T8; see "2026-08-21" below) were scored
  with `deepseek/deepseek-r1` via OpenRouter, the same substitute used for Llama's
  2026-08-16 outage repair when the local DeepSeek-R1-14B evaluator is unreachable.
  There is still no separate `event_results_evaluatorB_openrouter.json` for this
  model the way there is for the other three, since the original pass was never
  scorable at the time that pass was run for the other campaigns.
- `event_results_evaluatorA_repeat1.json`, `repeat2.json`, `repeat3.json` — 3
  independent Evaluator A reads (`deepseek/deepseek-v4-flash-0731` via OpenRouter,
  schema-enforced), now 90/90 rows each. Only 3, not 4: there is no original
  single-pass Evaluator A record to add as a fourth.
- `event_results_evaluatorC_gptlunapro.json` — Evaluator C, `openai/gpt-5.6-luna-pro`,
  1 independent read, now 90/90 rows. Same JSON-schema fallback caveat as the other 3
  models' files.
- `reproducibility_analysis.json` — the analysis backing
  Section~\ref{sec:four_model_extension} and Table~\ref{tab:four_model_clean}: instrument
  spread across the 3 Evaluator A reads, cross-evaluator agreement (A vs C), and
  condition-level Brier/accuracy/lift/susceptibility/flat-rate, computed on all 30
  available events and on the 20 that are also contamination-clean and shared with the
  other 3 models (grown from 17 once T6, C6, T8 were recovered). Regenerate with
  `python ECN-HPC-DEPLOY/build_reproducibility_analysis.py` from the repo root.
- `summary.json` — full-schema campaign summary, generated via
  `summarize_event_results()` (the same function used for Llama/Mistral/Qwen2.5-7B),
  computed from `event_results.json` only, now over all 90 rows. Regenerate with
  `python scratch/regen_qwen14b_summary.py` (or the equivalent inline call) after any
  change to `event_results.json`.
- `excluded_events_wrong_topic.json` — the 18 rows (6 events) originally excluded
  2026-08-14, kept for audit purposes. Superseded by the 2026-08-21 recovery below —
  do not merge these rows back in, they carry the wrong topic.

## Known gaps

`event_results_evaluatorA_repeat2.json` is missing 1 of 72 units: **T1_C_r1**. It hung
repeatedly against OpenRouter across 3 independent retry attempts and, with the user's
explicit sign-off, was accepted as a permanent gap rather than retried further. The row
still exists in the file but holds a stale, never-overwritten copy of `event_results.json`'s
original (non-Evaluator-A) value; `reproducibility_analysis.json` and
Section~\ref{sec:four_model_extension} explicitly exclude this row from `repeat2.json`
rather than double-counting a mismatched-evaluator value as a genuine read. T1 is not
among the 20 globally-clean events (Section~\ref{sec:cutoff}), so this gap does not
affect Table~\ref{tab:four_model_clean}.

## 2026-08-16 fix: `evaluator_dimension_labels` was stale in all 4 non-primary files

`run_openrouter_eval_official.py` refreshed `probabilities`/`mcq_dimensions`/`validated_scales` per read but never touched `evaluator_dimension_labels`, so all 72 units in `evaluatorA_repeat1/2/3` and `evaluatorC_gptlunapro` carried an identical label set regardless of that file's own (genuinely different) `mcq_dimensions`. Not used by any current table (`build_reproducibility_analysis.py` only reads `probabilities`) — but misleading if read directly. Fixed in code, then backfilled locally from each file's already-stored, already-independent `mcq_dimensions` (no new evaluator calls). The field is now a single-read dominant-bucket label per dimension (`evaluator_dimension_label_basis: "single_read"`). The T1_C_r1 stale-copy row noted above still gets a label, computed from its (pre-existing, stale) `mcq_dimensions` -- not a new problem, still excluded from `reproducibility_analysis.json` as before. Pre-fix originals backed up under `figures_backup_pre_dimension_label_fix/evaluator_files/` at the repo root.

## 2026-08-16: `C9_C_r1` has the same unreachable-endpoint corruption as the Llama campaign

While auditing the Llama-3.1-8B campaign's "69 units executed against an unreachable endpoint while recording `error: null` and `evaluator_fallback_used: false`" defect (Section~\ref{sec:outage}), the same signature was checked for across all 4 models. Mistral-7B and Qwen2.5-7B are clean (0 flat `round_jsd` series). Qwen2.5-14B has exactly **one** affected unit: `C9_C_r1` -- `error: null`, `evaluator_fallback_used: false`, but `round_jsd` is the flat placeholder `0.758277` repeated across all checkpoints, same as the Llama defect. `C9_A_r1` and `C9_B_r1` are unaffected.

Not fixed: `qwen2.5:14b` isn't available on either OpenRouter or Ollama Cloud (checked both 2026-08-16), so this unit can't be re-simulated the same way the Llama recovery was. Re-simulating it would require the original local vLLM/Ollama HPC path this model was served from. Left as a known, documented single-unit gap rather than silently trusted.

## 2026-08-21: the 6 wrong-topic events recovered — now 30/30

6 events (**T3, T4, T5, T6, C6, T8**) were originally simulated and scored against
the **wrong event topic**, because the 2026-08-14 campaign was built from the stale
`ECN-HPC-DEPLOY/data/events_raw.json` catalogue instead of the authoritative
`data/events_raw.json` at the repo root — the same class of ID-collision bug the
paper documents for the other 3 models' evaluator-replication pass, except here it
reached the simulation dossier itself (not just the evaluator's micro-questions), so
the affected units weren't recoverable by rescoring — the multi-agent swarm actually
deliberated about a different question entirely (e.g. T3 debated a Bitcoin price
threshold instead of the 2024 Taiwanese presidential election). See
`excluded_events_wrong_topic.json` for the original wrong-topic rows.

**Re-simulation, attempt 1 (2026-08-20), also invalid.** A SLURM job
(`run_qwen14b_6events_fix_gpu.slurm`) re-ran all 6 events, but its launch command
called `scripts/run_ecnbench_protocol.py --events-raw ../../data/events_raw.json`
from `ECN-HPC-DEPLOY/MiroFish-Offline/backend`, a relative path that resolves to the
*same stale* `ECN-HPC-DEPLOY/data/events_raw.json` — reproducing the identical bug
(verified: T3 again simulated as the Bitcoin question). That run's output is left on
disk under `.../qwen2.5_14b/ecnbench_20260820T133726352240Z/` as an audit trail; do
not use it.

**Re-simulation, attempt 2 (2026-08-21), correct.** Two SLURM jobs
(`run_qwen14b_3events_rootcat_A.slurm` for T3/T4/T5, `run_qwen14b_3events_rootcat_B.slurm`
for T6/C6/T8 — split in two because the `medium` QOS caps a user at 2 GPUs, so they
ran sequentially rather than in parallel) pointed `--events-raw`, `--seeds-dir` and
`--injection-bank` at absolute paths under `ecnbench_workspace/fix7_rootcat/data/` —
the authoritative catalogue and seed dossiers already staged there during the
2026-08-16 Llama outage repair for the same class of bug. Verified topic-correct for
all 18 units (6 events × A/B/C) against the root catalogue before scoring. The
injection bank was deliberately left as the same stale-aligned file every other
campaign uses for these ids (re-authoring it would give Qwen2.5-14B better stimuli
than Llama/Mistral/Qwen2.5-7B, which is not a fair comparison). Output:
`.../qwen2.5_14b/ecnbench_20260821T062753158194Z/` (T3/T4/T5) and
`.../qwen2.5_14b/ecnbench_20260821T120052194383Z/` (T6/C6/T8).

Scored the same day in 5 evaluator passes (primary `deepseek/deepseek-r1`, 3×
Evaluator A `deepseek/deepseek-v4-flash-0731`, Evaluator C `openai/gpt-5.6-luna-pro`)
and merged into all 5 canonical files via `merge_qwen14b_fix6.py` (dry-run first,
backups in `archive_pre_session_repairs/`). Two gotchas hit and fixed along the way:
`app/benchmarks/evaluator.py`'s hardcoded `max_tokens=65536` overflows
`deepseek/deepseek-r1`'s 64k context window (it assumes the 1M-context
`deepseek-v4-flash-0731`); worked around with a capping wrapper
(`rescore_qwen14b_fix6_primary.py`) rather than editing pipeline source. And one
`repeat1` unit (`T6_B_r1`) hung against OpenRouter for 30+ minutes with no timeout
firing (near-zero CPU use, not a retry loop) — killed and re-run alone, succeeded
immediately.

Qwen2.5-14B is now a complete 30/30-event, 90/90-unit campaign across all 5 files.

## Where the raw, unfiltered data lives (for audit trail — do not use for analysis)

- `ECN-HPC-DEPLOY/event_results_qwen2.5-14b_complete.json` and
  `results/qwen14b/ecnbench_20260727_qwen14b_complete/event_results.json` — the raw
  90-row merge as delivered from HPC, before the wrong-topic exclusion.
- `ECN-HPC-DEPLOY/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/`
  — the original (mostly-unscorable, 87/90 empty `ground_truth`) campaign directory
  plus intermediate repair attempts (`.hybrid_*`, `.bak_*`,
  `event_results_evaluatorB_openrouter.json`). `DEFAULT_MODEL_DIRS` in
  `run_openrouter_eval_official.py` used to point here; it now points to this
  directory instead.
