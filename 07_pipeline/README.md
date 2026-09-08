# 07_pipeline — the code that produced everything

> Historical source snapshots, not a verified reconstruction of every runtime configuration. Complete request-level logs are unavailable. These scripts may launch HPC jobs or paid model calls; do not execute them to reproduce the revised paper. Use [offline reanalysis](../00_docs/REPRODUCE.md) instead.

The simulation engine, the HPC protocol runner, the evaluator runners, the SLURM job
scripts as actually submitted, and the scoring rubric.

```
backend/        the MiroFish-Offline simulation + scoring engine (app package)
hpc/            protocol runner, evaluator runners, analysis builders
slurm/          the job scripts as submitted to the cluster
prompts/        the evaluator rubric
repair/         the merge and re-score scripts used during the repairs
```

## `backend/` — the engine

The `app` package that runs the simulations and computes the scores. 57 modules, ~1 MB.
The parts most likely to matter to a reader:

| Module | Role |
|---|---|
| `app/benchmarks/protocol.py` | the A/B/C protocol itself |
| `app/benchmarks/evaluator.py` | forecast extraction from a transcript |
| `app/benchmarks/scoring.py` | Brier, RPS, calibration, directional accuracy |
| `app/benchmarks/statistics.py` | bootstrap CIs, Diebold–Mariano, power |
| `app/benchmarks/injection_loader.py` | the round-30 perturbations |
| `app/benchmarks/orchestrator.py` | the multi-agent loop |
| `app/benchmarks/role_router.py` | routes agent / evaluator / graph-builder roles to different endpoints |
| `app/benchmarks/reliability.py` | evaluator agreement, kappa |
| `app/services/oasis_profile_generator.py` | generates the 300 agent personas |
| `app/services/simulation_runner.py` | drives a single simulation unit |

`requirements.txt`, `pyproject.toml` and `uv.lock` are included so the environment is
reconstructible. `analyze_truncation_grid.py` imports `app.benchmarks.scoring` from
here; `05_analysis/make_workspace.py` places it where that import resolves.

## `hpc/` — cluster-side runners

| Script | Role |
|---|---|
| `run_ecnbench_protocol_hpc.py` | the main protocol runner (~113 KB) |
| `run_openrouter_eval_official.py` | scores units against OpenRouter evaluators |
| `run_hpc_evaluator_standalone.py` | evaluator-only pass against a local endpoint |
| `separate_evaluator_datasets.py` | splits merged evaluator output into per-pass files |
| `build_reproducibility_analysis.py` | the cross-evaluator rollup |
| `api_eval_runner.py`, `local_eval_runner.py` | API vs local evaluation drivers |
| `eval_qwen14b_dedicated.py`, `repair_fast_3models.py`, `rescore_qwen14b_fix6_primary.py` | targeted re-scoring |
| `audit_waves_post_outage.py`, `find_qwen14b_sims.py` | audit helpers |

## `slurm/` — the jobs as submitted

The scripts that produced the released data, including the ones that produced *invalid*
data. `run_qwen14b_6events_fix_gpu.slurm` is the attempt that silently used the stale
catalogue; `run_qwen14b_6events_fix_rootcat.slurm` and the `3events_rootcat_A/B` pair
are the corrected re-run. Keeping both is the point — the diff between them is the bug.

## `prompts/ecnbench_mcq_v1.yaml` — the rubric

The scoring rubric, versioned `v1` (matching `mcq_prompt_version` in every
`run_manifest.json`). If you re-score these transcripts with a different evaluator, use
this so the only thing that changes is the model.

---

## Environment assumptions

These scripts targeted a specific cluster — GLiCID/Nautilus: A100 nodes, vLLM behind
Apptainer, a per-job Neo4j instance, SLURM with a 2-GPU-per-user QOS. They will need
adapting. Paths inside the SLURM scripts are absolute and refer to a scratch filesystem
that no longer holds this data.

## Four traps that cost real time

1. **Always pass an absolute `--events-raw`.** Two separate re-simulation attempts in
   this project silently simulated the wrong events because a relative path resolved to
   a stale catalogue. Diff the simulated questions against
   `01_benchmark/events_raw.json` before scoring anything.
2. **Raise the evaluator token budget.** The call site asks for 1 500; a reasoning model
   spends that entirely on reasoning, returns `content=None`, and the scorer dies with
   *"expected string or bytes-like object, got 'NoneType'"*. Use 6 000–16 000 and coerce
   null content. Separately, a hardcoded `max_tokens=65536` overflows
   `deepseek/deepseek-r1`'s 64 k context.
3. **`run_truncation_grid.py` has no lock.** Two drivers writing the same output file
   clobber each other, and killing a Python worker does not kill the bash driver — it
   just starts the next cell.
4. **`error: null` does not mean healthy.** The Llama outage recorded exactly that on 23
   of 30 events while executing against an unreachable endpoint. Check `round_jsd` for a
   flat placeholder series.

## License

The engine derives from MiroFish-Offline; its license terms apply to `backend/`.
The runners, SLURM scripts and analysis code in this archive are released for research
reuse. Attribution to the paper is requested — see `CITATION.cff`.
