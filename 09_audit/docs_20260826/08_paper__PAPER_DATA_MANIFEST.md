# ECN-BENCH paper — data manifest (as of 2026-08-15)

Single point of reference for submitting or reporting on `ecn_bench_paper.tex` and the
data behind it. Read this first if you're picking the project back up later.

## The paper itself

- **`ecn_bench_paper.tex`** — current draft. Structurally verified (balanced braces/
  environments, no dangling `\ref`/`\cite`/`\label`, no duplicate labels) **and now
  compiled clean**: 68 pages, 0 undefined references, 0 undefined citations, 0 overfull
  or underfull boxes. Build with `tectonic -X compile ecn_bench_paper.tex --outdir
  build_pdf` (Tectonic 0.17 installed via scoop; poppler is installed too, for
  `pdftotext`/`pdftoppm` inspection). Output PDF is `build_pdf/ecn_bench_paper.pdf`,
  copied to the repo root as `ecn_bench_paper.pdf` for the website to link.
- **`ecn_bench_paper.backup-pre-fixes.tex`** — the draft as it stood before the
  2026-08-15 correctness/compile pass described below.
- **`ecn_bench_paper.backup-pre-revision.tex`** — the draft exactly as it stood before
  this session's revision pass (Related Work added, restructured to lead with the
  central finding, anonymization leak fixed, abstract/conclusion trimmed). Keep for
  diffing; not otherwise needed.

## What changed this session, roughly in order

1. Academic review of the original draft; 5 prioritized revisions identified.
2. Revision pass: added a real Related Work section (4 verified citations), moved
   HPC-engineering/testbed-parameter-sweep material to an appendix, fixed an
   anonymization leak, trimmed the abstract and Conclusion.
3. Audited newly-recovered Qwen2.5-14B data; found 6/30 events were simulated against
   the wrong topic (stale-catalogue bug); excluded them, kept 24/30, organized into
   `completed_benches/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/`.
4. Extended the paper's single-pass "Evaluator Replication" check (previously
   Condition~A only, 3 models) to **all 3 conditions, 4 models, 4 independent
   Evaluator~A reads, 1 independent Evaluator~C read**, then restricted the headline
   cross-model comparison to the **17 events that are contamination-clean and common to
   all 4 models** — added as Section~\ref{sec:four_model_extension} /
   Table~\ref{tab:four_model_clean}.
5. This consolidation pass: saved that analysis to disk (previously only in chat/
   console output), caught and fixed 5 numeric errors that had crept into the paper
   text during manual transcription (see below), archived stale repair-attempt files,
   and wrote this manifest.

## Where the numbers in Section 8 (Evaluator Replication) come from

- **`reproducibility_analysis_master.json`** (repo root) — the single source of truth.
  Rollup of all 4 models' `reproducibility_analysis.json` (same content, saved
  alongside each model's `event_results_*.json` files). Regenerate any time with
  `python ECN-HPC-DEPLOY/build_reproducibility_analysis.py` (no arguments; paths are
  relative to the repo root, safe to run from anywhere).
- **`evaluator_replication_expanded_analysis.json`** (repo root) — earlier, per-unit-
  level dump (probabilities, individual read lists) from before the contamination-
  clean restriction existed. Superseded by `reproducibility_analysis_master.json` for
  anything reported in the paper; kept because it has finer per-unit detail the rollup
  doesn't.
- Each model's own `completed_benches/<model>/.../README.md` explains that model's
  specific files and any known gaps.

**Numeric errors found and fixed during this consolidation** (all were hand-transcription
slips from console output into LaTeX, not computation bugs, except the last):
1. Qwen2.5-14B susceptibility: `+0.155` → `+0.157`.
2. Pooled Evaluator-C Condition-C read count: `246` → `114` (`30+30+30+24`).
3. Qwen2.5-14B instrument spread: `0.194` → `0.191`.
4. Mistral-7B's "full, uncontrolled" lift was mislabeled with the 24-common-event
   figure (`-0.197`) instead of the true full-30-event figure: → `-0.224`.
5. **Real bug, not a transcription slip**: 3 permanently-failed OpenRouter reads
   (Qwen2.5-7B's `T3_C_r1`/`C9_A_r1`/`C13_C_r1` in `repeat3.json`, Qwen2.5-14B's
   `T1_C_r1` in `repeat2.json`) left a stale, never-overwritten copy of an earlier
   pass's value in place rather than being absent. The first build of the analysis
   counted these as genuine extra reads, artificially deflating spread and skewing the
   robust mean for the affected units. Fixed by explicitly excluding those exact
   (file, unit) pairs — see `KNOWN_GAPS` in the analysis script. This changed
   Qwen2.5-7B's Table~\ref{tab:four_model_clean} row (lift `+0.005→+0.004`,
   susceptibility `+0.186→+0.194`) and the pooled cross-evaluator correlation figures
   for Qwen2.5-7B and Qwen2.5-14B slightly. All of the above are already corrected in
   the current `ecn_bench_paper.tex`.

## Per-model data status

| Model | Events | Evaluator A reads/unit | Evaluator C reads/unit | Known permanent gaps |
|---|---|---|---|---|
| Llama-3.1-8B | 30/30 | 4 | 1 | none |
| Mistral-7B | 30/30 | 4 | 1 | none |
| Qwen2.5-7B | 30/30 | 4 (3 for 3 units) | 1 | T3_C_r1, C9_A_r1, C13_C_r1 unrecoverable in repeat3 |
| Qwen2.5-14B | 24/30 (6 excluded, wrong-topic bug) | 3 (2 for 1 unit) | 1 | T1_C_r1 unrecoverable in repeat2; 6 events need re-simulation to reach 30/30 |

Directory index:
- `completed_benches/llama-3.1-8b-awq/ecnbench_20260714T173650169846Z/`
- `completed_benches/mistral-7b-awq/ecnbench_20260715T080203247382Z/`
- `completed_benches/qwen2.5_7b/ecnbench_20260717T154127454597Z/`
- `completed_benches/qwen2.5-14b-awq/ecnbench_20260727_qwen14b_complete/` (canonical;
  do not use the older `ECN-HPC-DEPLOY/ecnbench_workspace/simulation_logs/qwen2.5-14b-awq/...`
  path or the raw merge duplicates under `ECN-HPC-DEPLOY/` and `results/qwen14b/` —
  those are pre-cleanup audit trail only, documented in that directory's own README)

Each of the 4 directories above now has its own `README.md` listing every
`event_results_*.json` file, what evaluator/pass it is, and any gaps specific to that
model. `archive_pre_session_repairs/` subfolders (Llama, Mistral, Qwen2.5-7B only) hold
superseded repair attempts from before this session — audit trail, not used by any
current analysis or figure.

## 2026-08-15 correctness and compile pass

Verified every headline number against the released artifacts, not against the previous
manifest. Table `tab:four_model_clean`, the susceptibility margins, the contamination
and cutoff strata, the persona audit and the outage counts all reproduce exactly. The
`5,959 / 6,161` Llama social-action figures were re-derived by direct SQL over the 120
campaign `.db` files and are correct as printed — `persona_run_health.json`'s `social`
field is larger (6,005 / 6,207) only because it counts `search_posts`, `repost`, `mute`
and friends, which Table `tab:action_30event_only`'s five columns do not.

Corrections made:

1. **Section 7.2 and the abstract described all-unit means as non-flat means.** The
   figures `0.514 / 0.485 / 0.538` are means over all 30 units *including* the flat
   ones, which carry a modal probability of `1/K` by construction — so the sentence
   excluded the flat units in words while including them in the arithmetic. Recomputed:
   non-flat Condition A is `0.664` and non-flat Condition B is `0.563 / 0.536 / 0.538`
   (Condition C: `0.538 / 0.475 / 0.488`). The sharpness claim survives, weaker. Both
   rows are now reported so the two mechanisms are visibly separate.
2. `18,381` characters was a specific unit (`S2_B_r1`), not the maximum → `20,329`
   (`S6_B_r1`), in both places it appeared.
3. Condition-A instrument spread max stated as `0.72` in one place and `0.715` in four
   others → `0.715` throughout.
4. Six figures and four tables had labels but were never cited in the running text
   (Figures 2, 3, 5, 6, 10, 12; Tables 9, 22, 23, 24). All now referenced. Added the
   missing `\label{sec:taxonomy}` this required.
5. `\bibitem{mmlu}` was never cited → now cited in Related Work alongside HLE.
6. Added a **Data Availability** section. The thanks footnote claimed both scored passes
   are "released separately" with no URL anywhere. The new section enumerates the
   released files and, because the paper is anonymous, routes reviewers through the
   venue with the public link deferred to camera-ready — **insert the real URL there
   before the camera-ready deadline**.
7. Compile fixes found only by building: a table row beginning `[0.75--1.00]` was parsed
   as an optional argument to `\\` ("Illegal unit of measure") — braced, along with its
   three sibling rows; wide tables reduced via font/`\tabcolsep`/`\resizebox`; `\texttt`
   hyphenation enabled and `\emergencystretch` set. 15 overfull boxes → 0.

## New analysis added 2026-08-15: the degeneracy mechanism

Section `sec:volume_mechanism` (§IX-E in the built PDF) and Figure `fig:volume_mechanism`
(`figI_volume_mechanism.png`, regenerate with `python make_volume_figure.py`) close the
question Section 7.1 previously left open. Derived by joining `evidence_depth.json`'s
per-unit `ev_len` to the flat-unit flags of all six scored passes:

- **Within-campaign association.** Flat units carry more evidence: median 19,016 vs
  3,009 chars for Llama (Mann-Whitney U=626, p=6.5e-5), 13,906 vs 12,074 for Mistral
  (U=683, p=3.1e-6). Qwen2.5-7B has no flat units, so no contrast.
- **Llama is confounded and the paper says so.** Its 12 high-volume units are exactly
  its 6 pre-outage events — 12/12 flat, against 6/48 for the outage units. Volume there
  is inseparable from whether deliberation happened at all.
- **Mistral is the clean test** (no outage, 0/60 units with ≤1 speaker): flat rate by
  `ev_len` tercile is 1/20 → 5/20 → 13/20 (5% → 25% → 65%) over a 10,192–15,557 char
  range.
- **Volume is not sufficient.** Same transcripts, different instrument: Llama's 12
  high-volume units go 12/12 flat (Evaluator J) → 0, 1, 2, 0 of 12 (four Evaluator A
  reads) → 0/12 (Evaluator C). Mistral's 20 longest go 13/20 → 1, 1, 0, 0 → 0.
- **Asymmetry worth keeping.** Under Evaluator A the residual flats *relocate* to
  Llama's low-volume outage arm (10, 8, 12, 12 of 48), whose evidence is a
  connection-error dump — where a uniform posterior is defensible. The two instruments
  fail in opposite regimes.

Conclusion as written: degeneracy is an *interaction* between a long input and one
schema-disabled instrument; volume is the trigger, the evaluator is the locus. The
remaining ambiguity — raw length versus speaker/claim count co-varying with it — is
stated explicitly and left to the truncation experiment in future-work item (iii).

Reproduce the numbers with the scratch scripts described in the session log, or directly:
they read only `evidence_depth.json` and the `event_results*.json` files listed above.

## New analysis added 2026-08-15: the paper's one positive result

Section `sec:predictive_signal` (§IX-F), Table `tab:predictive_signal` and Figure
`fig:predictive_signal` (`figJ_predictive_signal.png`). Regenerate everything with
`python make_predictive_signal.py`, which also writes `predictive_signal_analysis.json`.

Before this pass the paper had **no** affirmative conclusion about predictive ability —
susceptibility appeared only as item 3 of nine "context, not validated claims" in the
Conclusion, using the weak single-pass numbers. It now states one, bounded precisely.

**Established** (17 contamination-clean events, four-read means, same basis as
`tab:four_model_clean`):

- Directional accuracy in Condition B is far above chance. Chance is `1/K` per event and
  K ranges 2–9, so the null is a **Poisson binomial**, computed exactly — not a coin
  flip, which would have overstated significance. Pooled 60/68 = 88.2% vs 34.6% chance,
  p = 2.9e-22; every individual model p < 3e-5. 11/17 events called correctly by all
  four models, **0** events called wrongly by all four.
- Content sensitivity: B − C pooled is +0.178 Brier [+0.109, +0.246] and +19.9 points of
  directional accuracy [+8.8, +30.9]. Three of four per-model Brier CIs exclude zero
  (Mistral is the exception at +0.094 [−0.088, +0.275]). This is a within-simulation
  contrast, so it never touches the shared Condition A record.

**Explicitly not established, and stated as such in the paper:**

1. That simulation beats direct elicitation. B vs A directional accuracy is +0.176,
   0.000, 0.000, +0.118 — none close to significant. Condition A was shared, so no
   within-model contrast exists. Re-running Condition A per model is the highest-value
   next experiment; it would convert a demonstrated *signal* into a demonstrated
   *benefit*.
2. That the forecasts are well calibrated. Condition B mean Brier is 0.22–0.34.
3. That contamination is fully excluded. Release-date stratification rules out
   memorising the outcome, not the dossier carrying contemporaneous signal.

**Ordering reversal worth knowing:** under the old single-pass 30-event reading, Mistral
was the *only* model whose susceptibility interval excluded zero. Under four-read means
on clean events it is the *only* one that does not. Trust the pooled figure over any
single-model row.

## 2026-08-15 layout and presentation pass

Rendered all 68 pages and audited them for float drift, whitespace, stranded headings
and figure/caption defects.

**Float placement — the big one.** 51 of 56 floats carried `[h]`, the weakest possible
specifier: it gives LaTeX exactly one option, and when the float does not fit there it
goes into the deferred queue and drifts. The log showed 37 `` `h' float specifier
changed to `ht' `` warnings, and the appendix tables had piled up on pages 65–67, six to
nineteen pages after the text that cites them. Fixed by moving every float to
`[!htbp]` / `[!tbp]` and relaxing the float fractions in the preamble
(`\topfraction` 0.90, `\bottomfraction` 0.75, `\textfraction` 0.08,
`\floatpagefraction` 0.70, `topnumber` 3 / `bottomnumber` 2 / `totalnumber` 5).
Distant floats went from 24 to 2, and those 2 are deliberate forward references
(Figure 23 from the superseded Figure 13's caption; Table XVIII from the
interaction-density discussion). Result: **0 overfull boxes, 0 pages with a stray gap.**

**Figure defects — baked-in titles.** Ten figures carried their own title inside the
PNG, which duplicated the LaTeX caption and, worse, had gone stale:

- *Wrong figure numbers* (5): `fig3_taxonomy_breakdown` said "Figure 3" but is Fig. 5;
  `fig4_calibration_overlay` said "Figure 4" but is Fig. 6; `fig6_volatility_vs_lift`
  said "Figure 6" but is Fig. 11; `fig10_bss_comparison` said "Figure 10" but is Fig. 18;
  `fig11_bss_by_format` said "Figure 11" but is Fig. 19. `fig8_architecture` carried a
  caption bar at its foot reading "Figure 8" but is Fig. 1.
- *Stale Qwen2.5-14B annotations* (4), directly contradicted by Sections IX-E/IX-F which
  now score that model: `fig1_lift_heatmap` "HPC download pending";
  `fig5_jsd_convergence` "local download pending" / "Qwen-14B* excluded" / "pending";
  `fig7_directional_matrix` "not available locally"; `fig9_contamination_analysis`
  "Qwen-14B*: pending".

The four stale ones are produced by `scratch/generate_figures_4models.py`, which
hardcodes all its data, so the titles were corrected there and the figures regenerated —
same numbers, corrected text. The five wrong-numbered ones have no generator in the repo,
so the title band was cropped instead (the LaTeX caption already carries the content;
originals are in `figures_backup_pre_titlefix/`). Verified that no plot content was lost.

**Also fixed:** the errata table's three narrow `p{}` columns were justified, producing
~40 underfull-hbox warnings and visibly ragged spacing; switched to
`>{\raggedright\arraybackslash}p{...}`. Underfull warnings 40 → 6.

**Known, not fixed — mixed figure themes.** Six of the 27 figures have a near-black
background (`rgb(15,17,23)`): Figs. 1, 5, 6, 11, 18, 19. The other 21 are white. This
reads as inconsistent in print and is ink-expensive. Converting them properly needs the
original plotting code, which is not in the repo — only the rendered PNGs are.

Not changed, noted for the record: Figure 4 reports its bootstrap as `B=20,000` while
Table VIII reports `B=10,000` for the same susceptibility CIs. Both labels are accurate —
the figure is regenerated by `make_audit_figures.py` (`boot_ci(n=20000)`) and the table
comes from the pipeline — and the two agree to three decimals. Harmonise only if a
reviewer asks.

## New analysis added 2026-08-17: the single-agent CoT baseline

Section `sec:cot_baseline` (subsection of `sec:predictive_signal`), Table
`tab:cot_baseline`, Figure `fig:cot_baseline` (`figM_cot_vs_swarm.png`). In the
conference paper: `sec:cot_baseline`, Table `tab:cot`.

| file | what it is |
|---|---|
| `run_single_agent_cot_baseline.py` | generator — 17 clean events × 4 OpenRouter models × 3 replicates = 204 calls |
| `single_agent_cot_baseline_results.json` | the 204 raw runs; 204/204 `status: success` |
| `analyze_cot_baseline.py` | **the only authoritative analysis**; writes `cot_baseline_analysis.json` |
| `make_cot_baseline_figure.py` | writes `figM_cot_vs_swarm.png` |

Regenerate with `python analyze_cot_baseline.py && python make_cot_baseline_figure.py`.
The swarm side reuses `make_predictive_signal.py`'s loader verbatim (four-read means over
the available Evaluator A passes), so the Condition B column of `tab:cot_baseline` matches
`tab:predictive_signal` by construction.

**Headline:** non-superiority. On the two identity-matched arms one CoT call has the lower
Brier (0.352 vs 0.549 Llama; 0.285 vs 0.330 Qwen2.5-7B); pooled matched ΔBrier =
−0.121 [−0.274, +0.024], clustered p = 0.156, d_z = 0.37, achieved power 30%, and 59
events would be needed for 80%. Pooled directional accuracy 0.856 (CoT) vs 0.831 (swarm),
so the accuracy half of the paper's surviving claim is reproduced with no deliberation;
the B−C content-sensitivity contrast is unaffected and remains the simulation-specific part.

**Three traps, all of which the first pass at this analysis fell into simultaneously and
which together produce a spurious p = 0.045 — do not reintroduce them:**

1. **Only 2 of the 4 arms are identity-matched.** `mistralai/ministral-8b-2512` ≠
   Mistral-7B-Instruct-v0.1 and `qwen/qwen3-14b` ≠ Qwen2.5-14B. The four-arm pool is a
   cross-model comparison and is reported separately, marked with `*`.
2. **Do not ensemble the 3 CoT replicates into one probability vector.** That is a 3×-cost
   arm; the swarm's four reads re-read *one* simulation. Primary = mean of the
   per-replicate scores (`single`); `ens3` is reported only as an upper bound.
   Note replicate 1 is temperature 0 and replicates 2–3 are temperature 0.7, so the three
   are not homogeneous draws — hence also the `t0` variant.
3. **Events recur across arms.** Pooled inference is a cluster bootstrap over events plus a
   cluster-robust t on per-event means (df = 16). The naive df = 67 test gives p = 0.115
   where the clustered one gives 0.267.

Superseded files moved to `superseded/`: `figK_cot_vs_swarm.png` (also collided with
`figK_degeneracy_transfer.png`), `paired_cot_swarm_detailed_stats.json`, and
`single_agent_cot_analysis_summary.json` (per-replicate aggregation, and its `n_units: 52`
is wrong — the design has 68 unit-pairs). None of their numbers should be quoted.

## 2026-08-17 FINAL PASS — `ecn_bench_paper.tex` is the single deliverable

Frozen for the 2026-08-18 report. `ecn_bench_paper.pdf`: **83 pages, 0 errors, 0 undefined
refs/cites, 0 overfull boxes**, 2 long-standing cosmetic underfull hboxes. Rebuild with
`tectonic -X compile ecn_bench_paper.tex`.

What this pass changed beyond adding `sec:cot_baseline`:

- `\thanks` date 2026-08-14 → **2026-08-17**, and it now names the two analyses that
  postdate the campaigns and ran off-cluster (evaluator/truncation, and the CoT baseline).
- **Data Availability** now releases the three post-campaign experiments with generator +
  analysis + figure script each; previously it listed only the campaign records, while the
  paper already rested claims on the truncation and transfer runs. Every filename named
  there was verified present on disk.
- **Errata bookkeeping**: 24 → **25** claims; the "Downgraded or restricted" class 2 → 3.
  New row records that the paper's surviving positive result is halved — a single CoT call
  reproduces the above-chance directional accuracy, so only the B−C contrast is evidence
  about deliberation.
- **Future work item (xiv)** added: the CoT baseline is *partly* done. Cross-references
  that its 59-event power requirement is weaker than item (x)'s E ≥ 92 (different effect).

**`ecn_bench_paper_conf.tex` is NOT part of this deliverable.** It is left in a consistent,
honest state at 8 pages with `sec:cot_baseline` included. If a 7-page limit ever applies,
`scratch/conf_variants/_conf_honest.tex` is the tested trim (section removed, limitation
rewritten to say the experiment was run and points at the tech report) and compiles to
exactly 7 pages. Do **not** restore the old "No single-agent baseline" wording — the
experiment has been run and that sentence is now false.

## 2026-08-21: Qwen2.5-14B recovered to 30/30; four-model comparison grows 17→20 events

Resolves "Still open" item 2 below. The 6 excluded events (T3, T4, T5, T6, C6, T8)
were re-simulated (300 agents, 60 rounds, all 3 conditions, split across two SLURM
jobs to fit the cluster's 2-GPU-per-user QOS) and rescored under all 5 evaluator
passes. A first re-simulation attempt (2026-08-20) reproduced the identical
stale-catalogue bug that caused the original exclusion — caught by diffing simulated
questions against the root catalogue before scoring — and had to be redone pointing
at absolute paths under `ecnbench_workspace/fix7_rootcat/data/`. Full account,
including two evaluator-side bugs hit and fixed (a hardcoded `max_tokens=65536`
overflowing `deepseek/deepseek-r1`'s 64k context; one unit hung 30+ min against
OpenRouter with no timeout), is in the campaign's own README.

**Ripple effects, all applied:**
- `event_results.json` + 4 evaluator files: 72→90 rows each, merged via
  `merge_qwen14b_fix6.py` (backups in `archive_pre_session_repairs/`).
- `summary.json` regenerated (90/90, 0 failures).
- `build_reproducibility_analysis.py`: `CLEAN_17_COMMON` (a 17-event subtraction that
  existed only because Qwen2.5-14B was missing T6/C6/T8) renamed and restored to
  `CLEAN_20_COMMON` = the full globally-clean set. Re-run; `reproducibility_analysis.json`
  (all 4 models) and `reproducibility_analysis_master.json` regenerated. This changed
  cross-evaluator-agreement and instrument-spread numbers for **all four models**, not
  only Qwen2.5-14B — those figures had drifted from a stale prior run (e.g. Llama's
  pooled evaluator-agreement $r$: paper said $0.669$, regenerated value is $0.696$);
  the regenerated master file is authoritative.
- `make_predictive_signal.py`: `CLEAN17`→`CLEAN20` (same event set). Pooled headline:
  was 56.5/68 = 83.1% dir-acc, $p=9.8\times10^{-19}$, ΔBrier $+0.125$ $[+0.053,+0.195]$;
  now 65.5/80 = 81.9%, $p=3.7\times10^{-22}$, ΔBrier $+0.112$ $[+0.042,+0.182]$.
- `run_single_agent_cot_baseline.py` + `analyze_cot_baseline.py`: same rename, and the
  generator was re-run (240 calls, was 204) since the CoT baseline shares the swarm's
  clean-event set — otherwise the paper would compare a 20-event swarm figure against
  a stale 17-event CoT figure. (Also fixed an unrelated pre-existing path bug:
  `ROOT = os.path.join(HERE, "..")` pointed one directory too high; the script lives
  at the repo root, not a subdirectory.)
- `ecn_bench_paper.tex`: Table~\ref{tab:four_model_clean}, Table~\ref{tab:predictive_signal},
  Table~\ref{tab:cot_baseline}, Appendix~\ref{sec:fourth_model_status}, future-work
  item (xi), Data Availability, the errata table, and every inline citation of "17
  events" / "68 units" / "204 calls" / the old pooled numbers updated throughout,
  including the CoT-baseline section (\S\ref{sec:cot_baseline}) once
  `run_single_agent_cot_baseline.py` was re-run to 240 calls (see hang note below)
  and `analyze_cot_baseline.py` regenerated `cot_baseline_analysis.json`.
  **Headline shift worth flagging**: on the 20-event set the single CoT call now
  *matches or slightly exceeds* the swarm on pooled directional accuracy (0.834 vs
  0.819, was 0.856 vs 0.831 -- both used to read as "matches", the new numbers still
  do but the direction flipped by less than a point) and its per-arm point estimate
  favours the single call on all 4 arms rather than 3 of 4 (Qwen3-14B's cross-model
  arm flipped sign). Two of six pooled ensemble configurations now exclude zero in
  the CoT-favouring direction (was zero of six) -- still not the primary `single`
  estimate, which remains non-significant on both scopes (clustered p=0.109 matched,
  p=0.083 all-four). Non-superiority conclusion is unchanged but strengthened.
- `run_single_agent_cot_baseline.py` **hit the same class of hang** as the HPC
  OpenRouter scoring: the 240-task run stalled at 220/240 for 15+ minutes with the
  python process near-idle (urllib's `timeout=60` did not effectively bound the
  hang). Killed and retried just the 20 missing `(model, event, repeat)` combos
  (mostly `qwen/qwen3-14b`, a slower reasoning model) with `scratch/retry_cot_missing.py`
  (lower concurrency, 45s timeout, 3 attempts) -- succeeded in one pass, appended into
  the existing results file. Also fixed a pre-existing, unrelated path bug in the
  original script (`ROOT = os.path.join(HERE, "..")` pointed one directory above the
  repo root; the script lives at the repo root, not a subdirectory) that had silently
  been masked before by whatever cwd it was originally run from.
- `ecn_bench_paper.tex` **self-correction found and fixed during this pass**: my
  first edit to Appendix~\ref{sec:fourth_model_status} incorrectly stated the
  2026-07-27 action-density SQL scan (Table~\ref{tab:action_density_30event}, 2,407
  actions / 180 DBs) covered only 24 of Qwen2.5-14B's 30 events. The table's own
  footnote says otherwise ("180 DBs = exactly one full 30-event campaign") -- the
  scan already covered all 30, including the 6 that were, at scan time, simulated
  under the *wrong* topic. Corrected to say the counts include real wrong-topic
  dossier actions for those 6 DBs, not that they're missing.
- PDF rebuilt with Tectonic: **85 pages** (was 83), 0 errors, 0 undefined refs/cites,
  same 2 pre-existing cosmetic underfull hboxes and no new ones. Copied to
  `ecn_bench_paper.pdf` at the repo root.

## 2026-08-26: the replication archive, and Qwen2.5-14B's traces off the cluster

`ECNBENCH-RELEASE/` at the repo root is the publish-ready replication package: **2,454
files, 2.4 GB**, numbered `00_docs` ... `09_audit` in reading order, each directory with
its own README. Root carries `README.md`, `MANIFEST.md`, `CITATION.cff`, `LICENSE.txt`
and `checksums.sha256` (all 2,454 verified).

**Files under `03_traces/` are NTFS hard links** into `completed_benches/`, so the tree
costs almost no extra disk — which matters, C: has ~7 GB free. Zip/tar/rsync materialise
real content, so uploading is unaffected. But never point a script that *writes* at
them: an early version of the workspace builder linked everything, and one analysis run
silently rewrote five released files through the shared inode. (Content was identical,
so nothing was lost — the hazard is what matters.) `05_analysis/make_workspace.py` now
hard-links only the read-only traces and **copies** anything a script might overwrite.

### Pulled off Nautilus (first transfer ever for this data)

| What | Where it landed |
|---|---|
| Qwen2.5-14B corrected re-simulation 2026-08-21, 18 units / 189 MB | `03_traces/qwen2.5-14b-awq/recovered-2026-08-21/` |
| C15 fragment, 3 units — all that survives of the original 2026-07-27 campaign | `.../original-2026-07-27_C15-fragment/` |
| `fix7_rootcat` recovery inputs, SLURM logs, cluster-side evaluator outputs, stale catalogue, HPC pipeline code, SLURM scripts, `ecnbench_mcq_v1.yaml` | `07_pipeline/`, `09_audit/` |
| Invalid 2026-08-20 re-simulation — metadata only (~8 MB, no `.db`) | `09_audit/qwen2.5-14b_invalid-resimulation_2026-08-20/` |

Tar on the cluster first, then SFTP: 372 MB of SQLite compressed to **16 MB**.

**The other 21 events' Qwen2.5-14B transcripts are gone permanently** — removed by the
scratch retention policy. Verified by direct search: only C15 and a C1 pilot survive
under `simulation_logs/qwen2.5_14b/`. A separate June 2026 `qwen-14b-awq` campaign on
the cluster covers all 30 events but is an *earlier, different* run — not the released
data. Scored records are unaffected.

### Reproduction is verified, not asserted

`python 05_analysis/make_workspace.py`, then the five analyses, regenerate output
**byte-identical** to the released files (ignoring embedded timestamps):
`reproducibility_analysis_master`, `predictive_signal_analysis`, `cot_baseline_analysis`,
`degeneracy_transfer_summary`, `truncation_results`. `analyze_truncation_grid.py` needs
`app.benchmarks.scoring`, so the MiroFish backend package ships at `07_pipeline/backend/`
and the workspace builder places it where that import resolves.

Nine paper figures have **no generator anywhere** in the repo — rendered PNG only:
`fig3`, `fig4`, `fig6`, `fig10`, `fig11`, `cross_model_comparison`,
`compute_cost_analysis`, `n_sweep_calibration`, `r_sweep_calibration`.

### Paper edits applied this session

Backups: `ecn_bench_paper.tex.backup-pre-data-availability`, same for `_conf`.

- **Preamble**: added `\ifecnanonymous` / `\ecnarchivedoi` / `\ecnarchiveurl` /
  `\ecnarchive`. Set `\ecnanonymousfalse` and fill the DOI for camera-ready; the Data
  Availability section then resolves the real link by itself.
- **Data Availability**: rewritten. Now describes the archive's layout and its three
  reference documents, states that reproduction was verified end to end, adds a
  paragraph on the benchmark/pipeline/audit-trail release, and wraps the anonymity
  sentence in the conditional.
- **The claim that is now false was corrected in three places.** The paper said
  Qwen2.5-14B's artifacts "were never transferred off the cluster, for either its
  original 24 scorable events or the six recovered 2026-08-21". The second half is no
  longer true. Fixed in Data Availability, in `sec:fourth_model_status`'s "What remains
  a gap", and in future-work item (xi).
- Rebuilt with Tectonic: **87 pages, 0 errors, 0 undefined refs/cites, 0 overfull**,
  same 2 pre-existing cosmetic underfull hboxes. Copied to `ecn_bench_paper.pdf`.

### `ecn_bench_paper_conf.tex` synchronised 17 -> 20 events

The conference version had been left at 2026-08-17, before the Qwen2.5-14B recovery, and
still carried the superseded 17-event statistics. Every value was re-sourced from the
regenerated JSONs (`predictive_signal_analysis.json`, `cot_baseline_analysis.json`) and
cross-checked against `tab:predictive_signal` in the report, which was already correct.

Changed: abstract, contribution bullet, `tab:signal` (all 5 rows + caption), the
"far above chance" paragraph, the content-sensitivity paragraph, `tab:cot` (all 6 rows +
caption), the non-superiority paragraph, the three-traps paragraph, and the
single-agent limitation.

| Was | Now |
|---|---|
| 17 events / 68 pairs | 20 events / 80 pairs |
| 56.5/68 = 83.1% | 65.5/80 = 81.9% |
| chance 34.6% | 32.6% |
| p = 9.8e-19 | 3.7e-22 |
| ΔBrier +0.125 [+0.053, +0.195] | +0.112 [+0.042, +0.182] |
| Δdir-acc +0.184 [+0.066, +0.309] | +0.194 [+0.075, +0.313] |
| "Nine of the seventeen" called right by all four | Ten of the twenty (none wrong by all four, unchanged) |
| CoT pooled 0.856 vs 0.831 | 0.834 vs 0.819 |
| 204 calls, df = 16 / 67 | 240 calls, df = 19 / 79 |
| d_z 0.37, power 30%, 59 events for 80% | d_z 0.39, power 37%, 55 events |

**Two claims changed in substance and were rewritten, not renumbered:**

1. "On both matched arms one call has the lower Brier **and the higher directional
   accuracy**" is no longer true on 20 events. Brier still favours the single call on
   both (0.364 vs 0.545; 0.318 vs 0.348), but accuracy splits — Llama 0.778 vs 0.675
   favours CoT, Qwen2.5-7B 0.790 vs 0.850 favours the swarm.
2. "No clustered $p$ falls below 0.069" is now false — the `ens3` variant reaches 0.034
   (matched) and 0.032 (four-arm). The primary `single` estimates stay non-significant
   (0.109 / 0.083). The text now says this and marks `ens3` as a 3x-cost upper bound.

Per-arm p-values moved a lot on the larger event set (Ministral 0.391 -> 0.115,
Qwen3-14B 0.405 -> 0.881); these are genuine recomputations, not transcription fixes.

Rebuilt: **8 pages, 0 errors, 0 undefined refs/cites, 0 overfull boxes.**

### 2026-08-26 typography pass — a silent font bug, and bold headings

**The bug: no bold, italic or small caps was rendering anywhere in either PDF.**
Both papers built with IEEEtran under the default OT1 Computer Modern setup. Tectonic
runs XeTeX, which in that configuration silently falls back to the regular face for
every `\textbf`, `\textit` and `\scshape` request. The documents compiled clean --- 0
errors, 0 overfull --- and looked plausible, so the loss was invisible unless you
compared against the source.

What was actually lost, across 87 pages:

- every `\textbf{...}` run-in lead, which is this paper's primary emphasis device
- every `\textit`/`\emph`
- IEEEtran's own `Abstract` and `Index Terms` labels, its small-caps table captions,
  its small-caps section headings and italic subsection headings
- **table content the captions explicitly promise** --- e.g.
  `tab:per_event_llama_8b` says "Bold B-score indicates With-Sim $<$ No-Sim", and not
  one of those cells was bold in the built PDF

**Fix:** `\usepackage[T1]{fontenc}` + `\usepackage{lmodern}` in both preambles,
commented as required. Verified by probe: `\textbf`, `\textit`, `\textsc` and `\texttt`
all render correctly afterwards.

**Bold headings (the request that surfaced this).** IEEEtran ships no bold at any
heading level. Both preambles now redefine the four levels with IEEEtran's own spacing,
numbering and run-in parameters copied verbatim, changing only the font:

| level | before | after |
|---|---|---|
| `\section` | small caps, centred | **bold**, centred |
| `\subsection` | italic | **bold** |
| `\subsubsection` | italic, run-in | ***bold italic***, run-in |
| `\paragraph` | italic, run-in | italic, run-in (unchanged; the paper uses none) |

`\title` is now `\bfseries` in both papers.

Section is deliberately **not** `\bfseries\scshape`: Latin Modern has no bold small-caps
shape (`T1/lmr/bx/sc` is undefined), so that pairing silently drops one attribute.

**Fallout, all resolved.** Real bold and italic are wider than the regular glyphs that
had been substituted, so line breaking changed throughout.

- Report: overfull 0 -> 4 -> **0**. Three per-event tables tightened to
  `\tabcolsep 4pt`; `tab:outage` wrapped in `\resizebox`.
- Report: underfull 2 -> 16 -> **9**. `tab:benchmark_checklist` and the errata table's
  narrow `p{}` columns switched to `>{\raggedright\arraybackslash}p{...}`. The residual
  9 are long unbreakable `\texttt{}` strings; cosmetic.
- Conference: overfull 0 -> 1 -> **0** (`tab:signal` to `\tabcolsep 2pt`). Still 8 pages.
- Page counts unchanged: **87** and **8**. 0 undefined references or citations in both.

Six `LaTeX Font Warning: Font shape ... undefined` lines remain and are benign
substitutions, not errors: `TU/ptm/*` (IEEEtran asking for Times in the Unicode
encoding, pre-existing) and `T1/lmr/bx/sc` / `T1/lmr/m/scit` (bold and italic *inside*
IEEEtran's small-caps table captions, which Latin Modern resolves to `bx/n` and
`m/scsl`).

Also corrected: the `\thanks` date, August 17 -> **August 26, 2026**.

**Flagged, not changed:** `ecn_bench_paper_conf.tex` carries the author's real name,
affiliation and email on page 1, while `ecn_bench_paper.tex` says "Anonymous Authors".
If both go to the same anonymous review, the conference version de-anonymises the
submission. Decide deliberately before sending either.

### 2026-08-26 Brier-scale audit — one false empirical claim, one missing convention

Prompted by the observation that the multi-category Brier score is bounded in $[0,2]$,
not $[0,1]$. **The report's definition was already correct** (\S`sec:grading`:
$BS = \sum_k (f_k - o_k)^2$, "bounded in $[0,2]$", with an explicit note to halve when
comparing against $[0,1]$-normalised literature), and `scoring.py` matches it --- it
sums the squared error over every label, so the released numbers are genuinely on
$[0,2]$. Verified empirically over **5,890 scored rows** across the whole archive.

Two defects found around that correct definition:

**1. A false empirical claim, now corrected.** The paper asserted "the observed maximum
is exactly $2.0$". Across the four campaigns' six evaluator passes (2,070 scores) the
maximum is **1.883** (Mistral-7B `C12_C_r1`, Evaluator A read 3). A value of exactly
2.0 does occur --- but only **six times, and only in the truncation grid**, which
postdates the campaigns and is not what that sentence was about. Nothing anywhere in
the release exceeds 2.0, so the bound itself holds.

**2. A stale count, now corrected.** "21 of the 270 reported unit scores exceed 1.0" was
computed before the Llama repair and before Qwen2.5-14B became a fourth campaign. The
current figure on the primary pass is **34 of 360** (the original three campaigns alone
are now 29 of 270, not 21).

The sentence now reads: 34 of 360 exceed 1.0; the maximum across all six passes is
1.883, named by unit; 2.0 is attained exactly six times, only in the truncation grid;
nothing exceeds 2.0.

**3. The conference version never stated the scale at all** --- no formula, no range,
while reporting Brier values throughout (0.112, 0.545, 0.364, ...). A reader defaulting
to the binary $[0,1]$ convention would misread every effect size by a factor of two.
Added, at the point where the uniform loss $1 - 1/K$ is first used: the formula, the
$[0,2]$ bound, the instruction to halve for comparison, and the note that the $1 - 1/K$
reference is consistent with the same convention.

Both papers rebuilt: **87 and 8 pages, 0 errors, 0 overfull, 0 undefined references.**

Checked and found already consistent: `BS_{random} = 1 - 1/K` is indeed the expected
score of a uniform forecast under the unnormalised convention (algebraically
$(1-1/K)^2 + (K-1)/K^2 = 1 - 1/K$), so the reported skill scores are internally
consistent; no figure axis or table caption asserts a $[0,1]$ range.

## Still open (documented in the paper, not blocking)

1. **Insert the real artifact DOI.** Upload `ECNBENCH-RELEASE/` (Zenodo: permanent DOI,
   50 GB limit), then set `\ecnarchivedoi` and `\ecnanonymousfalse` in the paper's
   preamble and fill the same DOI into `CITATION.cff`. The machinery is already in
   place; only the value is missing.
2. ~~**6 excluded Qwen2.5-14B events**...~~ **Resolved 2026-08-21**, see above.
3. Proofread pass on the newly-added Section~\ref{sec:four_model_extension} prose for
   flow/style consistency with the rest of the paper — content and numbers are
   verified, wording hasn't had a second read-through.
4. **Action-density scan, partly resolved 2026-08-26.** The scan behind
   Tables~\ref{tab:action_density_30event}--\ref{tab:action_breakdown} (2,407 actions,
   180 DBs) was taken 2026-07-27 and covers all 30 events, but 6 of those 180 DBs hold
   actions from the wrong-topic simulation. The corrected `.db` traces have now been
   transferred and released — **but the 180 DBs the scan read no longer exist**, so the
   scan cannot be repeated as taken. Correcting it means rescanning the released 18
   units against a fresh baseline, not reproducing the published counts. The paper now
   says exactly this.
5. ~~`ecn_bench_paper_conf.tex` carries stale 17-event statistics.~~ **Resolved
   2026-08-26**, see above. Both papers now compile clean and agree with the released
   JSONs.
6. **New 2026-08-26**: confirm the author block and ORCID in
   `ECNBENCH-RELEASE/CITATION.cff` before publishing; affiliation is inferred from the
   `ec-nantes.fr` account, ORCID is a commented placeholder.
