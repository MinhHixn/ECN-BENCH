"""Reanalyse the existing paired grid; no evaluator requests."""
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_analysis" / "scripts"))

from paper_analysis import main


if __name__ == "__main__":
    result, output = main()
    payload = {
        "analysis_version": result["analysis_version"],
        "inference": result["inference"],
        **result["truncation"],
    }
    (output / "truncation_results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")

