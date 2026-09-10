# Changes

## 1.2.3 — reference and provenance correction, 2026-09-10

- Centralized the manuscripts' references in `08_paper/references.bib` and added
  primary citations for model families, confidence elicitation, social-simulation
  validity, statistical methods, OASIS and MiroFish-Offline.
- Replaced outdated arXiv-only records where archival conference publications
  are available.
- Corrected the implementation description to match the archived custom
  Neo4j-backed retrieval code; the release does not contain Graphiti or Infinity.
- Recorded the non-monotonic existing tag mapping. No tag was rewritten.
  `689c9f11ede54830b5fad7f0f12e8d0fca7a7e12` identifies the pre-correction
  repository, not this corrected paper; cite the new target commit after release.
- Corrected Zhou and Sharma author lists, expanded software/model attribution
  to 47 references, and removed an unverified public-upstream commit claim.
- Added standalone arXiv source packaging, a fresh-extraction offline build
  check, explicit XeTeX fonts and a submission-readiness checklist.

## 1.2.2 — author and repository metadata, 2026-09-08

- Identified Minh Hien NGUYEN as primary and corresponding author, with the
  confirmed Sorbonne Université affiliation, programme, student number and
  academic email address.
- Acknowledged Hugues DIGONNET (Centrale Nantes / GeM) as academic supervisor;
  this acknowledgment does not confer co-authorship.
- Added the private GitHub repository, `main` branch and prior `v1.2.1` freeze
  metadata to the paper, citation file and documentation.
- Rebuilt and revalidated all three PDFs. No scientific result or input changed.

## 1.2.1 — publication preparation, 2026-09-08

- Prepared a dedicated GitHub folder and separate verified raw-trace archive.
- Removed embedded API credentials from five historical helpers, recording changes.
- Included the existing backend/source-snapshot AGPL license and attribution.
- Added a portable offline verifier, GitHub verification workflow, byte-preserving
  Git attributes, fresh inventory, checksums and publication instructions.
- Rechecked deterministic analyses, source integrity and manuscript builds.
- Preserved the 2026-09-06 scientific results and all documented limitations.

No model observations were added and no public deposition was performed.
