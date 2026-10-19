#!/usr/bin/env python3
"""Part 2 - Python/Pandas data wrangling & EDA.

Independent pandas pipeline over the raw CSVs in data/ (does NOT read the SQL
database), so Part 1 and Part 2 can be run in either order.

Run:  python analysis/clean_and_eda.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NATURAL_KEY = [
    "customer_id",
    "product_id",
    "order_date",
    "quantity",
    "discount_pct",
    "payment_method",
    "rating",
    "returned",
]
PART1_RAW_TOTAL = 99860.20  # Part 1 Report (a) raw total, in INR

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def strength_band(r: float) -> str:
    a = abs(r)
    if a < 0.2:
        return "negligible"
    if a < 0.4:
        return "weak"
    if a < 0.7:
        return "moderate"
    return "strong"


# --------------------------------------------------------------------------
# Task 1 - Load and inspect
# --------------------------------------------------------------------------
def task1_load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    header("TASK 1 - Load and inspect")
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    print("orders.shape    :", orders.shape)
    print("customers.shape :", customers.shape)
    print("products.shape  :", products.shape)
    print("\norders.head():\n", orders.head())
    print("\norders.dtypes:\n", orders.dtypes)
    print("\nNull counts (raw orders):\n", orders.isnull().sum())
    assert orders.shape == (180, 9), "orders must be (180, 9) before cleaning"
    return orders, customers, products


# --------------------------------------------------------------------------
# Task 2 - Standardize payment_method
# --------------------------------------------------------------------------
def task2_payment(orders: pd.DataFrame) -> pd.DataFrame:
    header("TASK 2 - Standardize payment_method casing")
    raw_values = orders["payment_method"].unique()
    print(f"Before fix: {len(raw_values)} distinct raw values -> {list(raw_values)}")
    orders = orders.copy()
    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    counts = orders["payment_method"].value_counts()
    print(f"After fix : {orders['payment_method'].nunique()} distinct values")
    print(counts.to_string())
    assert len(raw_values) == 7
    assert counts.to_dict() == {"CARD": 70, "UPI": 55, "COD": 55}
    return orders


# --------------------------------------------------------------------------
# Task 3 - Remove duplicate orders
# --------------------------------------------------------------------------
def task3_dedupe(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    header("TASK 3 - Remove duplicate orders")
    dup_mask = orders.duplicated(subset=NATURAL_KEY, keep="first")
    dropped = orders[dup_mask].copy()
    orders_clean = orders[~dup_mask].copy()
    print("Natural key:", NATURAL_KEY)
    print("Duplicate rows flagged:", int(dup_mask.sum()))
    print("Dropped order_ids     :", dropped["order_id"].tolist())
    print("orders_clean.shape    :", orders_clean.shape)
    assert dup_mask.sum() == 5
    assert orders_clean.shape == (175, 9)
    assert dropped["order_id"].tolist() == ["O0176", "O0177", "O0178", "O0179", "O0180"]
    return orders_clean, dropped


# --------------------------------------------------------------------------
# Task 4 - Impute missing values
# --------------------------------------------------------------------------
def task4_impute(orders_clean: pd.DataFrame) -> pd.DataFrame:
    header("TASK 4 - Impute missing values")
    orders_clean = orders_clean.copy()

    n_disc = int(orders_clean["discount_pct"].isnull().sum())
    print(f"discount_pct NaN rows (deduplicated frame): {n_disc} -> filled with 0 "
          "(business rule: no promo code applied)")
    orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)

    n_rating = int(orders_clean["rating"].isnull().sum())
    rating_median = orders_clean["rating"].median()
    print(f"rating median (non-null, deduplicated frame): {rating_median}")
    print(f"rating NaN rows: {n_rating} -> filled with median {rating_median}")
    orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)

    remaining = orders_clean[["discount_pct", "rating"]].isnull().sum().to_dict()
    print("Remaining nulls:", remaining)
    assert n_disc == 12 and n_rating == 15 and rating_median == 3.0
    assert remaining == {"discount_pct": 0, "rating": 0}
    return orders_clean


# --------------------------------------------------------------------------
# Task 5 - Merge and reconcile against Part 1
# --------------------------------------------------------------------------
def order_value(frame: pd.DataFrame) -> pd.Series:
    return frame["quantity"] * frame["price"] * (1 - frame["discount_pct"] / 100)


def task5_merge(orders_clean, dropped, customers, products) -> pd.DataFrame:
    header("TASK 5 - Merge and reconcile against Part 1")
    merged = (
        orders_clean.merge(products, on="product_id", how="left")
        .merge(customers, on="customer_id", how="left")
    )
    merged["order_value"] = order_value(merged)
    total = round(merged["order_value"].sum(), 2)
    print("merged.shape:", merged.shape)
    print(f"Total order_value (175 cleaned rows): {total:.2f}")

    # Independent check: order_value of the 5 dropped duplicates
    dropped_m = dropped.merge(products, on="product_id", how="left")
    dropped_m["discount_pct"] = dropped_m["discount_pct"].fillna(0)
    dropped_m["order_value"] = order_value(dropped_m)
    dropped_total = round(dropped_m["order_value"].sum(), 2)
    delta = round(PART1_RAW_TOTAL - total, 2)
    print("\nDropped duplicate rows and their order_value:")
    print(dropped_m[["order_id", "product_id", "quantity", "price",
                     "discount_pct", "order_value"]].to_string(index=False))
    print(f"Sum of dropped rows' order_value: {dropped_total:.2f}")

    print("\nRECONCILIATION NOTE:")
    print(
        f"Part 2's cleaned total of Rs {total:,.2f} is Rs {delta:,.2f} lower than Part 1 "
        f"Report (a)'s raw total of Rs {PART1_RAW_TOTAL:,.2f}. This entire delta is explained "
        f"by the 5 duplicate rows removed in Task 3 (O0176-O0180): summing their order_value "
        f"independently gives exactly Rs {dropped_total:,.2f}, which matches the gap. The Task 4 "
        f"imputations do not contribute to the difference - filling discount_pct NaN with 0 "
        f"mirrors how Part 1 treats a missing discount (no promo applied), and rating is not "
        f"part of the order_value formula, so neither changes any order_value total."
    )
    assert total == 97358.30
    assert dropped_total == delta == 2501.90
    return merged


# --------------------------------------------------------------------------
# Task 6 - IQR outlier detection on quantity
# --------------------------------------------------------------------------
def task6_outliers(merged: pd.DataFrame) -> pd.DataFrame:
    header("TASK 6 - IQR outlier detection on quantity")
    q1 = merged["quantity"].quantile(0.25)
    q3 = merged["quantity"].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    print(f"Q1 = {q1}, Q3 = {q3}, IQR = {iqr}, lower = {lower}, upper = {upper}")
    merged = merged.copy()
    merged["is_outlier"] = (merged["quantity"] < lower) | (merged["quantity"] > upper)
    outliers = merged[merged["is_outlier"]]
    print(f"Outlier rows: {len(outliers)} (flagged, NOT dropped)")
    print(outliers[["order_id", "order_date", "quantity", "order_value"]].to_string(index=False))
    assert (q1, q3, iqr, lower, upper) == (1.0, 2.0, 1.0, -0.5, 3.5)
    assert outliers["order_id"].tolist() == ["O0011", "O0098"]
    return merged


# --------------------------------------------------------------------------
# Task 7 - Hypothesis: COD has a higher return rate
# --------------------------------------------------------------------------
def task7_cod(merged: pd.DataFrame) -> pd.DataFrame:
    header("TASK 7 - Hypothesis: does COD have a higher return rate?")
    print("Hypothesis: Cash-on-Delivery (COD) orders are returned at a higher rate "
          "than prepaid (CARD / UPI) orders.")
    summary = merged.groupby("payment_method")["returned"].agg(["count", "mean"])
    summary["return_rate_pct"] = (summary["mean"] * 100).round(1)
    print(summary.to_string())
    rates = summary["return_rate_pct"].to_dict()
    assert rates == {"CARD": 14.7, "COD": 44.4, "UPI": 18.9}
    verdict = "Confirmed" if rates["COD"] > max(rates["CARD"], rates["UPI"]) else "Busted"
    print(f"Verdict: {verdict} - COD returns at {rates['COD']}% vs CARD {rates['CARD']}% "
          f"and UPI {rates['UPI']}% (~{rates['COD'] / rates['CARD']:.0f}x Card).")
    return summary


# --------------------------------------------------------------------------
# Task 8 - Multi-level segmentation
# --------------------------------------------------------------------------
def task8_segments(merged: pd.DataFrame) -> None:
    header("TASK 8 - Multi-level segmentation (payment_method x city_tier)")
    seg = merged.groupby(["payment_method", "city_tier"])["returned"].agg(["count", "mean"])
    seg["return_rate_pct"] = (seg["mean"] * 100).round(1)
    print(seg.to_string())
    top = seg["return_rate_pct"].idxmax()
    top_row = seg.loc[top]
    print(f"\nHighest-risk segment: {top[0]} + Tier-{top[1]} cities at "
          f"{top_row['return_rate_pct']}% ({int(top_row['count'])} orders)")
    t1, t2 = seg.loc[("COD", 1)], seg.loc[("COD", 2)]
    print(f"COD risk is NOT uniform: Tier-1 COD = {int(t1['count'])} orders at "
          f"{t1['return_rate_pct']}%, Tier-2 COD = {int(t2['count'])} orders at "
          f"{t2['return_rate_pct']}%. The blended 44.4% COD rate hides that the problem is "
          f"concentrated in Tier-2 cities.")
    assert top == ("COD", 2) and top_row["return_rate_pct"] == 54.5


# --------------------------------------------------------------------------
# Task 9 - Correlation analysis
# --------------------------------------------------------------------------
def task9_correlation(merged: pd.DataFrame) -> None:
    header("TASK 9 - Correlation analysis")
    cols = ["rating", "returned", "discount_pct", "quantity"]
    corr = merged[cols].corr()
    print(corr.round(3).to_string())
    print("\nBands: negligible 0-0.19 | weak 0.2-0.39 | moderate 0.4-0.69 | strong 0.7-1.0")
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r = corr.loc[a, b]
            print(f"  {a:>12} vs {b:<12} r = {r:+.3f} -> {strength_band(r)}")
            assert strength_band(r) == "negligible"
    r = corr.loc["discount_pct", "returned"]
    print(f"\nHypothesis 'higher discounts reduce returns': r = {r:+.3f} "
          f"({strength_band(r)}) -> Busted. Discount level has no meaningful link to returns.")


# --------------------------------------------------------------------------
# Task 10 - Outlier-corrected time series
# --------------------------------------------------------------------------
def monthly_revenue(merged: pd.DataFrame, exclude_outliers: bool) -> pd.Series:
    frame = merged[~merged["is_outlier"]] if exclude_outliers else merged
    frame = frame.assign(year_month=pd.to_datetime(frame["order_date"]).dt.to_period("M"))
    return frame.groupby("year_month")["order_value"].sum().round(2)


def task10_timeseries(merged: pd.DataFrame) -> None:
    header("TASK 10 - Outlier-corrected time series")
    incl = monthly_revenue(merged, exclude_outliers=False)
    excl = monthly_revenue(merged, exclude_outliers=True)
    print("(1) Monthly order_value INCLUDING outliers:")
    print(incl.map("{:.2f}".format).to_string())
    print("\n(2) Monthly order_value EXCLUDING outliers (outlier-corrected):")
    print(excl.map("{:.2f}".format).to_string())
    print(f"\nPeak incl. outliers: {incl.idxmax()} | Peak excl. outliers: {excl.idxmax()}")
    print("January's apparent lead is an artifact of the two bulk orders that landed in "
          "January (O0011 on 2026-01-28, qty 25; O0098 on 2026-01-10, qty 30). Once they are "
          "excluded, March (2026-03: 20318.90) is the genuine peak month. This is why outlier "
          "detection (Task 6) must come before the time-series analysis.")
    assert str(incl.idxmax()) == "2026-01" and incl.iloc[0] == 29582.10
    assert excl.astype(float).round(2).tolist() == [
        11637.10, 13195.50, 20318.90, 9495.30, 13151.10, 11615.40
    ]


def build_clean_dataset() -> pd.DataFrame:
    """Full pipeline without printing side effects beyond the task output."""
    orders, customers, products = task1_load()
    orders = task2_payment(orders)
    orders_clean, dropped = task3_dedupe(orders)
    orders_clean = task4_impute(orders_clean)
    merged = task5_merge(orders_clean, dropped, customers, products)
    return task6_outliers(merged)


def main() -> None:
    merged = build_clean_dataset()
    task7_cod(merged)
    task8_segments(merged)
    task9_correlation(merged)
    task10_timeseries(merged)
    from narrator.export_findings import write_findings

    write_findings(merged)
    header("All Part 2 checks passed.")


if __name__ == "__main__":
    main()
