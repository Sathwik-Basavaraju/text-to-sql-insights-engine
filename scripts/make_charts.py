"""Charts for the text-to-SQL evaluator (matplotlib, optional)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping charts")
        return
    metrics = json.loads((ROOT / "outputs" / "metrics.json").read_text())
    tiers = ["easy", "medium", "hard"]
    v1 = [metrics["iteration_1_baseline_v1"]["by_tier"][t]["accuracy"] for t in tiers]
    v2 = [metrics["iteration_2_improved_v2"]["by_tier"][t]["accuracy"] for t in tiers]
    outdir = ROOT / "outputs" / "charts"
    outdir.mkdir(parents=True, exist_ok=True)
    x = range(len(tiers))
    fig, ax = plt.subplots()
    ax.bar([i - 0.2 for i in x], v1, width=0.4, label="Iteration 1 (baseline)")
    ax.bar([i + 0.2 for i in x], v2, width=0.4, label="Iteration 2 (improved)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(tiers)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Execution-match accuracy")
    ax.legend()
    ax.set_title("Text-to-SQL accuracy by tier (24 gold questions)")
    fig.tight_layout()
    fig.savefig(outdir / "accuracy_by_tier.png", dpi=150)
    print(f"Wrote {outdir / 'accuracy_by_tier.png'}")


if __name__ == "__main__":
    main()
