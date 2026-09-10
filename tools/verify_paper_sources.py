"""Offline consistency checks for this archive's manuscript sources.

This deliberately handles the static input/citation syntax used by these files;
it is not a general TeX parser or bibliographic fact-checker. Actual typesetting
and figure resolution are additionally checked by prepare_arxiv.py.
"""
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "08_paper"


def expanded(path, seen=None):
    seen = set() if seen is None else seen
    if path in seen:
        raise ValueError(f"Recursive or repeated TeX input: {path.name}")
    seen.add(path)
    source = path.read_text(encoding="utf-8")
    # Ignore comments, preserving escaped percent signs.
    source = re.sub(r"(?<!\\)%[^\n]*", "", source)
    for name in re.findall(r"\\input\{([^}]+)\}", source):
        if Path(name).name != name:
            raise ValueError(f"Unexpected nonlocal input: {name}")
        target = PAPER / (name if Path(name).suffix else name + ".tex")
        source += "\n" + expanded(target, seen)
    return source


def verify():
    bibliography = (PAPER / "references.bib").read_text(encoding="utf-8")
    keys = re.findall(r"(?m)^@\w+\{([^,]+),", bibliography)
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate bibliography keys: {duplicates}")
    report = {"bibliography_entries": len(keys), "manuscripts": {}}
    for filename in ("ecn_bench_paper.tex", "ecn_bench_paper_short.tex", "ecn_bench_paper_conf.tex"):
        source = expanded(PAPER / filename)
        citations = {key.strip() for group in re.findall(r"\\cite(?:\[[^]]*\])*\{([^}]+)\}", source)
                     for key in group.split(",")}
        missing = citations - set(keys)
        if missing:
            raise ValueError(f"Unresolved citations in {filename}: {sorted(missing)}")
        labels = re.findall(r"\\label\{([^}]+)\}", source)
        if len(labels) != len(set(labels)):
            raise ValueError(f"Duplicate labels in {filename}")
        if filename == "ecn_bench_paper.tex" and set(keys) != citations:
            raise ValueError(f"Unused full-report references: {sorted(set(keys) - citations)}")
        report["manuscripts"][filename] = {"citations": len(citations), "labels": len(labels)}
    metadata = (ROOT / "00_docs/ARXIV_METADATA.md").read_text(encoding="utf-8")
    abstract = metadata.split("## Abstract\n", 1)[1].split("\n## ", 1)[0].strip()
    if not abstract.isascii() or len(abstract) > 1920:
        raise ValueError(f"arXiv form abstract must be ASCII and <=1920 characters; got {len(abstract)}")
    report["arxiv_abstract_characters"] = len(abstract)
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
