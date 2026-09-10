# Final technical freeze review — 2026-09-08

Scientific scope: the restored 2026-09-06 full technical report and its retrospective
measurement audit. Package version: 1.2.2. No simulation, evaluator call, model
download or HPC job was performed for this metadata revision. A later 2026-09-10
audit found that `v1.2.1` points to `689c9f1`, a descendant of `v1.2.2` at
`197f087`; use the full current commit SHA rather than inferring chronology from
those tag numbers.

## Findings and fixes

The original checksum manifest matched its listed files; its human-readable
inventory still described the August release. The publication copy has a fresh
inventory and complete checksums, including dotfiles and publication documentation.

Five historical helpers contained a non-placeholder API-key-shaped literal.
The publication copy removes these values; paths and file-level hashes are listed
in `PUBLICATION_CHANGES.json`. Values are never included in the review. Original
research files remain untouched outside this package. Known-pattern scans cannot
prove the absence of every possible secret or personal identifier.

The local backend declares AGPL-3.0. Its existing upstream LICENSE is now included
alongside the backend and historical source snapshots, with a provenance notice.
The full application and exact historical upstream commit are not reconstructed.

Available raw traces are provided separately with per-file checksums. Scored
observations, injected inputs, historical figures and current analysis source
were preserved byte-for-byte. Historical scripts and outputs remain marked as
historical; their old claims are not promoted to current results.

## Numerical verification

- 12/12 regression and integration tests passed in the prepared package.
- Both analyses ran again from the package's own inputs, with Python 3.14.2,
  NumPy 2.3.5 and Matplotlib 3.10.8.
- Both regenerated JSON documents exactly match the parsed released results in
  `08_paper/` and `05_analysis/outputs/`; both generated TeX tables match their
  released bytes. The regenerated audit figure also matches byte-for-byte in
  this local environment.
- Recorded input SHA-256 hashes match; verification checks publication hashes
  again after reanalysis to detect accidental mutation.
- The 360 stored units remain present. The known three T1 question mismatches
  remain explicit; the 29-event aligned and 20-event primary scopes are unchanged.

The independent audit of scientific scope is limited to internal consistency,
code, stored evidence and manuscript agreement. This review did not independently
adjudicate all 30 real-world outcomes or verify every bibliography entry online.
It is not peer review, and the technical checks do not establish causal claims,
contamination freedom or full historical system reproducibility.

## Manuscript builds

All three PDFs were rebuilt with local Tectonic 0.17.0 using only its existing
package cache: full report 78 pages, short report 10 pages, conference wrapper
8 pages. No missing references,
multiply defined labels, blank pages or overfull boxes were found. The logs retain
font-substitution warnings and underfull-box spacing warnings (3 / 1 / 26),
particularly in the conference layout; these are documented rather than hidden.

## Publication status

The prepared package supports a technical freeze of this existing research scope.
The repository is private and access-controlled; any public release still depends
on the owner's rights review and visibility choice, described in
`GITHUB_PUBLISH.md`. No DOI is asserted.
The two short paper variants are not venue-specific submission compliance checks.

Build and verification evidence is in the sibling local `verification/` directory;
the compact published evidence summary is `FREEZE_EVIDENCE.json`.
