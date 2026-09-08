# Frozen scored campaign records

Four campaigns each contain 30 events × three recorded conditions. All source scored JSON files are retained unchanged by the September 6 revision.

`event_results.json` is the original primary-file convention, but contains substitute-evaluator recovery rows for Llama and Qwen2.5-14B. It must not be treated as a homogeneous Evaluator J pass.

The Evaluator A initial pass is named `event_results_evaluatorB_openrouter.json`; three additional reads use `event_results_evaluatorA_repeat{1,2,3}.json`. Qwen2.5-14B lacks the initial file. Evaluator C uses `event_results_evaluatorC_gptlunapro.json`. Repeated files are not new simulations.

Use `../05_analysis/scripts/paper_analysis.py` for current results. Legacy `summary.json`, per-campaign reproducibility summaries and descriptive README histories were produced before this revision and are not current inferential results. The documented four stale rereads are excluded by explicit keys. Full provenance: `../00_docs/PROVENANCE.md`.

