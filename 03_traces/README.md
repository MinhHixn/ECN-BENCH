# Available raw simulation artifacts

This directory retains available simulation databases, logs, action records and configuration files. Coverage is incomplete: Qwen2.5-14B original raw traces are absent for 21 events following cluster scratch-storage deletion. Recovery traces and the surviving original C15 fragment remain.

The revised paper reads frozen `evidence_text` from scored campaign records, not a newly reconstructed digest. These evidence fields can survive when raw simulation traces do not. They are not full historical HTTP requests.

Llama's recovered executions and Qwen2.5-14B's recovered events must not be confused with the original July executions. Directory-specific filenames and the archived prior documentation preserve the execution history. Status flags alone are insufficient proof of healthy simulation.

The source-level and scoring audit does not validate a simulation as a model of real human populations or establish that 300 configured agents contributed independent evidence.
# Companion archive for the GitHub package

The GitHub folder contains this guide and `TRACE_MANIFEST.json`. The 1,861 raw
trace files are packaged separately as `ECN-BENCH-traces-2026-09-08.zip`.
Every member was streamed from the finished ZIP and its SHA-256 compared to
the source. The manifest records file sizes, hashes and the ZIP checksum.
No public download URL has been assigned yet.

The ZIP contains paths starting with `03_traces/`; extract it at the repository
root when raw traces are needed. These payloads are ignored by Git to avoid
accidentally adding them to source history. The current offline reanalysis uses
stored scored records and does not require this ZIP. Historical trace coverage
limitations below remain unchanged.

