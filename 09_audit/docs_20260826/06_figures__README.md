# 06_figures — every figure the paper renders

All 30 PNGs referenced by `\includegraphics` in `08_paper/ecn_bench_paper.tex`. The
conference version reuses four of them (`figK`, `figL`, `figR1`, `figR2`).

## Which script regenerates which

| Figures | Regenerate with |
|---|---|
| `figJ_predictive_signal` | `make_predictive_signal.py` |
| `figM_cot_vs_swarm` | `make_cot_baseline_figure.py` |
| `figK_degeneracy_transfer` | `analyze_degeneracy_transfer.py` |
| `figL_truncation` | `analyze_truncation_grid.py` |
| `figI_volume_mechanism` | `make_volume_figure.py` |
| `figR1_evaluator_replication`, `figR2_instrument_noise` | `make_replication_figures.py` |
| `figA`–`figH` | `make_audit3_figures.py` |
| `fig1_lift_heatmap`, `fig2_cross_model_brier`, `fig5_jsd_convergence`, `fig7_directional_matrix`, `fig9_contamination_analysis` | `make_audit_figures.py` |
| `fig8_architecture` | `make_fig8_architecture_v2.py` |
| `fig1_lift_heatmap`, `fig5_jsd_convergence`, `fig7_directional_matrix`, `fig9_contamination_analysis` (4-model variants) | `generate_figures_4models.py` — note it **hardcodes its data** rather than reading the campaigns |

**Nine figures have no generator in this archive** — only the rendered PNG survives:
`fig3_taxonomy_breakdown`, `fig4_calibration_overlay`, `fig6_volatility_vs_lift`,
`fig10_bss_comparison`, `fig11_bss_by_format`, plus `cross_model_comparison`,
`compute_cost_analysis`, `n_sweep_calibration` and `r_sweep_calibration` from the HPC
parameter-sweep appendix. They were produced by pipeline code that was not preserved.
Stated here rather than left for a reader to discover.

## Two known cosmetic defects, not fixed

**1. Mixed themes.** Six figures have a near-black background (`rgb(15,17,23)`):
figures 1, 5, 6, 11, 18 and 19 as numbered in the built PDF. The other 21 are white.
This reads as inconsistent in print. Converting them properly needs the original
plotting code, which for exactly those figures is not in the archive.

**2. Cropped title bands.** Five figures carried a baked-in title inside the PNG that
had gone stale — it named a figure number that no longer matched after the paper was
restructured (`fig3` said "Figure 3" but is Figure 5, and so on). Since they have no
generator, the title band was **cropped** rather than re-rendered. The LaTeX caption
already carries the content, and no plot area was lost. Uncropped originals are at
`09_audit/figure-backups/figures_backup_pre_titlefix/`.

Four further figures had stale "Qwen-14B: HPC download pending" annotations, directly
contradicted by the sections that now score that model. Those *do* have a generator
(`generate_figures_4models.py`, which hardcodes its data), so the text was corrected and
the figures re-rendered — same numbers, corrected labels. Pre-correction versions are in
the same backup folder.

## Figure backups

`09_audit/figure-backups/` holds every intermediate figure state kept during the audit:
`figures_backup_pre_titlefix` (before title cropping), `figures_backup_dark_originals`
and `figures_light_candidate` (the theme-conversion attempt),
`figures_backup_pre_provenance_fix` and `figures_backup_pre_fig1_redraw`. They are audit
trail, not inputs to anything.
