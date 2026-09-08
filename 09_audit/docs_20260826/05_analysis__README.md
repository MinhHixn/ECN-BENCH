# 05_analysis — analyses over the campaign data

Scripts and outputs for the analyses that run over `02_campaigns/` and `03_traces/`
directly, as opposed to the four standalone experiments in `04_experiments/`.

Start with `make_workspace.py` — see `00_docs/REPRODUCE.md`.

## `make_workspace.py`

Materialises `_workspace/`, the directory layout the scripts were written against
(`completed_benches/<model>/<campaign_id>/` beside the scripts). Raw traces are
hard-linked so it costs almost no disk; anything a script might *write* is copied, so
re-running an analysis can never modify this archive. Delete `_workspace/` freely.

## `scripts/`

| Script | Produces |
|---|---|
| `make_predictive_signal.py` | `predictive_signal_analysis.json`, `figJ_predictive_signal.png` — the paper's one surviving positive result |
| `make_volume_figure.py` | `figI_volume_mechanism.png` — the degeneracy/volume mechanism |
| `make_audit_figures.py` | `fig1`, `fig2`, `fig5`, `fig7`, `fig9`, `figI`, kappa and action-density figures |
| `make_audit3_figures.py` | `figA`–`figH` — the audit figure set |
| `make_fig8_architecture_v2.py` | `fig8_architecture.png` |
| `make_architecture_diagram.py` | `fig1_architecture_code_generated.png` |

## `outputs/`

| File | What it holds |
|---|---|
| `predictive_signal_analysis.json` | **Source of truth** for Table `tab:predictive_signal`. The LaTeX table has drifted from it before; trust the JSON. |
| `evidence_depth.json` | Per-unit evidence length (`ev_len`), used by the volume analysis |
| `persona_run_health.json` | Per-run persona and action-health audit |
| `audit3_data.json` | Backing data for the `figA`–`figH` audit figures |
| `contamination_analysis.json` | Release-date stratification of the event catalogue |
| `full_analysis_results.json` | Early consolidated analysis, retained for reference |

## What `make_predictive_signal.py` establishes, and what it does not

**Established**, on the 20 contamination-clean events with four-read means:

- Directional accuracy far above chance: pooled 65.5/80 = 81.9 % against a 32.6 %
  chance baseline, exact Poisson-binomial **p = 3.7 × 10⁻²²**. Chance is `1/K` with K
  from 2 to 9, so the null is a Poisson binomial computed exactly — a coin-flip null
  would overstate this badly.
- Content sensitivity: B − C is **+0.112 Brier [+0.042, +0.182]**. This is a
  within-simulation contrast, so it never touches the shared Condition A record.

**Explicitly not established**, and the paper says so:

1. That simulation beats direct elicitation. Condition A was shared, so no within-model
   A-versus-B contrast exists. Re-running Condition A per model is the highest-value
   next experiment.
2. That the forecasts are well calibrated — Condition B mean Brier is 0.22–0.34.
3. That contamination is fully excluded. Release-date stratification rules out
   memorising the *outcome*, not the dossier carrying contemporaneous signal.

And since the CoT baseline (`04_experiments/04_…`) reproduces the directional accuracy
with a single call, **only the B − C contrast is evidence about deliberation.**

## Two conventions to keep

- **Directional accuracy credits a k-way tie at `1/k`.** That is why the pooled count is
  65.5, not an integer. Say so whenever quoting "N of 80".
- **Pooled inference clusters on events**, because events recur across models. The naive
  unclustered test is anticonservative here.

## A note on a harmless inconsistency

`figJ`'s bootstrap is labelled B = 20 000 while some tables report B = 10 000 for the
same intervals. Both labels are accurate — the figure script and the pipeline use
different replicate counts — and the two agree to three decimals.
