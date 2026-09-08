# Reproducing the results

Every number and figure in the paper is regenerable from this archive. This page gives
the exact commands, and states honestly which parts **cannot** be reproduced and why.

---

## Verified status

The chain below was run end-to-end against this archive on **2026-08-26**. All five
analyses regenerated output that is **byte-identical to the released files**, ignoring
only their embedded generation timestamps:

| Analysis | Result |
|---|---|
| `reproducibility_analysis_master.json` | identical |
| `predictive_signal_analysis.json` | identical |
| `cot_baseline_analysis.json` | identical |
| `degeneracy_transfer_summary.json` | identical |
| `truncation_results.json` | identical |

If your run produces something different, that is a finding — please report it.

---

## 1. Set up

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r 07_pipeline/backend/requirements.txt
```

Python 3.11+ works; the archive was verified on 3.14. Only the analysis path is needed
for everything on this page — no GPU, no cluster, no API keys.

## 2. Build the working layout

The analysis scripts were written to run from the original repository root, where the
campaigns sit at `completed_benches/<model>/<campaign_id>/` beside the scripts. This
archive is organised for readers instead, so one command materialises the layout they
expect:

```bash
python 05_analysis/make_workspace.py
cd _workspace
```

`_workspace/` hard-links the 2.3 GB of raw traces (costing almost no disk) and **copies**
everything a script might overwrite, so re-running an analysis can never modify the
released archive. Delete `_workspace/` at any time; nothing else depends on it.

## 3. Regenerate the analyses

Run from inside `_workspace/`. Each takes seconds to a couple of minutes.

```bash
# Evaluator replication -> Table tab:four_model_clean, Section sec:four_model_extension
python ECN-HPC-DEPLOY/build_reproducibility_analysis.py
#   writes reproducibility_analysis.json (per model) + reproducibility_analysis_master.json
#   and prints the four rows of the headline cross-model table

# The surviving positive result -> Table tab:predictive_signal, Figure figJ
python make_predictive_signal.py
#   writes predictive_signal_analysis.json + figJ_predictive_signal.png

# Single-agent CoT baseline -> Table tab:cot_baseline, Figure figM
python analyze_cot_baseline.py
python make_cot_baseline_figure.py
#   writes cot_baseline_analysis.json + figM_cot_vs_swarm.png

# Cross-evaluator degeneracy transfer -> Figure figK
python analyze_degeneracy_transfer.py
#   writes degeneracy_transfer_summary.json + figK_degeneracy_transfer.png

# The 2x4 truncation grid -> Figure figL
python analyze_truncation_grid.py
#   writes truncation_results.json + figL_truncation.png

# The degeneracy/volume mechanism -> Figure figI
python make_volume_figure.py

# Audit and replication figure sets
python make_audit_figures.py
python make_audit3_figures.py
python make_replication_figures.py
```

> **`reproducibility_analysis_master.json` is the source of truth**, not the LaTeX
> tables. Tables have drifted from it during manual transcription in the past. When the
> two disagree, the JSON is right.

## 4. Rebuild the paper

```bash
cd 08_paper
tectonic -X compile ecn_bench_paper.tex
```

Tectonic 0.17 resolves all packages offline on first run. Expect **85 pages, 0 errors,
0 undefined references or citations, 0 overfull boxes**, and 2 long-standing cosmetic
underfull hboxes.

---

## 5. Re-running the *generators* (needs credentials)

The commands above re-analyse existing runs. Re-running the runs themselves calls
external APIs and costs money.

```bash
export OPENROUTER_API_KEY=...

python run_single_agent_cot_baseline.py   # 240 calls: 20 events x 4 models x 3 replicates
python run_degeneracy_transfer.py         # 60 units x 5 evaluators
python build_truncation_inputs.py         # build the 4 length arms
python run_truncation_grid.py             # score them
```

Practical warnings, learned the hard way:

- **`run_truncation_grid.py` has no lock.** Two drivers writing the same
  `event_results_trunc_*.json` clobber each other. Check for a running instance first.
  Completed units are skipped on re-run, so it is safely resumable.
- **`run_single_agent_cot_baseline.py` can hang** near the end of a large batch with the
  process near-idle; `urllib`'s `timeout=` does not effectively bound it. Kill it and
  retry only the missing `(model, event, repeat)` combinations at lower concurrency.
- **Raise the evaluator token budget.** Reasoning models spend a 1 500-token budget
  entirely on reasoning and return `content=None`, which crashes the scorer. Use
  6 000–16 000 and coerce null content.
- **Model availability drifts.** The OpenRouter model ids in these scripts were live in
  August 2026. Substituting a different model produces a different measurement — which
  is, after all, this paper's point.

## 6. Re-running the simulations (needs an HPC cluster)

`07_pipeline/slurm/` holds the exact SLURM scripts used, and `07_pipeline/hpc/` the
protocol runner. These target a specific cluster (GLiCID/Nautilus: A100 nodes, vLLM,
Apptainer, a Neo4j instance per job) and will need adapting. `07_pipeline/README.md`
describes what each script does and what it assumes.

**Before trusting any re-simulation, diff the questions it produced against
`01_benchmark/events_raw.json`.** Two separate attempts in this project silently
simulated the wrong events because a relative `--events-raw` path resolved to a stale
catalogue. Always pass an absolute path. See `00_docs/PROVENANCE.md` §2.3.

---

## 7. What cannot be reproduced

| Not reproducible | Why |
|---|---|
| **Evaluator J's readings** | The local DeepSeek-R1-Distill-Qwen-14B endpoint no longer exists and no provider serves that model. Every Evaluator-J number is a measurement that can be re-analysed but never repeated. This is also why the decisive follow-up experiment — the truncation grid against a restored DeepSeek-R1-14B endpoint — remains open. |
| **Qwen2.5-14B's original transcripts** for 21 of 30 events | Deleted by the cluster's scratch policy before transfer. Their scored records survive in full; the transcripts do not. |
| **Bit-exact re-simulation** | Runs are deterministic in configuration (`temperature: 0.0`, `seed: 42`) but depend on the serving stack — vLLM version, quantisation, batching. Expect close, not identical. |
| **The action-density scan for Qwen2.5-14B** | Taken 2026-07-27 over 180 databases that no longer exist; 6 of them held wrong-topic actions. |

## 8. Re-scoring with your own evaluator

This is the most valuable thing a third party can do with this archive, because the
paper's central claim is that the extractor dominates the measurement.

You need two things, both released:

1. `evidence_text` from any `event_results*.json` row — the **exact bytes** the evaluator
   read, not a reconstruction.
2. `07_pipeline/prompts/ecnbench_mcq_v1.yaml` — the scoring rubric.

Then compare against the existing passes. Two methodological requirements:

- **Report `modal − 1/K`, not the flat rate.** The flat test only fires within 0.005 of
  uniform, so a model emitting `0.49 / 0.51` — the same behaviour, one rounding step
  away — scores as a non-event. Anchor: Evaluator J = +0.145 over its 60 simulated units.
- **Vary one thing at a time.** Every comparison in this project before the truncation
  grid changed the evaluator model *and* schema enforcement together, so none of them
  could attribute the effect to either. Isolating enforcement within one model gave a
  null (12/239 vs 11/239, Fisher p = 1.000).
