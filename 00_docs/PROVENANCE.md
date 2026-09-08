# Current provenance and claim boundaries

Revision: 2026-09-06. No new simulation or evaluator calls were made for this revision. The prior narrative is preserved under `09_audit/manuscript_20260826.tex`; previous documentation is under `09_audit/docs_20260826/`.

## Observation versus interpretation

The fixed-evidence J/A comparison uses 60 Mistral B/C units, 60 Qwen2.5-7B B/C units and 12 Llama B/C units from unaffected events C3 and S2–S6. Evidence text, question, options and outcome metadata match within all 132 pairs. Counts are 31 versus one at tolerance 0.005, unchanged at exact numerical uniformity or 0.01; at 0.02 they are 32 versus one.

This demonstrates sensitivity to the historical extraction configurations. It does not prove an architecture-specific cause, evaluator correctness, a reasoning deficit or a beneficial schema intervention. Complete request bytes, raw completions, backend identities and retry histories are not consistently available.

## Defects and treatment

| Defect | Current treatment |
|---|---|
| Shared Condition A | No per-model direct-reference lift claim |
| Llama outage and defective initial recovery | Only six unaffected events in J/A comparison; final recovered observations retained for exploratory analyses |
| Qwen2.5-14B wrong-topic simulations | Use previously repaired records; no J/A primary comparison for this campaign |
| Remaining Qwen2.5-14B T1 question collision | All A/B/C primary questions concern the Fed rather than the UAW question; options/outcome coincide. Retain stored rows, exclude T1 across campaigns from extended aligned aggregates. T1 is absent from the main 20-event subset. |
| Wrong-topic injection IDs C6, T1, T3, T4, T5, T6, T8 | Preserve inputs; B is nominally relevant; exclude C6/T6/T8 in the post-release input sensitivity |
| Qwen2.5-14B C9/C outage-like telemetry | Report full-set descriptive estimates and a sensitivity excluding C9 across all campaigns |
| Four stale evaluator rereads | Exclude the file–unit pairs below |
| Schema bypass and silent default handling | Report as source-level defects; no claim that constraints guarantee informative or faithful probabilities |
| Missing Qwen2.5-14B raw traces | 21 original events lack raw traces; scored evidence records survive |
| Convergence/rubric/persona validity | Not retained as validated behavioural or psychological findings |

Stale rereads:
- Qwen2.5-7B, evaluator A repeat 3: T3_C_r1, C9_A_r1, C13_C_r1.
- Qwen2.5-14B, evaluator A repeat 2: T1_C_r1.

`event_results.json` is instrument-mixed for Llama and Qwen2.5-14B recoveries. Recovered primary rows use recorded `deepseek/deepseek-r1`, not the original local DeepSeek-R1-Distill-Qwen-14B deployment.

Evaluator A's four files (three for Qwen2.5-14B) are repeated requests, not new simulations. Evaluator C has one read. JSON-object handling must not be described as verified strict-schema enforcement. The hosted model identifiers are recorded identifiers, not guarantees of provider continuity.

## Forecasting interpretation

The 20-event subset is selected by campaign-model release dates. It does not rule out later evaluator knowledge or hindsight in the assembled dossiers and perturbations. The injection bodies are not length-matched: relevant/null body character ratios are 1.51–2.37, median 2.04. The same null body is reused.

Current event-cluster intervals are generated in `paper_results.json`. Both evaluator A aggregation choices, evaluator C, input/gap exclusion, US-election grouping and US-election omission are reported. These are retrospective sensitivities, not preregistered or multiplicity-adjusted tests. No pooled independent-unit Poisson-binomial claim is retained.

A B/C difference is a whole-pipeline input contrast. It cannot identify the additional contribution of agent-to-agent deliberation without matched single-agent B/C arms. Existing CoT data do not establish equivalence, non-inferiority or a swarm advantage.

## Authority

The restored full edition distinguishes current vector-derived results, design specifications, historical scan summaries and superseded figures. The seven-dimensional rubric and scaling rationale are restored as detailed technical material, not as validated behavioral constructs or a proven optimum. All 30 old figures are reproduced with explicit corrected interpretations. Their embedded old p-values and claims remain withdrawn.

`paper_full_analysis.py` checks cross-campaign question identity as well as within-unit evaluator inputs. It records the known T1 mismatch and fails on unexpected question mismatches. Its extended summaries use 29 question-aligned events, which is not a claim that those events are free of leakage, input defects or execution failures.

Source-level claims are inspectable in `07_pipeline/backend/app/utils/llm_client.py` (`chat_json` and its async counterpart) and `07_pipeline/backend/app/benchmarks/evaluator.py` (micro-question mapping and validation). The older deployment's actual uniform-fallback implementation is retained in `09_audit/source_snapshots/hpc_evaluator.py`, with its origin and hash documented alongside it. The newer pipeline snapshot rejects non-positive matched probability mass; do not conflate these versions or infer a verified runtime history from either snapshot.

The frozen scored observations remain unchanged. `05_analysis/scripts/paper_analysis.py` recomputes the current results and records input SHA-256 hashes. Older outputs, including `reproducibility_analysis_master.json`, are historical summaries, not the authority for the revised manuscript.
