"""Package exactly the checksum-covered release files, without Git history."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from verify_release import ROOT, digest, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Keep release artifacts outside the checksum-covered repository")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    subprocess.run([sys.executable, str(ROOT / "tools/verify_release.py"), "--integrity-only"], check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    included = [*files(), ROOT / "checksums.sha256"]
    expected = {"ECN-BENCH/" + p.relative_to(ROOT).as_posix(): digest(p) for p in included}
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            archive.write(path, "ECN-BENCH/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        if set(archive.namelist()) != set(expected):
            raise ValueError("Archive membership mismatch")
        for name, checksum in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                raise ValueError(f"Archived file differs: {name}")
    report = {"artifact": output.name, "sha256": digest(output),
              "bytes": output.stat().st_size, "files": len(included),
              "archive_member_hashes": "passed",
              "scope": "sanitized release; excludes Git history and companion raw traces"}
    output.with_suffix(".validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
