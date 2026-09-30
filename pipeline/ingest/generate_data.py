"""
Synthetic data generator — Ingest stage.
Produces three raw CSV files:
  - raw/customers.csv
  - raw/products.csv
  - raw/orders.csv
"""
import os
import random
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INGEST] %(message)s")
log = logging.getLogger(__name__)

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ── Output directories ──────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(BASE, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ── Constants ────────────────────────────────────────────────────────────────
N_CUSTOMERS = 2_000
N_PRODUCTS  = 150
N_ORDERS    = 25_000
START_DATE  = datetime(2022, 1, 1)
END_DATE    = datetime(2024, 12, 31)

CATEGORIES = {
    "Electronics":  {"weight": 0.20, "price_range": (49,  1499)},
    "Clothing":     {"weight": 0.25, "price_range": (10,   200)},
    "Home & Garden":{"weight": 0.15, "price_range": (15,   500)},
    "Sports":       {"weight": 0.15, "price_range": (20,   400)},
    "Books":        {"weight": 0.10, "price_range": (8,     60)},
    "Toys":         {"weight": 0.08, "price_range": (10,   150)},
    "Beauty":       {"weight": 0.07, "price_range": (5,    120)},
}

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
CHANNELS = ["Online", "In-Store", "Mobile App", "Marketplace"]


def generate_customers() -> pd.DataFrame:
    log.info("Generating %d customers …", N_CUSTOMERS)
    records = []
    for cid in range(1, N_CUSTOMERS + 1):
        reg_date = fake.date_between(START_DATE.date(), END_DATE.date())
        records.append({
            "customer_id":   cid,
            "first_name":    fake.first_name(),
            "last_name":     fake.last_name(),
            "email":         fake.email(),
            "region":        random.choice(REGIONS),
            "country":       fake.country(),
            "city":          fake.city(),
            "registered_at": reg_date,
            "age":           random.randint(18, 72),
            "gender":        random.choice(["M", "F", "Other"]),
            "loyalty_tier":  random.choices(
                                ["Bronze", "Silver", "Gold", "Platinum"],
                                weights=[0.5, 0.3, 0.15, 0.05])[0],
        })
    df = pd.DataFrame(records)
    # Inject ~2% duplicates / nulls for cleaning
    dup_idx = df.sample(frac=0.02, random_state=1).index
    df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)
    null_idx = df.sample(frac=0.01, random_state=2).index
    df.loc[null_idx, "email"] = None
    return df


def generate_products() -> pd.DataFrame:
    log.info("Generating %d products …", N_PRODUCTS)
    cats   = list(CATEGORIES.keys())
    weights = [CATEGORIES[c]["weight"] for c in cats]
    records = []
    for pid in range(1, N_PRODUCTS + 1):
        cat = random.choices(cats, weights=weights)[0]
        lo, hi = CATEGORIES[cat]["price_range"]
        records.append({
            "product_id":   pid,
            "product_name": fake.catch_phrase()[:60],
            "category":     cat,
            "sub_category": fake.bs()[:40],
            "unit_price":   round(random.uniform(lo, hi), 2),
            "cost_price":   round(random.uniform(lo * 0.4, lo * 0.8 + 1), 2),
            "in_stock":     random.choice([True, True, True, False]),
            "supplier":     fake.company()[:50],
        })
    return pd.DataFrame(records)


def generate_orders(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    log.info("Generating %d orders …", N_ORDERS)
    cust_ids = customers["customer_id"].unique().tolist()
    prod_ids = products["product_id"].tolist()
    prod_prices = dict(zip(products["product_id"], products["unit_price"]))

    date_range_days = (END_DATE - START_DATE).days
    records = []
    for oid in range(1, N_ORDERS + 1):
        order_date = START_DATE + timedelta(days=random.randint(0, date_range_days))
        pid        = random.choice(prod_ids)
        qty        = random.choices([1, 2, 3, 4, 5, 10], weights=[40, 25, 15, 10, 7, 3])[0]
        unit_price = prod_prices[pid]
        discount   = random.choices([0, 0.05, 0.10, 0.15, 0.20],
                                    weights=[55, 20, 12, 8, 5])[0]
        revenue    = round(unit_price * qty * (1 - discount), 2)
        status     = random.choices(
            ["Completed", "Completed", "Completed", "Returned", "Cancelled"],
            weights=[75, 5, 5, 10, 5])[0]

        records.append({
            "order_id":    oid,
            "customer_id": random.choice(cust_ids),
            "product_id":  pid,
            "order_date":  order_date.date(),
            "quantity":    qty,
            "unit_price":  unit_price,
            "discount":    discount,
            "revenue":     revenue,
            "channel":     random.choice(CHANNELS),
            "status":      status,
            "ship_days":   random.randint(1, 14) if status == "Completed" else None,
        })

    df = pd.DataFrame(records)
    # Inject ~1% nulls for cleaning demo
    df.loc[df.sample(frac=0.01, random_state=3).index, "ship_days"] = None
    return df


def run():
    customers = generate_customers()
    products  = generate_products()
    orders    = generate_orders(customers, products)

    customers.to_csv(os.path.join(RAW_DIR, "customers.csv"), index=False)
    products.to_csv(os.path.join(RAW_DIR,  "products.csv"),  index=False)
    orders.to_csv(os.path.join(RAW_DIR,    "orders.csv"),    index=False)

    log.info("✅  Ingest complete → %s", RAW_DIR)
    log.info("   customers : %d rows", len(customers))
    log.info("   products  : %d rows", len(products))
    log.info("   orders    : %d rows", len(orders))


if __name__ == "__main__":
    run()
