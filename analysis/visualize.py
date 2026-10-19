#!/usr/bin/env python3
"""Part 2 Task 11 - two Matplotlib charts built from the raw CSVs.

Run after (or independently of) clean_and_eda.py:
    python analysis/visualize.py
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_and_eda import REPO_ROOT, build_clean_dataset, monthly_revenue  # noqa: E402

OUT_DIR = REPO_ROOT / "visualizations"


def main() -> None:
    # Rebuild the cleaned frame from raw CSVs (silence the task printouts).
    with contextlib.redirect_stdout(io.StringIO()):
        merged = build_clean_dataset()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Return rate by payment method, descending
    rates = (merged.groupby("payment_method")["returned"].mean() * 100).sort_values(ascending=False)
    cod, card = rates["COD"], rates["CARD"]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(rates.index, rates.values, color=["#C0392B", "#7F8C8D", "#7F8C8D"])
    for bar, val in zip(bars, rates.values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1, f"{val:.1f}%",
                ha="center", fontweight="bold")
    ax.set_title(f"COD Returns at {cod:.1f}% - {cod / card:.0f}x Card", fontweight="bold")
    ax.set_xlabel("Payment method")
    ax.set_ylabel("Return rate (%)")
    ax.set_ylim(0, rates.max() * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "return_rate_by_payment.png", dpi=150)
    plt.close(fig)

    # 2) Outlier-corrected monthly revenue
    monthly = monthly_revenue(merged, exclude_outliers=True)
    labels = [str(p) for p in monthly.index]
    peak = monthly.idxmax()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(labels, monthly.values, marker="o", linewidth=2, color="#2E86AB")
    for x, y in zip(labels, monthly.values):
        ax.annotate(f"Rs {y:,.0f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center")
    ax.set_title(f"Outlier-Corrected Monthly Revenue - Peak in {peak.strftime('%B %Y')}",
                 fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Order value (Rs, after discount)")
    ax.set_ylim(0, monthly.max() * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "monthly_revenue_trend.png", dpi=150)
    plt.close(fig)

    print("Saved:", OUT_DIR / "return_rate_by_payment.png")
    print("Saved:", OUT_DIR / "monthly_revenue_trend.png")


if __name__ == "__main__":
    main()
