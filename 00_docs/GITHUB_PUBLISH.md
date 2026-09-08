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

- Confirm the existing author name, affiliation, contact email and acknowledgments.
- Review distribution rights for the quoted news material and historical artifacts.
  Existing license notices and upstream AGPL text are included; this technical
  freeze is not a rights clearance.
- Revoke/rotate the credential found in the five original scripts if it is real
  and active. No API request was made to test its validity.
- Choose the GitHub owner/repository and public/private visibility. Add the actual
  URL to `CITATION.cff` and Data Availability once publication occurs. A DOI is
  optional for GitHub; never insert a placeholder DOI as though deposited.

## Create the repository

Create an empty GitHub repository with your chosen visibility. Do not initialize
it with an extra README/license, because this package already includes them.
Then, from this package root:

```sh
git init -b main
git add .
git diff --cached --stat
git status --short
git commit -m "Freeze ECN-BENCH technical report and reproducible audit"
```

Add the remote using the exact URL shown by GitHub and push `main`. The workspace
preparation does not create a remote, commit on your behalf or publish data.
`.gitattributes` preserves source bytes across platforms so input hashes survive
cloning. Use Git or upload the prepared ZIP; browser drag-and-drop may omit dotfiles
such as `.github`, `.gitignore` and `.gitattributes`.

## Companion artifact and version

The sibling `artifacts/` folder contains the separate raw-trace ZIP and a ZIP of
the GitHub folder. Keep these ZIPs outside Git history. The raw-trace archive is
optional for offline numerical reproduction but is needed to distribute all
available transcripts. Attach it to a repository release or deposit it separately
after the owner review. Record the real URL in `03_traces/TRACE_MANIFEST.json`.

The package version is 1.2.1; scientific analysis versions remain 2026-09-06 and
2026-09-06-full. After the final metadata update and passing hosted checks, a
version tag such as `v1.2.1` can identify the published commit.

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
