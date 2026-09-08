# Revised offline analysis

The current authority is `scripts/paper_analysis.py`, with outputs in `outputs/paper_results.json`. Dependencies are in `requirements-analysis.txt` and numerical/data-contract tests are in `tests/`.

The script consumes the existing release layout directly, validates probability records and paired evidence, excludes known stale reads, and generates tables/figure data without API calls. See `../00_docs/REPRODUCE.md`.

The predictive-signal, CoT-analysis, CoT-figure and truncation-analysis entrypoints now delegate to the revised offline analysis. Their former implementations are archived in `../09_audit/analysis_20260826/`. Other scripts and outputs are retained historical analyses: their older p-values, independence assumptions, contamination language and causal narratives are not adopted by the revised manuscript. `make_workspace.py` is a historical-layout helper and is not needed for the current command.

Current generated outputs: `paper_results.json`, `paper_tables.tex`, `fig_paper_audit.png`.

The full edition adds `scripts/paper_full_analysis.py`, producing `paper_full_results.json` and `paper_full_tables.tex`. It restores every event-level lookup row, adds the complete question register and recalculates confidence bins without outcome-conditioned binning. The known Qwen2.5-14B T1 question collision is retained and flagged; aligned aggregate tables exclude T1 across all campaigns. The expanded suite contains 12 tests.
