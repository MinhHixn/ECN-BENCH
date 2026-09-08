# Historical deployment source snapshots

These two files are byte-preserving copies taken during the September 2026 audit from the existing `ECN-HPC-DEPLOY/MiroFish-Offline/backend/app/` tree: `benchmarks/evaluator.py` and `utils/llm_client.py`. They were not executed or modified for this revision. Inclusion does not prove which snapshot served each historical request.

`hpc_evaluator.py`, function `_normalize_probabilities`, implements the silent uniform fallback for non-positive matched probability mass. Its SHA-256 is `b5deee744b0f2039ece85b3742e8c6916abce3c51cc237d3f26164e104995ed4`. The newer `07_pipeline/backend/app/benchmarks/evaluator.py` instead rejects that case. The two versions must not be treated as identical runtime code.

The schema bypass is inspectable in `hpc_llm_client.py` and the newer `07_pipeline/backend/app/utils/llm_client.py`; policies differ across snapshots. This is source-level evidence, not a reconstruction of complete July request logs. Existing source license terms continue to apply.
