"""Deliberately refresh inventory/checksums after reviewed publication edits."""
import argparse
import json

from verify_release import ROOT, digest, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acknowledge-changes", action="store_true", required=True,
                        help="Confirm that changes since the previous freeze were reviewed")
    parser.parse_args()
    for name in ("paper_results.json", "paper_full_results.json"):
        result = json.loads((ROOT / "08_paper" / name).read_text(encoding="utf-8"))
        for path, checksum in result["input_sha256"].items():
            if digest(ROOT / path) != checksum:
                raise ValueError(f"Frozen research input changed; stop and review the scientific version: {path}")
    groups = {}
    for path in files():
        if path.name == "MANIFEST.md":
            continue
        relative = path.relative_to(ROOT)
        name = relative.parts[0] if len(relative.parts) > 1 else "(root)"
        count, size = groups.get(name, (0, 0))
        groups[name] = count + 1, size + path.stat().st_size
    lines = ["# Publication package inventory", "", "Package 1.2.2; research analysis versions 2026-09-06 / 2026-09-06-full.", "",
             "Counts exclude this generated inventory and `checksums.sha256`.",
             "Raw traces are separate; see `03_traces/TRACE_MANIFEST.json`.", "",
             "| Directory | Files | Bytes |", "|---|---:|---:|"]
    lines += [f"| {name} | {count} | {size} |" for name, (count, size) in sorted(groups.items())]
    lines += ["", "All publication files, including this manifest and dotfiles, are hashed in",
              "`checksums.sha256`. The checksum file itself, runtime caches, extracted",
              "companion traces and paper build intermediates are excluded.",
              "Run `python tools/verify_release.py` for complete validation.", "",
              "Five credential redactions are recorded in `00_docs/PUBLICATION_CHANGES.json`.",
              "Scored observations and current numerical analysis sources are unchanged.", ""]
    (ROOT / "MANIFEST.md").write_bytes("\n".join(lines).encode("utf-8"))
    listed = list(files())
    (ROOT / "checksums.sha256").write_bytes("".join(
        f"{digest(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in listed).encode("utf-8"))
    print(f"Updated manifest and checksums for {len(listed)} files. Run verification before publication.")


if __name__ == "__main__":
    main()
