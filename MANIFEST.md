# Publication package inventory

Package 1.2.3; research analysis versions 2026-09-06 / 2026-09-06-full.

Counts exclude this generated inventory and `checksums.sha256`.
Raw traces are separate; see `03_traces/TRACE_MANIFEST.json`.

| Directory | Files | Bytes |
|---|---:|---:|
| (root) | 6 | 17795 |
| .github | 1 | 503 |
| 00_docs | 11 | 40633 |
| 01_benchmark | 97 | 385051 |
| 02_campaigns | 42 | 28923005 |
| 03_traces | 2 | 368212 |
| 04_experiments | 37 | 11229697 |
| 05_analysis | 25 | 746974 |
| 06_figures | 32 | 4810031 |
| 07_pipeline | 99 | 1876787 |
| 08_paper | 18 | 6064833 |
| 09_audit | 288 | 97336391 |
| tools | 5 | 17286 |

All publication files, including this manifest and dotfiles, are hashed in
`checksums.sha256`. The checksum file itself, runtime caches, extracted
companion traces and paper build intermediates are excluded.
Run `python tools/verify_release.py` for complete validation.

Five credential redactions are recorded in `00_docs/PUBLICATION_CHANGES.json`.
Scored observations and current numerical analysis sources are unchanged.
