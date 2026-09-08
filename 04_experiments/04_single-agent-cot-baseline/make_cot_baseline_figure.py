"""Plot revised CoT differences from frozen observations."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_analysis" / "scripts"))

from paper_analysis import estimate_text, main, plt


if __name__ == "__main__":
    result, output = main()
    rows = [(model, arm["variants"]["single"]) for model, arm in result["cot"]["arms"].items()]
    rows.append(("Identity-matched pool", result["cot"]["pooled"]["identity_matched"]))
    figure, axis = plt.subplots(figsize=(9, 4), layout="constrained")
    for position, (label, estimate) in enumerate(rows):
        axis.plot([estimate["low"], estimate["high"]], [position, position], color="#3074aa")
        axis.plot(estimate["mean"], position, "o", color="#3074aa")
        axis.text(estimate["high"] + 0.01, position, estimate_text(estimate),
                  va="center", fontsize=8)
    axis.set_yticks(range(len(rows)), [label for label, _ in rows])
    axis.invert_yaxis()
    axis.axvline(0, linestyle="--", color="gray")
    axis.set_xlim(-0.42, 0.38)
    axis.set_xlabel("Brier: CoT minus simulation (positive favours simulation)")
    axis.set_title("Existing CoT comparison: exploratory event-cluster intervals")
    axis.spines[["top", "right"]].set_visible(False)
    figure.savefig(output / "figM_cot_vs_swarm.png", dpi=220)
    plt.close(figure)

