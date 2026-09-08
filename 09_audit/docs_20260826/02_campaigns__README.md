# 02_campaigns — the primary data

Per-unit scored records for all four campaigns. **This is what almost every number in
the paper is computed from.** Field-by-field definitions are in
`00_docs/DATA_DICTIONARY.md`.

Each `event_results*.json` is a JSON array of 90 objects — 30 events × 3 conditions ×
1 repeat. Four campaigns → **360 units** in total.

## What is in each model directory

| File | Evaluator | Model | Schema enforced? |
|---|---|---|---|
| `event_results.json` | **J** (primary) | DeepSeek-R1-Distill-Qwen-14B, local vLLM | **No** — silently disabled |
| `event_results_evaluatorB_openrouter.json` | **A**, read 1 | `deepseek/deepseek-v4-flash-0731` | Yes |
| `event_results_evaluatorA_repeat1.json` | **A**, read 2 | same | Yes |
| `event_results_evaluatorA_repeat2.json` | **A**, read 3 | same | Yes |
| `event_results_evaluatorA_repeat3.json` | **A**, read 4 | same | Yes |
| `event_results_evaluatorC_gptlunapro.json` | **C** | `openai/gpt-5.6-luna-pro` | Yes |
| `summary.json` | — | campaign rollup, computed from `event_results.json` only |
| `reproducibility_analysis.json` | — | this model's cross-evaluator analysis |
| `run_manifest.json` | — | how the campaign was launched, incl. the resolved catalogue path |
| `calibration_curve.png` | — | calibration plot |
| `README.md` | — | this model's own notes and gaps |

> **Never mix numbers across these files.** Different evaluators disagree substantially
> on identical input — that is the paper's central finding, not a nuisance. The passes
> are stored separately precisely so that merging them requires a deliberate act.

## Per-model status

| Model | Events | Evaluator A reads | Evaluator C | Notes |
|---|---|---|---|---|
| `llama-3.1-8b-awq` | 30/30 | 4 | 1 | 23 events hit a silent backend outage; repaired 2026-08-16 after a first, invalid repair. 24 events re-simulated via OpenRouter — a within-row serving-stack change. |
| `mistral-7b-awq` | 30/30 | 4 | 1 | No outage. The clean campaign; used as the reference for several controlled analyses. |
| `qwen2.5_7b` | 30/30 | 4 (3 for 3 units) | 1 | `T3_C_r1`, `C9_A_r1`, `C13_C_r1` unrecoverable in `repeat3`. |
| `qwen2.5-14b-awq` | 30/30 | **3** | 1 | No `evaluatorB` file (no original scorable pass). 6 events re-simulated 2026-08-21 after a wrong-topic bug. `T1_C_r1` unrecoverable in `repeat2`. `C9_C_r1` carries the outage signature and could not be repaired. |

## The four rows that will bite you

These rows exist in their files but are **not genuine reads** — they hold a stale,
never-overwritten copy of an earlier pass's value, because the read failed permanently:

```
Qwen2.5-7B   repeat3.json   T3_C_r1, C9_A_r1, C13_C_r1
Qwen2.5-14B  repeat2.json   T1_C_r1
```

Counting them as extra reads deflates instrument spread and skews the robust mean.
`build_reproducibility_analysis.py` excludes them explicitly by `(file, unit)` pair in
its `KNOWN_GAPS`. **Any analysis you write over the repeat files must do the same.**

## Instrument mixing inside `event_results.json`

Two sets of rows in the "primary" file were **not** scored by Evaluator J:

- Llama's 24 repaired events (scored by `deepseek/deepseek-r1` in August — those events
  did not exist in July, so no J reading is possible);
- Qwen2.5-14B's 18 recovered rows (same substitute evaluator).

The file is therefore instrument-mixed for those rows. This is why the paper reports
Llama's lift and susceptibility on an *instrument-consistent* basis in a separate table,
and why the J-versus-A comparison is restricted to the 198-unit paired scope where both
evaluators read byte-identical text. See `00_docs/DATA_DICTIONARY.md` §7.

## The single biggest caveat

**Condition A is one shared record, not a per-model baseline.** It was run once and
reused across all four campaigns; its `evidence_text` hashes identically across all four
on 30/30 events. Every `A → B` comparison inherits this. The paper is explicit that
re-running Condition A per model is the highest-value next experiment — it would convert
a demonstrated *signal* into a demonstrated *benefit*.
