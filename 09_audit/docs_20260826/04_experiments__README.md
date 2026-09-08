# 04_experiments — the post-campaign controlled experiments

Four experiments run *after* the campaigns, in response to what the audit found. Each is
self-contained: generator, analysis, outputs. Three of the four **contradict** something
an earlier draft claimed — that is why they exist.

Run them with `python 05_analysis/make_workspace.py` first; see `00_docs/REPRODUCE.md`.

---

## 01_evaluator-replication

**Question:** how much of the measured signal is the evaluator rather than the swarm?

**Design:** all 4 models × 3 conditions, 4 independent Evaluator-A reads and 1
Evaluator-C read of byte-identical transcripts, restricted for the headline comparison
to the 20 events that are contamination-clean and common to all four models.

| File | Role |
|---|---|
| `build_reproducibility_analysis.py` | the analysis; **run this to regenerate** |
| `reproducibility_analysis_master.json` | **source of truth** for Table `tab:four_model_clean` |
| `evaluator_replication_expanded_analysis.json` | earlier per-unit dump with finer detail the rollup drops; superseded for anything reported |
| `ecn_replication_analysis.py` / `.json` | the J-versus-A instrument comparison |
| `make_replication_figures.py` | figures `figR1`, `figR2` |

**Finding:** re-scoring the same bytes drops the degenerate-forecast rate from 20.6 % to
6.1 % and dissolves the cross-model pattern. Re-reading Condition A three times
reproduces only 4/30 units exactly, mean Brier spread 0.128, max 0.715.

> **Scope discipline is mandatory here.** J-versus-A is an instrument comparison *only*
> where both passes read identical text: all 30 events for Mistral and Qwen2.5-7B, but
> **only the 6 outage-free events (C3, S2–S6) for Llama**. An earlier analysis ignored
> this and scored July readings against August readings of *re-simulated* transcripts —
> measuring the repair, not the instrument. It reported a pooled `r` of +0.415
> (Llama +0.144); the correct paired-scope value is **+0.552** pooled, and remarkably
> uniform per model (+0.589 / +0.587 / +0.549).

---

## 02_degeneracy-transfer

**Question:** is the flat-forecast degeneracy a property of one deployment, or does it
transfer to other evaluators reading the same transcripts?

**Design:** 60 simulated units, five comparison evaluators, all unconstrained (no
`response_format`), byte-identical input.

| File | Role |
|---|---|
| `run_degeneracy_transfer.py` | generator (needs an OpenRouter key) |
| `degeneracy_transfer.json` | the raw scored runs |
| `analyze_degeneracy_transfer.py` | analysis + figure `figK` |
| `degeneracy_transfer_summary.json` | the summary table |
| `probe_models.json` | the evaluator roster probed |

**Finding:** four of five evaluators return nothing uniform, but `qwen/qwen3-14b`
degenerates — and it fails on **the same transcripts**: 6 of its 8 flat units fall inside
Evaluator J's 19-unit flat set against 2.6 expected, one-sided Fisher **p = 0.012**, with
the same volume signature.

Two controls matter: the production rubric prompt (0/25) rules out "our prompt was
simpler", and `ministral-14b-2512` at 0/60 rules out parameter count alone. Both
degenerating instruments are small *reasoning* models, and the within-family contrast is
clean (qwen3-14b 8/58 vs qwen3-32b 0/57) — a pattern, not an established mechanism,
n = 1 per cell.

> **Run this on all 60 units, never on a screening subset.** A 6-unit probe suggested
> "the degeneracy does not transfer at all". On the full 60 that is false, and the wrong
> conclusion had already been written into a draft before it was caught.

---

## 03_truncation-grid

**Question:** does evidence *length* cause degeneracy, and does schema enforcement
prevent it?

**Design:** 2 (enforcement off/on) × 4 (assigned evidence length ~2k / ~5k / ~8k /
untruncated), evaluator, prompt, temperature and transcript fixed within each arm.
478 scored units.

| File | Role |
|---|---|
| `build_truncation_inputs.py` | builds the four length arms |
| `run_truncation_grid.py` | scores them (no lock — check for a running instance) |
| `analyze_truncation_grid.py` | analysis + figure `figL` |
| `truncation_results.json` | the summary |
| `scored_arms/event_results_trunc_*.json` | the 16 scored cells |

**Finding — a null on both mechanisms the paper previously credited.**

- **Assigned length does not raise degeneracy; the sign reverses.** Enforcement off,
  flat rate by length: ~1.8k **7/59**, ~4.8k 4/60, ~7.8k 0/60, untruncated **1/60**.
  Shortest is worst; two-sided Fisher 2k vs untruncated **p = 0.032**.
- **Enforcement, isolated within one model, does nothing.** Pooled over four lengths:
  **12/239 off vs 11/239 on, Fisher p = 1.000.** This is the *only* test in the project
  that varies enforcement alone — every earlier comparison, including the headline
  31/132 → 1/132 re-scoring, changed model **and** enforcement together, so none of them
  could attribute the effect to either.

What dominates instead is **which model reads the transcript**: the deepseek-r1 versus
qwen3-14b sharpness gap is ≈ 0.13 at every length, larger than either manipulation.

> **Design caveat that must travel with this result:** truncation cuts length and
> speaker count together — median distinct speakers 44 → 29 → 20 → 9 across untruncated
> → 8k → 5k → 2k. It converts an observational contrast into an assigned one; it does
> not decompose the bundle.

---

## 04_single-agent-cot-baseline

**Question:** does the multi-agent swarm beat one model thinking once?

**Design:** 240 runs — 20 contamination-clean events × 4 models × 3 replicates —
each given exactly the evidence the swarm's agents received.

| File | Role |
|---|---|
| `run_single_agent_cot_baseline.py` | generator; 240 calls |
| `single_agent_cot_baseline_results.json` | the raw runs (CoT text truncated to 300 chars) |
| `analyze_cot_baseline.py` | **the only authoritative analysis** |
| `cot_baseline_analysis.json` | all three aggregation variants and both pooling scopes |
| `make_cot_baseline_figure.py` | figure `figM` |

**Finding — non-superiority.** Pooled directional accuracy 0.834 (CoT) vs 0.819 (swarm);
matched-arm ΔBrier is not significant (clustered p = 0.109). So the *accuracy* half of
the paper's surviving claim is reproduced with **no deliberation at all**. Only the
B − C content-sensitivity contrast remains evidence about deliberation.

> **Three traps this design invites.** The first pass at this analysis fell into all
> three simultaneously and produced a spurious p = 0.045. They are documented in full in
> `00_docs/PROVENANCE.md` §4: only 2 of 4 arms are identity-matched; the 3 replicates
> must not be ensembled into the primary estimate; and events recur across arms, so
> pooled inference needs clustering (naive df = 67 gives p = 0.115 where clustered gives
> 0.267).
