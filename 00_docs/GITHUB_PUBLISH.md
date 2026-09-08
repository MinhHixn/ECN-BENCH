# Publish the prepared research package

Use the **ECN-BENCH directory containing this document**, not the original
Claw-4-FUN workspace or ECNBENCH-RELEASE archive. The original archive still
contains credentials in historical scripts. Only the prepared copy was sanitized.

## Validate locally

Run from the ECN-BENCH repository root:

```sh
python -m pip install -r 05_analysis/requirements-analysis.txt
python tools/verify_release.py
```

This verifies complete checksum coverage, scans known credential patterns,
checks every recorded analysis-input hash, runs 12 tests and regenerates both
analyses into a temporary directory. It compares both JSON outputs and both
TeX tables with the released copies. It never calls models or HPC services.
`--integrity-only` runs the standard-library checks without NumPy/Matplotlib.

The GitHub workflow runs the same numerical checks after a push or pull request.
Its first hosted execution is still pending. Python/package installation requires
network access; the research analyses are offline.

## Final owner decisions

- Author metadata is confirmed as Minh Hien NGUYEN, student no. 21618468,
  L2 EEA (Bi-disciplinaire) / minor in Mechanics, Faculté des Sciences et
  Ingénierie, Sorbonne Université; academic contact email
  `nguyen.minh_hien@etu.sorbonne-universite.fr`.
- Review distribution rights for the quoted news material and historical artifacts.
  Existing license notices and upstream AGPL text are included; this technical
  freeze is not a rights clearance.
- Revoke/rotate the credential found in the five original scripts if it is real
  and active. No API request was made to test its validity.
- The repository is `MinhHixn/ECN-BENCH`, private, with `main` as its principal
  branch. Decide separately whether to make it public. A DOI is optional for
  GitHub; never insert a placeholder DOI as though deposited.

## Update the existing repository

The repository and local `origin` already exist. After reviewing the metadata
change, commit and push from this package root. Do not move the existing
`v1.2.1` tag: it identifies commit `ec161cef73f79758b85bf91fd7cc89e9908c9697`.

```sh
git add .
git diff --cached --stat
git status --short
git commit -m "Add author, supervisor, and repository metadata"
git tag v1.2.2
git push origin main
git push origin v1.2.2
```

The configured remote is `https://github.com/MinhHixn/ECN-BENCH.git`.
`.gitattributes` preserves source bytes across platforms so input hashes survive
cloning.

## Companion artifact and version

The sibling `artifacts/` folder contains the separate raw-trace ZIP and a ZIP of
the GitHub folder. Keep these ZIPs outside Git history. The raw-trace archive is
optional for offline numerical reproduction but is needed to distribute all
available transcripts. Attach it to a repository release or deposit it separately
after the owner review. Record the real URL in `03_traces/TRACE_MANIFEST.json`.

The package version is 1.2.2; scientific analysis versions remain 2026-09-06 and
2026-09-06-full. Tag `v1.2.1` remains the initial freeze; tag `v1.2.2` should
identify this metadata-only revision after verification.

Every edit changes the frozen checksums. Regenerate `checksums.sha256` deliberately
after final metadata edits, then rerun verification and rebuild the publication
ZIP. Never silently refresh hashes to hide changes to scored source observations.

```sh
python tools/update_checksums.py --acknowledge-changes
python tools/verify_release.py
```

The refresh command refuses to proceed if inputs recorded in the released analyses
no longer match their original hashes. Numerical/scientific changes require a new
review and version, not just a metadata refresh.
