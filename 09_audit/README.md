# 09_audit — superseded, invalid and excluded artifacts

`checksums_short_20260906.sha256` preserves the checksum manifest immediately before the full-report restoration. The release-root `checksums.sha256` describes the restored release; it excludes itself, Python caches and transient paper build logs/intermediates.

The September 2026 revision additionally archives the old manuscripts (`manuscript_20260826.tex`, `manuscript_conf_20260826.tex`), documentation (`docs_20260826/`), analysis entrypoints (`analysis_20260826/`), derived summaries (`outputs_20260826/`) and previous checksum manifest (`checksums_20260826.sha256`). These are historical records, not the current paper or analysis. The technical narrative below is also historical; consult `../00_docs/PROVENANCE.md` for current qualifications.

**Nothing here should be used as data.** It is kept so that every defect the paper
reports is independently checkable rather than merely asserted. If a reviewer asks
"how do you know that repair was broken?", the answer is a directory, not a paragraph.

Read `00_docs/PROVENANCE.md` first; it explains what each of these demonstrates.

| Directory | What it demonstrates |
|---|---|
| `stale-catalogue/` | **The root cause of two separate wrong-topic bugs.** Two `events_raw.json` files side by side: the authoritative root catalogue and the stale copy that shipped inside the HPC deployment directory. Diff them and seven ids disagree — C6, T1, T3, T4, T5, T6, T8. T1 and T5 collide silently: same options, same ground truth. |
| `qwen2.5-14b_excluded-wrong-topic/` | The 18 original rows (6 events) that were simulated against the wrong question — T3 debated a Bitcoin price threshold instead of the 2024 Taiwanese presidential election. **Do not merge these back in.** |
| `qwen2.5-14b_invalid-resimulation_2026-08-20/` | The re-simulation attempt that reproduced the identical bug, because its launch command used a relative `--events-raw` that resolved back to the stale file. Metadata only — `event_results.json`, `summary.json`, `run_manifest.json`, per-unit `simulation_config.json`, `execution.jsonl`. The 184 MB of databases were not retained; the manifests are what prove the bug. Compare `simulation_config.json`'s `event_question` against `01_benchmark/events_raw.json` to see it. |
| `qwen2.5-14b_recovery-inputs_fix7-rootcat/` | The inputs that were *actually* used for the successful 2026-08-21 re-simulation: the root catalogue, the seed dossiers for the six events, the injection bank, and the per-event job logs. |
| `llama_outage-repair-trail/` | The full Llama-3.1-8B repair history: the first, defective repair's outputs (`fix17`), the corrected one (`fix24`), the 23-event recovery reads, the S7 recovery, and timestamped pre-merge backups. |
| `pre-repair-archives/` | Per-model snapshots taken before each merge, plus `evaluator_dimension_labels_pre_fix/` — the four evaluator files as they stood before the stale-label backfill of 2026-08-16. |
| `cluster-side-evaluator-outputs/` | The raw evaluator outputs as they sat on the cluster, before merging into the campaign directories. Useful for verifying the merges. |
| `slurm-logs/` | The scheduler logs for every job that produced released data, including the failed ones. Job ids match the SLURM scripts in `07_pipeline/slurm/`. |
| `superseded-analyses/` | Analyses that were replaced and whose numbers must **not** be quoted — including `single_agent_cot_analysis_summary.json`, whose `n_units: 52` is simply wrong (the design has 80 unit-pairs), and a `figK_cot_vs_swarm.png` that collided with a different figure's filename. |
| `figure-backups/` | Every intermediate figure state kept during the audit: pre-title-crop originals, the dark/light theme conversion attempt, and pre-redraw versions. |

## Two things this directory proves

**1. The first Llama repair was invalid, and the paper says so.**
`build_dataset_and_run_phase2.py` rebuilt 72 recovery rows using keys
`simulation_config.json` does not have (`question` instead of `event_question`;
`evidence_text`, which does not exist at all). Both returned `''`, so every one of the
72 units was judged on an **empty Evidence field**, with the three conditions differing
by a single character. The negative post-release lift and the reversed susceptibility
this produced were artifacts. Restoring Condition A alone collapsed the lift reversal:
−0.161 → −0.028, n.s.

**2. The wrong-topic bug was caught twice, and both times before scoring.**
The check that caught it — diffing simulated questions against the root catalogue — is
cheap and should be a standing gate in any pipeline of this shape. Both the original
2026-08-14 campaign and the 2026-08-20 repair attempt failed it.

## Also not part of the release

An earlier exploratory Qwen-14B campaign from 2026-06-07 exists on the cluster
(three runs covering all 30 events). It predates the released protocol and is **not**
the campaign scored in `02_campaigns/qwen2.5-14b-awq/`. It is mentioned here only so
that nobody who gains access to that filesystem mistakes it for the released data.
