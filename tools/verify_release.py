"""Verify the frozen publication package without model calls or network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(rb"sk-[a-zA-Z0-9_-]{20,}|gh[pousr]_[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def files():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "_workspace", "_verification"} for part in rel.parts):
            continue
        if p.suffix == ".pyc" or (rel.parts[0] == "08_paper" and p.suffix in {".log", ".aux", ".out", ".xdv", ".gz"}):
            continue
        if rel.parts[0] == "03_traces" and rel.as_posix() not in {"03_traces/README.md", "03_traces/TRACE_MANIFEST.json"}:
            continue
        if rel.as_posix() != "checksums.sha256":
            yield p


def run(args, env):
    completed = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, text=True, capture_output=True)
    if completed.returncode:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {args[0]}")
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrity-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"python": sys.version.split()[0], "integrity": "pending", "secret_scan": "pending", "reanalysis": "not run"}
    expected = {}
    for line in (ROOT / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        checksum, name = line.split("  ", 1)
        if name in expected or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Invalid or duplicate checksum entry")
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            raise ValueError(f"Missing or unsafe checksum path: {name}")
        expected[name] = checksum
    actual = {p.relative_to(ROOT).as_posix(): p for p in files()}
    if set(expected) != set(actual):
        raise ValueError(f"Manifest coverage differs: {sorted(set(expected) ^ set(actual))}")
    for name, path in actual.items():
        if digest(path) != expected[name]:
            raise ValueError(f"Checksum mismatch: {name}")
        if SECRET.search(path.read_bytes()):
            raise ValueError(f"Potential credential in {name}; value suppressed")
    report.update(integrity="passed", secret_scan="passed", files_verified=len(actual))
    for filename in ("paper_results.json", "paper_full_results.json"):
        saved = json.loads((ROOT / "08_paper" / filename).read_text(encoding="utf-8"))
        for name, checksum in saved["input_sha256"].items():
            if digest(ROOT / name) != checksum:
                raise ValueError(f"Analysis input changed: {name}")
    report["analysis_input_hashes"] = "passed"
    if not args.integrity_only:
        import numpy
        import matplotlib
        report.update(numpy=numpy.__version__, matplotlib=matplotlib.__version__)
        with tempfile.TemporaryDirectory(prefix="ecnbench-verify-") as temporary:
            output = Path(temporary)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLCONFIGDIR=str(output / "matplotlib"))
            tests = run(["-m", "unittest", "discover", "-s", "05_analysis/tests", "-v"], env)
            count = re.search(r"Ran (\d+) tests", tests.stderr)
            report["tests_passed"] = int(count.group(1)) if count else "passed"
            for script in ("paper_analysis.py", "paper_full_analysis.py"):
                run([f"05_analysis/scripts/{script}", "--data-root", str(ROOT), "--output-dir", str(output)], env)
            for name in ("paper_results.json", "paper_full_results.json"):
                generated = json.loads((output / name).read_text(encoding="utf-8"))
                for directory in ("08_paper", "05_analysis/outputs"):
                    saved = json.loads((ROOT / directory / name).read_text(encoding="utf-8"))
                    if generated != saved:
                        raise ValueError(f"Regenerated JSON differs: {directory}/{name}")
            for name in ("paper_tables.tex", "paper_full_tables.tex"):
                for directory in ("08_paper", "05_analysis/outputs"):
                    if (output / name).read_bytes().replace(b"\r\n", b"\n") != (ROOT / directory / name).read_bytes().replace(b"\r\n", b"\n"):
                        raise ValueError(f"Regenerated table differs: {directory}/{name}")
            report["reanalysis"] = "passed: both JSON outputs and both TeX tables match both released copies"
            report["figure_byte_identity"] = digest(output / "fig_paper_audit.png") == digest(ROOT / "08_paper/fig_paper_audit.png")
    # A final pass catches accidental source mutation during tests/reanalysis.
    for name, path in actual.items():
        if digest(path) != expected[name]:
            raise ValueError(f"Release changed during verification: {name}")
    print(json.dumps(report, indent=2))
    if args.report:
        target = args.report.resolve()
        if target.is_relative_to(ROOT) and "_verification" not in target.relative_to(ROOT).parts:
            raise ValueError("Write the report outside the frozen package or under _verification/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
