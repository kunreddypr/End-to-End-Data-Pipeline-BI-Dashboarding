"""
Transform stage — Clean, validate, and enrich raw CSVs.
Outputs enriched Parquet files to data/processed/.
Also writes a data-quality report (JSON) for the dashboard.
"""
import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TRANSFORM] %(message)s")
log = logging.getLogger(__name__)

BASE      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR   = os.path.join(BASE, "data", "raw")
PROC_DIR  = os.path.join(BASE, "data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _dq_check(name: str, df_raw: pd.DataFrame, df_clean: pd.DataFrame, issues: dict):
    issues[name] = {
        "raw_rows":        int(len(df_raw)),
        "clean_rows":      int(len(df_clean)),
        "duplicates_removed": int(len(df_raw) - len(df_raw.drop_duplicates())),
        "null_counts_raw": {c: int(df_raw[c].isna().sum()) for c in df_raw.columns},
    }
    log.info("   %s: %d → %d rows after cleaning", name, len(df_raw), len(df_clean))


# ── Per-table cleaning ───────────────────────────────────────────────────────

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["customer_id"]).copy()
    df["email"] = df["email"].fillna("unknown@unknown.com")
    df["registered_at"] = pd.to_datetime(df["registered_at"])
    df["age"] = df["age"].clip(lower=18, upper=100)
    df["full_name"] = df["first_name"].str.strip() + " " + df["last_name"].str.strip()
    log.info("   customers cleaned: %d → %d rows", before, len(df))
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["product_id"])
    df["unit_price"] = df["unit_price"].clip(lower=0.01)
    df["cost_price"]  = df["cost_price"].clip(lower=0.01)
    df["margin_pct"]  = ((df["unit_price"] - df["cost_price"]) / df["unit_price"] * 100).round(2)
    df["product_name"] = df["product_name"].str.strip()
    return df


def clean_orders(df: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"])
    df = df[df["customer_id"].isin(customers["customer_id"])]
    df = df[df["product_id"].isin(products["product_id"])]
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_days"]  = df["ship_days"].fillna(df["ship_days"].median())
    df["revenue"]    = df["revenue"].clip(lower=0)
    df["quantity"]   = df["quantity"].clip(lower=1)

    # Enrich: year / month / quarter / weekday
    df["year"]      = df["order_date"].dt.year
    df["month"]     = df["order_date"].dt.month
    df["quarter"]   = df["order_date"].dt.quarter
    df["month_str"] = df["order_date"].dt.to_period("M").astype(str)
    df["weekday"]   = df["order_date"].dt.day_name()

    # Merge product category & customer region
    df = df.merge(
        products[["product_id", "category", "unit_price", "margin_pct"]],
        on="product_id", how="left", suffixes=("", "_prod")
    )
    df = df.merge(
        customers[["customer_id", "region", "loyalty_tier", "full_name"]],
        on="customer_id", how="left"
    )

    log.info("   orders cleaned: %d → %d rows", before, len(df))
    return df


def compute_rfm(orders: pd.DataFrame, snapshot: date) -> pd.DataFrame:
    """Simple RFM segmentation on completed orders only."""
    snap = pd.Timestamp(snapshot)
    completed = orders[orders["status"] == "Completed"]
    rfm = completed.groupby("customer_id").agg(
        recency  =("order_date", lambda x: (snap - x.max()).days),
        frequency=("order_id",   "count"),
        monetary =("revenue",    "sum"),
    ).reset_index()

    # Quintile-based scoring (1=worst, 5=best)
    for col in ["recency", "frequency", "monetary"]:
        labels = [5, 4, 3, 2, 1] if col == "recency" else [1, 2, 3, 4, 5]
        rfm[f"{col}_score"] = pd.qcut(rfm[col], q=5, labels=labels, duplicates="drop").astype(int)

    rfm["rfm_score"] = rfm["recency_score"] + rfm["frequency_score"] + rfm["monetary_score"]

    def segment(row):
        if row["rfm_score"] >= 13:
            return "Champions"
        elif row["rfm_score"] >= 10:
            return "Loyal Customers"
        elif row["recency_score"] >= 4:
            return "Recent Customers"
        elif row["frequency_score"] >= 4:
            return "Potential Loyalists"
        elif row["rfm_score"] >= 6:
            return "At Risk"
        else:
            return "Lost"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


def run():
    log.info("Loading raw data …")
    customers_raw = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    products_raw  = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    orders_raw    = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))

    issues: dict = {}

    customers = clean_customers(customers_raw)
    products  = clean_products(products_raw)
    orders    = clean_orders(orders_raw, customers, products)
    rfm       = compute_rfm(orders, date(2025, 1, 1))

    _dq_check("customers", customers_raw, customers, issues)
    _dq_check("products",  products_raw,  products,  issues)
    _dq_check("orders",    orders_raw,    orders,    issues)

    # ── Save processed data ──────────────────────────────────────────────────
    customers.to_parquet(os.path.join(PROC_DIR, "customers.parquet"), index=False)
    products.to_parquet(os.path.join(PROC_DIR,  "products.parquet"),  index=False)
    orders.to_parquet(os.path.join(PROC_DIR,    "orders.parquet"),    index=False)
    rfm.to_parquet(os.path.join(PROC_DIR,       "rfm.parquet"),       index=False)

    with open(os.path.join(PROC_DIR, "dq_report.json"), "w") as f:
        json.dump(issues, f, indent=2)

    log.info("✅  Transform complete → %s", PROC_DIR)


if __name__ == "__main__":
    run()
