# ECN-BENCH — Replication Package

Complete data, code and audit trail behind the ECN-BENCH technical report:
*a multi-agent social-simulation forecasting benchmark, and the audit that changed
what it claims.*

**Start here.** This archive is arranged so that a reader can go from "what is this?"
to "I have reproduced Table X" without asking the authors anything. Read this file,
then `00_docs/PROVENANCE.md` — it tells you which numbers are trustworthy and which
were withdrawn, and why.

---

## What the experiment is

Four open-weight LLMs each forecast the same **30 real-world events** under **three
conditions**:

| Condition | Name | What the model gets |
|---|---|---|
| **A** | No-Sim baseline | The seed dossier, queried directly. Raw knowledge, no deliberation. |
| **B** | With-Sim benchmark | A multi-agent social simulation (300 agents, 60 rounds) reads the dossier and deliberates. At round 30 a **content-relevant** news injection arrives. Forecast extracted at round 60. |
| **C** | Null control | Identical to B, except the round-30 injection is **length-matched but topically unrelated**. |

`B − C` isolates sensitivity to *content*. `A → B` measures whether deliberation helps
at all. One `(model, event, condition)` triple is a **unit**; there are
4 × 30 × 3 = **360 units**.

> **Condition A is a single shared record, not a per-model baseline.** It was run once
> and reused across all four campaigns. Every `A → B` comparison in the paper carries
> this caveat, and it is the single biggest limitation of the design. See
> `00_docs/PROVENANCE.md`.

## The four models under test

| Directory | Model | Serving |
|---|---|---|
| `llama-3.1-8b-awq` | `hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4` | local vLLM on HPC; 24 of 30 events re-simulated via OpenRouter `meta-llama/llama-3.1-8b-instruct` after a backend outage |
| `mistral-7b-awq` | `mistralai/Mistral-7B-Instruct-v0.1` | local vLLM on HPC |
| `qwen2.5_7b` | `Qwen/Qwen2.5-7B-Instruct` | local vLLM on HPC |
| `qwen2.5-14b-awq` | `Qwen/Qwen2.5-14B-Instruct-AWQ` | local vLLM on HPC |

Directory names are kept exactly as the paper and the original campaign records use
them, so cross-references never break — even where the name is imprecise
(`mistral-7b-awq` was not in fact AWQ-quantised).

## The evaluators — read this before comparing any two numbers

A forecast is a probability vector extracted from a transcript **by an LLM**. Different
extractors disagree substantially on the *same bytes*. That is the paper's central
finding, so the passes are released as **separate files, never merged**:

| File | Evaluator | Model | Schema enforced? | Reads |
|---|---|---|---|---|
| `event_results.json` | **J** (primary) | DeepSeek-R1-Distill-Qwen-14B, local | **No** — silently disabled by a keyword heuristic | 1 |
| `event_results_evaluatorB_openrouter.json` | **A** | `deepseek/deepseek-v4-flash-0731` | Yes | 1 |
| `event_results_evaluatorA_repeat{1,2,3}.json` | **A** | `deepseek/deepseek-v4-flash-0731` | Yes | 3 more |
| `event_results_evaluatorC_gptlunapro.json` | **C** | `openai/gpt-5.6-luna-pro` | Yes | 1 |

Two exceptions, both documented in `00_docs/PROVENANCE.md`:
Llama's 24 repaired events and Qwen2.5-14B's 18 recovered rows inside
`event_results.json` were scored by `deepseek/deepseek-r1`, **not** by Evaluator J —
that file is therefore instrument-mixed for those rows. Qwen2.5-14B has no
`evaluatorB` file at all.

---

## Layout

```
00_docs/          Provenance, data dictionary, reproduction guide, LaTeX snippet
01_benchmark/     The benchmark definition: 30-event catalogue, seeds, injections
02_campaigns/     PRIMARY DATA — per-unit scored records, 4 models
03_traces/        Raw multi-agent simulation traces (SQLite + JSONL + logs)
04_experiments/   The four post-campaign controlled experiments
05_analysis/      Analysis scripts and their JSON outputs
06_figures/       Every figure the paper renders (30 PNGs)
07_pipeline/      The code that produced all of the above, incl. SLURM job scripts
08_paper/         The technical report and the conference version
09_audit/         Superseded, invalid and excluded artifacts — kept on purpose
```

Directories are numbered in **reading order**, not importance. Each has its own
`README.md` describing every file in it.

## Where to start, by intent

| You want to… | Go to |
|---|---|
| Re-derive a table or figure in the paper | `00_docs/REPRODUCE.md` |
| Understand a field in a scored record | `00_docs/DATA_DICTIONARY.md` |
| Know which claims survived the audit | `00_docs/PROVENANCE.md` |
| Score these transcripts with *your own* evaluator | `03_traces/` + `07_pipeline/prompts/` |
| Reuse the benchmark on a new model | `01_benchmark/` + `07_pipeline/` |
| Cite this archive | `CITATION.cff` |
| Check nothing was altered | `checksums.sha256` |

## Size

~2.4 GB, dominated by `03_traces/` (360 SQLite databases plus per-agent action logs).
Everything else totals about 120 MB. If you only want the numbers, `02_campaigns/`,
`04_experiments/` and `05_analysis/` are enough.

## Honest limits of this archive

1. **Qwen2.5-14B's raw traces are largely gone.** Released: the 18 units recovered
   2026-08-21, plus a 3-unit fragment (event C15) that is all that survives of the
   original 2026-07-27 campaign. The other 21 events' transcripts were deleted by the
   cluster's scratch policy before they were transferred. Their *scored records*
   survive in full — only the underlying transcripts are unrecoverable.
2. **Evaluator J cannot be re-run.** The local DeepSeek-R1-14B endpoint no longer
   exists and no provider serves that model. Every Evaluator-J number in the paper is
   therefore a measurement that cannot be repeated, only re-analysed.
3. **Three OpenRouter reads failed permanently** and are explicitly excluded rather
   than silently counted. See `00_docs/PROVENANCE.md`.
4. **The design is underpowered** at E = 30 events. The paper says so throughout;
   this archive does not fix it.

## License

Data and documentation: CC BY 4.0. Code: see `07_pipeline/README.md`.
Event dossiers quote publicly reported news; they are redistributed here for
research reproducibility under fair-use/quotation provisions.

---

*Archive assembled 2026-08-26. Contents verified against `checksums.sha256`.*
