"""Regenerate revised exploratory forecasts; no model calls."""
import json

from paper_analysis import main


if __name__ == "__main__":
    result, output = main()
    payload = {
        "analysis_version": result["analysis_version"],
        "inference": result["inference"],
        "forecast": result["forecast"],
        "sensitivity": result["sensitivity"],
    }
    (output / "predictive_signal_analysis.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")

