# Suggested arXiv form entries

Author review required. This is metadata for the full technical report, not
the differently titled concise manuscript. The abstract below is an abridgment
for arXiv's 1,920-character limit; it preserves the main estimates and caveats.
Do not paste this entire Markdown file into a form.

## Title

ECN-BENCH: Design, Systems Engineering, and a Forensic Audit of Multi-Agent Forecasting

## Authors

Minh Hien NGUYEN

## Abstract

An LLM that extracts a probability distribution from a multi-agent transcript is part of the forecasting system, not a neutral scoring function. We audit this measurement boundary in ECN-BENCH, a social-simulation testbed with four campaigns carrying 30 event identifiers each. On 132 simulated units with identical stored evidence, questions and options, near-uniform forecasts occur in 31 readings by the original extractor and one by a replacement. Repeated replacement readings also vary: the mean within-unit Brier range is 0.208-0.375 across campaigns. These findings establish sensitivity to the deployed extraction configuration, not which reading correctly represents the swarm. A source audit documents schema bypass and silent failure handling, but evaluator substitution also changes other configuration details. A proxy-model truncation/enforcement experiment does not establish the cause of the original near-uniform outputs. Forecasting comparisons remain exploratory. On 20 events resolving after the campaign models' release dates, the Brier contrast between simulation conditions is +0.112 [+0.030, +0.192] using averaged replacement readings and +0.081 [-0.003, +0.170] under another evaluator (event-cluster 95% bootstrap intervals). The latter includes zero. This subset is not protected against evaluator knowledge leakage; some injections target the wrong event and null payloads are not length-matched. An existing single-agent baseline does not establish a simulation advantage. The full report preserves the benchmark design, systems engineering, event tables and annotated historical figures while separating specifications and earlier diagnostics from validated results.

## Comments

81 pages, 31 figures. Full technical report with annotated historical figure register and retrospective reproducibility audit.

## Author-selected fields

- Category: select based on scope; cs.AI or cs.MA are candidates, not an assigned classification.
- License: author decision after rights review; see ARXIV_READINESS.md.
- Journal reference, DOI and institutional report number: leave blank unless an actual assigned identifier/publication exists.
- GitHub/data link: do not describe the currently private repository as a public archive.

The [official metadata instructions](https://info.arxiv.org/help/prep.html)
require short abstracts and expanded macros. The copy-ready fields above use
ASCII characters to avoid PDF copy/paste artifacts.
