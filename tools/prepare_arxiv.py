"""Build a minimal arXiv source ZIP, then compile a fresh extraction offline.

Requires Tectonic on PATH with its TeX bundle already cached. This is a local
XeTeX smoke test, not a claim that arXiv's TeX Live build has been tested.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAIN = "ecn_bench_paper"
SOURCES = [f"{MAIN}.tex", "paper_tables.tex", "paper_full_tables.tex",
           "paper_full_technical.tex", "paper_historical_figures.tex",
           "references.bib", "fig_paper_audit.png"]


def build(directory):
    run = subprocess.run(["tectonic", "--only-cached", "--keep-logs",
                          "--keep-intermediates", f"{MAIN}.tex"],
                         cwd=directory, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    log = (directory / f"{MAIN}.log").read_text(encoding="utf-8", errors="replace")
    failures = [line for line in log.splitlines() if re.search(
        r"undefined|multiply defined|Overfull|Missing character|Font Warning", line)]
    if failures:
        raise RuntimeError("Review TeX warnings before packaging:\n" + "\n".join(failures))
    return [line for line in log.splitlines() if "Underfull" in line]


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "ECN-BENCH-arxiv-1.2.3.zip"
    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite existing submission artifact: {archive}")
    # Keep build evidence in a unique directory; no destructive cleanup required.
    stage = Path(tempfile.mkdtemp(prefix="arxiv-build-", dir=output))
    for name in SOURCES:
        shutil.copy2(ROOT / "08_paper" / name, stage / name)
    figure_names = re.findall(r"\\HistoricalFigureRoot/([^}]+)",
                             (stage / "paper_historical_figures.tex").read_text(encoding="utf-8"))
    (stage / "figures").mkdir()
    for name in sorted(set(figure_names)):
        if Path(name).name != name:
            raise ValueError(f"Unsafe figure path: {name}")
        shutil.copy2(ROOT / "06_figures" / name, stage / "figures" / name)
    warnings = build(stage)
    included = SOURCES + [f"{MAIN}.bbl"] + [f"figures/{n}" for n in sorted(set(figure_names))]
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as handle:
        for name in included:
            handle.write(stage / name, name)
    extracted = Path(tempfile.mkdtemp(prefix="arxiv-roundtrip-", dir=output))
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(extracted)
    build(extracted)
    preview = output / "ECN-BENCH-arxiv-1.2.3-preview.pdf"
    shutil.copy2(extracted / f"{MAIN}.pdf", preview)
    report = {"source_zip": archive.name, "sha256": sha256(archive),
              "bytes": archive.stat().st_size, "files": len(included),
              "historical_figures": len(set(figure_names)),
              "main": f"{MAIN}.tex", "local_engine": "Tectonic (XeTeX)",
              "arxiv_engine_to_select": "XeLaTeX",
              "fresh_extraction_offline_build": "passed",
              "arxiv_server_build": "not tested; author must review server-generated PDF",
              "nonfatal_underfull_boxes": warnings,
              "members": {name: sha256(stage / name) for name in included}}
    (output / "ECN-BENCH-arxiv-1.2.3-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "members"}, indent=2))


if __name__ == "__main__":
    main()
