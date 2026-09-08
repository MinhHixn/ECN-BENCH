# Data contract for the revised analysis

The frozen campaign JSON files are lists of 90 event–condition records per file. Counts do not imply independent simulations or independent raters. Filenames are mapped explicitly in `paper_analysis.py`.

| Field | Interpretation |
|---|---|
| event_id | Catalogue identifier; do not infer topic from its prefix |
| unit / unit_id | Unit identifier; the loader otherwise builds event_condition_rrepeat |
| condition | A shared reference; B nominally relevant injection; C unrelated injection |
| repeat | Simulation-record replicate identifier, distinct from evaluator file repeats |
| question, options | Forecast question and recorded outcome categories |
| ground_truth | Released outcome label; not independently re-adjudicated in this revision |
| probabilities | Stored normalized vector; contains post-processing as well as model output |
| evidence_text | Stored extractor evidence digest; not the entire simulation or full HTTP request |
| brier, rps, directional_accuracy | Historical derived fields; current metrics are recomputed |
| error, simulation_status, full_simulation_completed | Historical status flags; do not guarantee a healthy run |
| evaluator_fallback_used / reason / source | Partial historical diagnostics; not proof that strict JSON schema was accepted |
| round_jsd and convergence fields | Historical telemetry, potentially placeholders or incomplete |
| mcq_dimensions, validated_scales, micro_epistemic_mapping | Historical rubric/extraction outputs; construct validity is not established |

The analysis validates finite probabilities in [0,1], total mass within 1e-6 of one, exact option-key coverage and ground-truth membership. It rejects incomplete or duplicate campaign unit collections.

Brier is the unnormalised multicategory sum of squared error, bounded in [0,2]. Uniform Brier is 1–1/K. Near-uniform means maximum absolute deviation from 1/K < 0.005; it is an output diagnostic, not an automatic failure label. These units remain in score summaries.

Accuracy assigns 1/h when the truth is among h tied maximal options. A fractional hit total cannot simply be rounded and called an exact Bernoulli-sum test. The current analysis reports no such p-values.

Evaluator A results distinguish scoring the mean probability vector from averaging individual-read scores. The former gains a vector-ensembling term. Evaluator C has one read. Neither is a reference ground truth for what the swarm believed.

Known stale file–unit pairs, shared reference evidence, instrument-mixed primary files, injection mismatches and the C9/C uncertainty are specified in `PROVENANCE.md`. Source observations are retained as recorded. Read the provenance before building another analysis.

Cross-campaign question equality is an additional contract in `paper_full_analysis.py`. Qwen2.5-14B T1 is a known exception: its Fed question has the same options/outcome as the intended UAW question. The exception is explicitly logged, retained in per-record output, and excluded from all 29-event aligned summaries. A matching event ID and valid vector are not enough to establish a valid pairing.
