# Current manuscript

**ECN-BENCH: Design, Systems Engineering, and a Forensic Audit of Multi-Agent Forecasting**

- `ecn_bench_paper.tex` / `.pdf`: full technical report, including the restored design, rubric, systems discussion, event register and all 30 historical figures with explicit corrective annotations.
- `ecn_bench_paper_short.tex` / `.pdf`: separate concise audit manuscript.
- `ecn_bench_paper_conf.tex` / `.pdf`: two-column rendering of the concise manuscript; not a venue-specific submission template.
- `paper_full_technical.tex`: extended methods, engineering and historical tables.
- `paper_full_tables.tex` / `paper_full_results.json`: generated full-register tables and machine-readable offline audit.
- `paper_historical_figures.tex`: documentary figure register; historical plots are not current inferential results.
- `paper_tables.tex`: generated numerical table rows and inline estimates.
- `paper_results.json`: machine-readable current analysis.
- `fig_paper_audit.png`: current figure.
- `PAPER_DATA_MANIFEST.md`: mapping from claims to frozen sources.
- `references.bib`: shared, primary-source bibliography for the full and concise
  manuscripts.

The original August long report and conference draft are preserved in `../09_audit/`. They contain withdrawn claims and must not be cited as current results. The full restoration preserves their research scope without reinstating unsupported conclusions. The extended audit retains all 360 stored units and excludes T1 from four-model aligned aggregates because Qwen2.5-14B T1 asks a different question; the primary 20-event analysis is unaffected.

Venue-specific formatting and any future DOI deposition remain release steps,
not missing simulation experiments.

Authorship metadata was confirmed on 2026-09-08: Minh Hien NGUYEN is the primary
and corresponding author, affiliated with the Faculté des Sciences et Ingénierie,
Sorbonne Université (L2 EEA, Bi-disciplinaire, minor in Mechanics; student
no. 21618468). Hugues DIGONNET (Centrale Nantes / GeM) is acknowledged as the
academic supervisor and is not listed as a co-author. The private repository is
`MinhHixn/ECN-BENCH`, branch `main`. This corrected archive is package 1.2.3 and
is not yet tagged. The pre-correction `main` commit audited on 2026-09-10 was
`689c9f11ede54830b5fad7f0f12e8d0fca7a7e12`; `v1.2.1` points there and
`v1.2.2` to its parent. Publish 1.2.3 under a new monotonic tag and cite that
tag's full target commit.

Build instructions: `../00_docs/REPRODUCE.md`.

arXiv packaging and remaining author decisions:
[ARXIV_READINESS.md](../00_docs/ARXIV_READINESS.md).
The dedicated source ZIP is generated with `tools/prepare_arxiv.py`; do not
upload the complete GitHub or trace ZIP as the manuscript source.
