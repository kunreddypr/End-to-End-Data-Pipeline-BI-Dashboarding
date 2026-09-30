# 🚀 End-to-End Data Pipeline & BI Dashboard

A fully self-contained data engineering + business intelligence project built with Python.

## 📐 Architecture

```
pipeline/
├── ingest/       → Generate synthetic raw data (sales, orders, customers)
├── transform/    → Clean, validate, and enrich the data
├── data/
│   ├── raw/      → Raw CSV files from ingest stage
│   └── processed/→ Cleaned & transformed Parquet files
└── dashboard/    → Interactive Dash + Plotly BI dashboard
```

## ⚡ Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline (ingest → clean → transform)
python run_pipeline.py

# 3. Launch the BI dashboard
python dashboard/app.py
```

Then open **http://127.0.0.1:8050** in your browser.

## 🗂️ Pipeline Stages

| Stage | Script | Description |
|-------|--------|-------------|
| **Ingest** | `pipeline/ingest/generate_data.py` | Generates 3 years of synthetic sales data |
| **Transform** | `pipeline/transform/clean_transform.py` | Cleans, validates, enriches data |
| **Dashboard** | `dashboard/app.py` | Interactive multi-tab BI dashboard |

## 📊 Dashboard Tabs

- **Overview** – KPI cards: Revenue, Orders, Customers, Avg Order Value
- **Sales Trends** – Monthly revenue & volume line charts
- **Product Analysis** – Category revenue breakdown, top products
- **Customer Segments** – RFM segmentation, geographic distribution
- **Pipeline Logs** – Data quality report from the transform stage
