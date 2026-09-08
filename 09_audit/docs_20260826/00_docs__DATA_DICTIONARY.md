# Data dictionary

Every file format in this archive, field by field.

---

## 1. `event_results*.json` — the scored records (primary data)

A **JSON array of 90 objects**, one per unit (30 events × 3 conditions × 1 repeat).
Located in `02_campaigns/<model>/`. All evaluator passes share this schema; they differ
only in which evaluator produced the `probabilities` and everything derived from them.

### Identity and design

| Field | Type | Meaning |
|---|---|---|
| `event_id` | str | Catalogue id, e.g. `S2`, `C11`, `T3`. Prefix encodes the taxonomy: **C** = Social/Electoral, **S** = Senate/Binary, **T** = Technical/Economic. |
| `unit_id` | str | `<event>_<condition>_r<repeat>`, e.g. `S2_A_r1`. The primary key. |
| `question` | str | The forecasting question posed. |
| `ground_truth` | str | The realised outcome. Must be one of `options`. |
| `options` | list[str] | The answer set. K ranges 2–9 across the catalogue. |
| `condition` | str | `A` (No-Sim), `B` (With-Sim + relevant injection), `C` (With-Sim + null injection). |
| `repeat` | int | Always `1` in the released campaigns. |
| `seed_file` | str | Path to the seed dossier the agents read. Resolve against `01_benchmark/seeds/`. |

> **`options` is heterogeneous across events.** Chance is `1/K` per event, not 0.5.
> Any significance test against "chance" must therefore use a **Poisson binomial**, not
> a coin flip. Using 0.5 overstates significance dramatically.

### Execution status

| Field | Type | Meaning |
|---|---|---|
| `simulation_status` | str | `completed` / failure state. |
| `full_simulation_completed` | bool | Whether the multi-agent run finished. |
| `simulation_executed` | bool | **`false` for every Condition A row** — A is direct elicitation, no simulation. |
| `error` | str/null | Populated on failure. **See the caveat below.** |
| `strict_contract` | bool | Whether the unit satisfied the strict output contract. |

> **`error: null` does not prove the unit is healthy.** During the Llama-3.1-8B outage,
> 23 of 30 events executed against an unreachable endpoint while recording
> `error: null` **and** `evaluator_fallback_used: false`. The reliable tell is a
> **flat `round_jsd`** — the same placeholder value repeated at every checkpoint. Check
> it before trusting any unit. See `00_docs/PROVENANCE.md` §2.2.

### The forecast and its scores

| Field | Type | Meaning |
|---|---|---|
| `probabilities` | dict[str,float] | **The forecast.** Maps each option to a probability. Everything below derives from it. |
| `brier` | float | Multi-class Brier score, lower is better. **Bounded in [0, 2], not [0, 1]** — see below. |
| `rps` | float | Ranked probability score. |
| `directional_accuracy` | float | 1.0 if the modal option is the outcome; a k-way tie is credited `1/k`. |
| `directional_correct` | int | Hard 0/1 version. |
| `yes_probability` | float/null | Probability of the affirmative option, binary events only. |
| `weighted_rubric_score` | float | Aggregate of the qualitative rubric dimensions. |
| `calibration_bracket` | str | Confidence bin of the modal probability, e.g. `0.75-1`. |
| `calibration_predicted_probability` | float | The modal probability itself. |
| `calibration_hit` | int | Whether the modal option was correct. |
| `baseline_scores` | dict | Reference scores, incl. `uniform_random`, for computing skill scores. |

> **`brier` is the UNNORMALISED multi-category Brier score, bounded in [0, 2].**
> `BS = Σ_k (f_k − o_k)²`, summed over every category — not the ½-scaled `[0,1]` variant
> that the binary forecasting literature usually means by "Brier score". Zero is a
> perfect deterministic forecast; 2 is full confidence on the wrong category.
>
> **If you compare these values against `[0,1]`-normalised Brier scores from elsewhere,
> halve them first.** This is not hypothetical: 34 of the 360 primary unit scores exceed
> 1.0, which the ½-scaled convention cannot produce. Verified over all 5,890 scored rows
> in this archive: the campaign maximum is **1.883** (Mistral-7B `C12_C_r1`, Evaluator A
> read 3); exactly 2.0 occurs six times, only in the truncation grid; **nothing exceeds
> 2.0**.
>
> The uniform-forecast reference `BS_random = 1 − 1/K` in `baseline_scores` is the
> expected score of a uniform forecast *under this same convention*, so skill scores
> computed from it are internally consistent. Do not mix it with a ½-scaled `brier`.

> **A *flat* forecast is `probabilities` uniform at `1/K`.** It is the degeneracy the
> paper is about. Detect it with a tolerance — the test only fires within 0.005 of
> `1/K`, and `qwen/qwen3-14b` emits `0.49 / 0.51`, the same behaviour one rounding step
> away, which scores as a non-event.
>
> **Prefer `modal − 1/K` ("excess sharpness") over the flat rate or the raw modal
> probability.** Raw modal is not comparable across a mixed-K catalogue. Anchor value:
> Evaluator J scores +0.145 over its 60 simulated units.

### Evaluator metadata

| Field | Type | Meaning |
|---|---|---|
| `evaluator_fallback_used` | bool | Whether the evaluator fell back from structured output. |
| `evaluator_fallback_reason` / `_source` | str/null | Detail when it did. |
| `mcq_dimensions` | dict | Per-dimension categorical distributions the evaluator emitted (`prediction_accuracy`, `polarization`, …). Genuinely independent per read. |
| `evaluator_dimension_labels` | dict | Dominant-bucket label per dimension. |
| `evaluator_reliability_status` | str | `complete` / degraded. |
| `evaluator_noisy_dimensions` | list | Dimensions flagged unstable. |
| `validated_scales` | dict | Schema-versioned numeric rubric scores. |

> **`evaluator_dimension_labels` was stale in all four non-primary files** until
> 2026-08-16: the runner refreshed `probabilities` / `mcq_dimensions` /
> `validated_scales` per read but never this field, so every unit carried an identical
> label set regardless of its own (genuinely different) `mcq_dimensions`. It has since
> been backfilled from each file's own stored `mcq_dimensions`
> (`evaluator_dimension_label_basis: "single_read"`). No analysis in the paper reads it.
> Pre-fix originals are in `09_audit/pre-repair-archives/`.

### Simulation dynamics (Conditions B and C only)

| Field | Type | Meaning |
|---|---|---|
| `round_jsd` | list[float]/null | Jensen–Shannon divergence of the opinion distribution per checkpoint. |
| `convergence_monotonic` | bool/null | Whether JSD decreased monotonically. |
| `injection_direction` | str/null | Direction the round-30 injection argued. |
| `signed_delta` | float/null | Signed belief shift after injection. |
| `delta_conformity` | float/null | Conformity change. |
| `belief_update_failure` | bool/null | Whether the belief update failed. |

> **`round_jsd` telemetry is 27.7–87.7 % non-functional** across the campaigns. A
> previously reported convergence result inverted once this was accounted for. Treat
> every convergence field as suspect until you have checked the series is not flat.

### Evidence

| Field | Type | Meaning |
|---|---|---|
| `evidence_text` | str | **The exact text the evaluator read.** For Condition A this is the seed dossier; for B/C it is the transcript digest built by `build_evidence_text()`. |
| `micro_epistemic_mapping` | dict | Per-micro-question mapping produced by the evaluator. |

> `evidence_text` is the single most useful field for re-scoring with your own
> evaluator: it is what was actually shown, not a reconstruction. Its Condition-A value
> hashes **identically across all four campaigns on 30/30 events** — that is how the
> shared-baseline claim is verified.
>
> Note that `build_evidence_text()` reads `<unit>/{twitter,reddit}/actions.jsonl` plus
> the tail of `simulation.log` — **not** the SQLite database. A digest is capped, so it
> is not the complete transcript; the complete record is in `03_traces/`.

---

## 2. `summary.json` — campaign rollup

One object per campaign. Computed from `event_results.json` **only** (not from the other
evaluator passes). Regenerate with `summarize_event_results()`.

Top-level groups: `condition_mean_brier`, `lift` (`A_to_B`, `A_to_C`, `B_to_C`),
`directional_accuracy`, `weighted_rubric_score`, `rubric`, `evaluator_reliability`
(includes `kappa_by_dimension`), `content_susceptibility`, `signed_susceptibility`,
`rps`, `calibration`, `convergence`, `effect_size` (Cohen's *d* with bootstrap CI),
`power_analysis`, `strict_contract`, `evaluator_fallback`, `composite_score`,
plus row counters (`total_rows`, `simulation_success_count`, …).

`power_analysis.required_n_for_target_power` is **92** against `actual_n` of **30** —
the design is underpowered by roughly a factor of three, and every campaign says so.

---

## 3. `reproducibility_analysis.json` — cross-evaluator analysis

Per model; the master rollup over all four is
`04_experiments/01_evaluator-replication/reproducibility_analysis_master.json`, which is
the **authoritative source** for anything the paper reports about evaluator agreement.

| Key | Meaning |
|---|---|
| `model`, `generated_at_utc` | Provenance stamp. |
| `source_files` | Exactly which evaluator files were read. |
| `known_permanent_gaps` | `(file, unit)` pairs excluded because the read failed permanently. **Honour these.** |
| `instrument_spread` | Brier spread across the independent Evaluator-A reads of the same unit. |
| `cross_evaluator_agreement` | Pearson *r* between the Evaluator-A mean and Evaluator C. |
| `all_available_events` | Condition-level Brier / accuracy / lift / susceptibility / flat rate over all 30. |
| `clean_20_events_where_available` | The same, restricted to the contamination-clean set. |
| `clean_20_events_common_to_all_4_models` | **The basis for the headline cross-model table.** |

---

## 4. `run_manifest.json` — how the campaign was launched

Records `run_id`, `created_at`, the resolved paths to `events_raw` / `seeds_dir` /
`injection_bank`, `event_ids`, `conditions`, `repeats`, `total_agents` (300),
`total_simulation_hours` (60), `minutes_per_round` (60), `workflow_mode`
(`abc-per-event`), `benchmark_model`, `python_exe`, `weights_schema_version`,
`mcq_prompt_version`, and the determinism snapshot
(`deterministic_mode: true`, `temperature: 0.0`, `seed: 42`).

> **The manifest is how the wrong-topic bug is detectable.** `events_raw` records which
> catalogue was actually resolved. Diff the questions it yields against
> `01_benchmark/events_raw.json` before trusting any campaign. This check is what caught
> the invalid 2026-08-20 Qwen2.5-14B re-simulation.

---

## 5. `03_traces/<model>/<unit>/` — raw simulation traces

Present for Conditions B and C. Condition A units are small (~0.5 MB) and carry no
database, because no simulation ran.

| File | Contents |
|---|---|
| `twitter_simulation.db` | SQLite. Tables: `user` (300 rows), `post`, `comment`, `like`, `dislike`, `follow`, `mute`, `rec` (recommendations served), `trace` (the full action log), `chat_group`, `group_members`, `group_messages`, `report`, `product`. |
| `reddit_simulation.db` | Same schema, Reddit platform. |
| `twitter/actions.jsonl` | Line-delimited action log. Header line declares `total_rounds` and `agents_count`; then `round_start` / action / `round_end` records. |
| `reddit/actions.jsonl` | Same, Reddit. |
| `twitter_profiles.csv`, `reddit_profiles.json` | The 300 generated agent personas. |
| `simulation_config.json` | The resolved configuration for this unit, including `event_question`. |
| `simulation.log` | Full driver log. Large (often 3 MB+). |

Campaign-level `_execution_traces/execution.jsonl` records job-level events.

> **Two header caveats.** (1) `actions.jsonl`'s header declares `total_rounds: 120`
> while the run actually emits rounds 0–60, matching `run_manifest.json`'s 60. Trust the
> observed `round` values. (2) **Action density is very low** — a typical Condition-B
> twitter trace contains only a handful of `CREATE_POST` actions across 300 agents and
> 60 rounds. This is a real property of the runs, analysed in the paper's
> interaction-realism section, not a truncated export.

---

## 6. `01_benchmark/events_raw.json` — the catalogue

The authoritative 30-event definition: id, question, options, ground truth, resolution
date and the seed-dossier reference for each.

> There are **two** catalogues in circulation and they disagree on seven ids
> (C6, T1, T3, T4, T5, T6, T8). `01_benchmark/events_raw.json` is the authoritative
> root catalogue. The stale one is preserved for diffing at
> `09_audit/stale-catalogue/events_raw_STALE_ECN-HPC-DEPLOY.json`. **T1 and T5 collide
> silently** — same options, same ground truth — so an id mix-up between them produces
> no error, only wrong data.

---

## 7. Units, counts and the sets you will actually analyse

| Set | Size | What it is |
|---|---|---|
| All units | 360 | 4 models × 30 events × 3 conditions |
| Simulated units | 240 | Conditions B and C only |
| Contamination-clean events | 20 | Resolve after every model's release date **and** present for all four models. The basis for the headline table. |
| Clean (model, event) pairs | 80 | 20 events × 4 models |
| Paired instrument scope | 198 units | Where Evaluator J and Evaluator A read byte-identical text: all 30 events for Mistral and Qwen2.5-7B, but **only the 6 outage-free events (C3, S2–S6) for Llama**. |

> The paired-scope restriction is not optional. Scoring July readings against August
> readings of *re-simulated* transcripts measures the repair, not the instrument — an
> earlier analysis did exactly that and reported a spurious pooled `r` of +0.415
> (Llama +0.144) where the correct paired-scope value is **+0.552** pooled, and a
> strikingly uniform +0.589 / +0.587 / +0.549 per model.
