# Provenance, defects and corrections

This file exists because ECN-BENCH's results changed materially during auditing. Several
findings that appeared in earlier drafts were **artifacts of bugs**, and were withdrawn.
Anyone reusing this data needs to know which is which.

Nothing here is hidden in a footnote: every defect below is reproducible from artifacts
in this archive, and the superseded versions are kept in `09_audit/`.

---

## 1. The headline result of the audit

The benchmark was built to measure whether multi-agent deliberation improves
forecasting. What the audit found instead is that **the measuring instrument dominates
the measurement.**

Re-scoring the same, byte-identical transcripts with a second, schema-enforced evaluator
drops the degenerate-forecast rate from 20.6 % to 6.1 % and dissolves the cross-model
pattern entirely. Re-reading Condition A's *identical* input three times reproduces only
4 of 30 units exactly, with a mean Brier spread of 0.128 and a maximum of 0.715 — large
enough to reverse the sign of one model's headline lift.

Practical consequence for anyone reusing this data: **never compare a number from one
evaluator file against a number from another.** The scored records are kept in separate
files for exactly this reason.

---

## 2. Defects found, and what each one cost

### 2.1 Silent schema-disabling in the primary evaluator (Evaluator J)

A keyword-matching heuristic in the evaluator turned off structured-output enforcement
across all three original campaigns without logging it. Under the unconstrained
instrument, long transcripts frequently produced *flat* forecasts — a uniform
probability of 1/K — which the pipeline scored as genuine low-confidence predictions.

- Affects: every `event_results.json` row scored in July 2026.
- Detected: 2026-08 re-scoring pass.
- Status: **documented, not repaired.** Evaluator J cannot be re-run (the endpoint is
  gone), so its readings are kept as-is and always reported next to the
  schema-enforced passes.

### 2.2 The Llama-3.1-8B backend outage — and a repair that was itself invalid

A run-integrity audit found the reference campaign's backend had failed silently on
**23 of 30 events**, recording `error: null` and `evaluator_fallback_used: false` while
executing against an unreachable endpoint. `round_jsd` telemetry for those units is a
flat placeholder value.

The **first repair (2026-08-16) was defective and produced two spurious findings.**
`build_dataset_and_run_phase2.py` rebuilt the recovery rows using keys that
`simulation_config.json` does not contain (`question` instead of `event_question`;
`evidence_text`, which does not exist at all). Both returned the empty string, so **all
72 units were judged on an empty Evidence field** — the three conditions differing by a
single character. The negative post-release lift and the reversed susceptibility that
this produced were artifacts, not findings.

The same script also pointed at a stale event catalogue, so seven event ids
(C6, T1, T3, T4, T5, T6, T8) simulated a *different event* than their id claims. T1 and
T5 collided silently — same options, same ground truth.

**Corrected the same day**: the seven catalogue-collision events were re-simulated
against the root catalogue; `evidence_text` was rebuilt with the pipeline's own
`build_evidence_text()`; all 48 B/C units were re-scored across six passes.
**Condition A was restored, never re-scored** — it is the shared No-Sim reference and
its `evidence_text` hashes identically across all campaigns on 30/30 events.

- Repair trail: `09_audit/llama_outage-repair-trail/`
- Pre-merge backups: `09_audit/llama_outage-repair-trail/pre_merge_backups/`
- Merge script: `07_pipeline/repair/merge_llama_fix24.py`

**Known residue:** the injection bank was deliberately left stale-aligned for those
seven ids. Re-authoring it would have given Llama better stimuli than the other three
campaigns, which all ran under the same off-topic injection. This is a design
limitation, stated in the paper, not a bug that was missed.

### 2.3 Qwen2.5-14B: six events simulated against the wrong topic

The 2026-08-14 campaign was built from the stale `ECN-HPC-DEPLOY/data/events_raw.json`
instead of the authoritative catalogue at the repository root. Six events
(**T3, T4, T5, T6, C6, T8**) were therefore simulated against the wrong question — the
swarm genuinely deliberated about a different topic (T3 debated a Bitcoin price
threshold instead of the 2024 Taiwanese presidential election). Rescoring could not fix
this; the transcripts themselves were about the wrong thing.

The **first re-simulation attempt (2026-08-20) reproduced the identical bug**, because
its launch command used a relative `--events-raw ../../data/events_raw.json` that
resolved back to the same stale file. It was caught by diffing the simulated questions
against the root catalogue *before* scoring.

- Invalid attempt, metadata retained: `09_audit/qwen2.5-14b_invalid-resimulation_2026-08-20/`
- The two catalogues, side by side, for diffing: `09_audit/stale-catalogue/`
- Corrected inputs actually used: `09_audit/qwen2.5-14b_recovery-inputs_fix7-rootcat/`
- Original wrong-topic rows: `09_audit/qwen2.5-14b_excluded-wrong-topic/`

The successful re-simulation (2026-08-21, two SLURM jobs to fit the 2-GPU-per-user QOS)
brought the campaign to 30/30. Its traces are in
`03_traces/qwen2.5-14b-awq/recovered-2026-08-21/`.

**Ripple effect worth knowing:** recovering these events grew the globally-clean event
set from 17 to 20 and changed cross-evaluator-agreement figures **for all four models**,
because the earlier values had drifted from a stale prior run. Trust
`04_experiments/01_evaluator-replication/reproducibility_analysis_master.json`, not any
number transcribed elsewhere.

### 2.4 Three permanently-failed evaluator reads are excluded, not counted

`Qwen2.5-7B: T3_C_r1, C9_A_r1, C13_C_r1` (in `repeat3.json`) and
`Qwen2.5-14B: T1_C_r1` (in `repeat2.json`) failed repeatedly against OpenRouter. The
rows still exist in those files but hold a **stale, never-overwritten copy of an earlier
pass's value**. Counting them as genuine extra reads artificially deflated spread and
skewed the robust mean.

They are excluded explicitly by `(file, unit)` pair in `KNOWN_GAPS` inside
`build_reproducibility_analysis.py`. If you write your own analysis over the repeat
files, **you must exclude them too**, or your instrument-spread numbers will be wrong.

### 2.5 One unaffected-looking Qwen2.5-14B unit carries the outage signature

`C9_C_r1` has `error: null` and `evaluator_fallback_used: false`, but its `round_jsd` is
the flat placeholder `0.758277` repeated across every checkpoint — the same signature as
the Llama outage. It could not be re-simulated (the model is not served by OpenRouter or
Ollama Cloud), so it is left as a documented single-unit gap rather than silently
trusted. `C9_A_r1` and `C9_B_r1` are unaffected.

---

## 3. Claims that were withdrawn

These appeared in earlier drafts and are **not supported** by the released data. They
are listed so that nobody re-derives them from a stale summary.

| Withdrawn claim | Why it fails |
|---|---|
| "Negative post-release lift; reversed susceptibility" (Llama) | Artifact of the empty-evidence repair (§2.2). Restoring Condition A alone collapsed it: −0.161 → −0.028, n.s. |
| "Evidence volume drives degeneracy" | An association *inside Evaluator J only*. When length is **assigned** rather than observed, the sign reverses: flat rate 7/59 at ~1.8k chars vs 1/60 untruncated (Fisher p = 0.032). |
| "Schema enforcement prevents degeneracy" | The only test that varies enforcement *alone*, holding the model fixed, is null: 12/239 off vs 11/239 on, Fisher p = 1.000. Every earlier comparison changed model **and** enforcement together. |
| "The degeneracy does not transfer to other evaluators" | Based on a 6-unit screening probe. On the full 60 units it is false: `qwen/qwen3-14b` degenerates on the *same* transcripts (6 of its 8 flat units fall in Evaluator J's 19-unit flat set, one-sided Fisher p = 0.012). |
| "Difficulty predicts simulation benefit (r = 0.847)" | Arithmetic artifact of regressing a difference on its own minuend. The mechanical value alone is +0.862. |
| "Multi-agent deliberation beats a single model" | A single chain-of-thought call reproduces the directional accuracy on its own (§4). |

**What survives**: on the 20 events resolving after every model's release date, the
swarm's modal forecast is the realised outcome in 81.9 % of 80 (model, event) pairs
against a 32.6 % chance baseline (exact Poisson-binomial p = 3.7 × 10⁻²²), and the
forecast tracks the *content* of what is deliberated over — replacing the injected
evidence with topically matched but unrelated material costs 0.112 Brier
[+0.042, +0.182].

---

## 4. The single-agent baseline bounds even that

A single chain-of-thought call, given exactly the evidence the swarm's agents received
(240 runs: 20 clean events × 4 models × 3 replicates), **matches the swarm** on pooled
directional accuracy (0.834 vs 0.819) and is not significantly worse on Brier
(clustered p = 0.109 on identity-matched arms).

So the *accuracy* half of the surviving claim is reproduced with no deliberation at all.
Only the **B − C content-sensitivity contrast** remains evidence about deliberation
rather than about what the base models already know.

**Three analysis traps this experiment invites — all three were fallen into
simultaneously on the first pass, and together they manufacture a spurious p = 0.045:**

1. **Only 2 of the 4 arms are identity-matched.** `mistralai/ministral-8b-2512` is not
   Mistral-7B-Instruct-v0.1, and `qwen/qwen3-14b` is not Qwen2.5-14B. The four-arm pool
   is a cross-model comparison and must be reported separately.
2. **Do not ensemble the 3 CoT replicates.** That is a 3×-cost arm; the swarm's four
   reads re-read *one* simulation. The primary estimate is the mean of per-replicate
   scores. (Replicate 1 is temperature 0, replicates 2–3 are 0.7 — they are not
   homogeneous draws.)
3. **Events recur across arms.** Pooled inference needs a cluster bootstrap over events
   plus a cluster-robust t (df = 16). The naive df = 67 test gives p = 0.115 where the
   clustered one gives 0.267.

---

## 5. Data that does not exist, and why

| Missing | Reason |
|---|---|
| Qwen2.5-14B raw traces for 21 of 30 events | Deleted by the cluster's scratch-filesystem policy before transfer. Scored records survive in full. Only C15 (3 units) survives from the original 2026-07-27 campaign. |
| A fourth Evaluator-A read for Qwen2.5-14B | There is no original single-pass Evaluator-A record to add as a fourth; that model has 3 reads, the others have 4. |
| `event_results_evaluatorB_openrouter.json` for Qwen2.5-14B | Its original pass was not scorable at the time that pass was run for the other three campaigns. |
| July Evaluator-J scoring for Llama's 24 recovery events | Those events did not exist in July. The J-vs-A comparison is therefore an instrument comparison **only** on all 30 events for Mistral and Qwen, and only on Llama's 6 outage-free events (C3, S2–S6). |
| Re-scanned action-density counts for Qwen2.5-14B | The 2026-07-27 scan (2,407 actions, 180 DBs) covers all 30 events, but 6 of those DBs hold actions from the wrong-topic simulation. The corrected traces were never folded into a fresh scan. |

---

## 6. Operational traps, for anyone re-running this

- **`LLMClient.chat` runs `re.sub()` straight on `message.content`.** Reasoning
  evaluators exhaust a small `max_tokens` on reasoning alone, return
  `finish_reason=length, content=None`, and the unit dies with *"expected string or
  bytes-like object, got 'NoneType'"*. Raise the budget to 6 000–16 000 and coerce null
  content. 15 of 34 units failed this way during the Llama repair.
- **A hardcoded `max_tokens=65536` overflows `deepseek/deepseek-r1`'s 64 k context.**
- **`urllib`'s `timeout=` does not effectively bound the hang** seen against OpenRouter:
  a 240-task run stalled at 220/240 for 15+ minutes with the process near-idle. Retry
  the missing combinations at lower concurrency with a short timeout.
- **`run_truncation_grid.py` has no lock.** Two drivers writing the same
  `event_results_trunc_*.json` clobber each other. Check for a running instance first.
  Completed units are skipped on re-run, so the driver is safely resumable.
- **Opening an SFTP channel and then `exec_command` on the same paramiko transport
  fails** with `ChannelException(2, 'Connect failed')`. Use a separate connection.

---

## 7. Timeline

| Date | Event |
|---|---|
| 2026-06-07 | Early exploratory Qwen-14B campaign (not part of this release) |
| 2026-07-04 → 07-18 | The three original campaigns: Llama-3.1-8B, Mistral-7B, Qwen2.5-7B. Scored by Evaluator J. |
| 2026-07-27 | Qwen2.5-14B campaign. Action-density scan taken (180 DBs). |
| 2026-08-14 | Qwen2.5-14B audited; 6 wrong-topic events found and excluded (24/30 kept) |
| 2026-08-15 | Evaluator replication extended to 4 models × 3 conditions × 5 reads |
| 2026-08-16 | Llama outage found; first repair made and found invalid; corrected repair completed the same day |
| 2026-08-17 | Degeneracy-transfer and truncation-grid experiments; two mechanism claims withdrawn |
| 2026-08-21 | Qwen2.5-14B recovered to 30/30; clean event set grows 17 → 20; all downstream numbers regenerated |
| 2026-08-26 | This archive assembled; Qwen2.5-14B recovered traces transferred off the cluster for the first time |

---

*Every defect above is demonstrable from files in `09_audit/`. If you find one that is
not, that is a bug in this document — please report it.*
