# Reproduce the revised paper offline

The current analysis requires Python 3.11+ with NumPy and Matplotlib; it was exercised with Python 3.14.2, NumPy 2.3.5 and Matplotlib 3.10.8. The exact tested dependency versions are in `05_analysis/requirements-analysis.txt`. This is a small analysis environment; the historical simulation backend is not required.

From the archive root:

```bash
python -m pip install -r 05_analysis/requirements-analysis.txt
python 05_analysis/scripts/paper_analysis.py --data-root . --output-dir 08_paper
python 05_analysis/scripts/paper_full_analysis.py --data-root . --output-dir 08_paper
python -m unittest discover -s 05_analysis/tests -v
tectonic --only-cached --keep-logs 08_paper/ecn_bench_paper.tex
tectonic --only-cached --keep-logs 08_paper/ecn_bench_paper_short.tex
tectonic --only-cached --keep-logs 08_paper/ecn_bench_paper_conf.tex
```

Installing packages may require network access. Analysis itself performs no network calls and never reads credentials. Tectonic's `--only-cached` flag requires TeX packages to have been cached previously; it cannot download missing packages. Without that flag, an initial build may need network access.

## Generated artifacts

- `paper_results.json`: all revised estimates, exclusions, bootstrap settings and hashed inputs.
- `paper_tables.tex`: numerical table rows and inline estimates consumed by the manuscript.
- `fig_paper_audit.png`: paired extraction observation and exploratory interval plot.
- `paper_full_results.json` / `paper_full_tables.tex`: full event register, all 360 stored units, 29-event question-aligned summaries and modal-confidence bins. The known Qwen2.5-14B T1 mismatch is recorded, not silently repaired.

The full manuscript also inputs `paper_full_technical.tex` and `paper_historical_figures.tex`. Historical plots come from `06_figures/` and are reproduced only in the annotated historical register; they are not regenerated current results. The short manuscript is a separate file, and `ecn_bench_paper_conf.tex` renders the short version in two columns. No venue-specific compliance is implied.

To regenerate the reference JSON in the analysis directory, substitute `--output-dir 05_analysis/outputs`. Outputs are deterministic in the tested environment; compare parsed JSON and input hashes. Bitmap/PDF byte identity can depend on rendering-library versions.

## Statistical contract

100,000 percentile bootstrap draws, generator seed 7. Events are resampled with their entire set of repeated campaigns/readings. The US-election-grouped sensitivity resamples 15 clusters for 20 events and preserves event weighting. There are no exact pooled accuracy p-values. The interval estimates condition on existing simulations and reads; they do not estimate between-simulation variance.

Four stale rereads are excluded before averaging. The main J/A pairing checks evidence, question, options and outcome metadata. The truncation comparison uses complete paired observations and retains repeated lengths/conditions within events. Missing off/on observations differ, yielding 238 complete pairs.

## Reanalysis versus rerunning

No model calls are needed to reproduce the revised analysis. Historical generation scripts can call paid endpoints or launch HPC work; they are retained as provenance and are not part of these commands.

The original evaluator endpoint cannot be replayed exactly. Its open-weight identifier does not restore the original serving environment. Qwen2.5-14B raw traces are absent for 21 original events; stored scored evidence remains available. Reanalysis is reproducible from those records, but full historical system execution is not.

The old `make_workspace.py` and historical analysis helpers are retained for prior versions. They are unnecessary for the revised paper.
