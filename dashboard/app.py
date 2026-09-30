"""
dashboard/app.py  —  Interactive BI Dashboard (Dash + Plotly)
Tabs:
  1. Overview KPIs
  2. Sales Trends
  3. Product Analysis
  4. Customer Segments
  5. Pipeline Quality Report
"""
import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ── Data loading ─────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR  = os.path.join(BASE, "data", "processed")

def load_data():
    orders    = pd.read_parquet(os.path.join(PROC_DIR, "orders.parquet"))
    customers = pd.read_parquet(os.path.join(PROC_DIR, "customers.parquet"))
    products  = pd.read_parquet(os.path.join(PROC_DIR, "products.parquet"))
    rfm       = pd.read_parquet(os.path.join(PROC_DIR, "rfm.parquet"))
    with open(os.path.join(PROC_DIR, "dq_report.json")) as f:
        dq = json.load(f)
    return orders, customers, products, rfm, dq

orders, customers, products, rfm, dq_report = load_data()

completed = orders[orders["status"] == "Completed"]

# ── Theme / colours ───────────────────────────────────────────────────────────
COLORS = {
    "bg":       "#0f1117",
    "card":     "#1a1d27",
    "accent1":  "#7c6af7",   # purple
    "accent2":  "#22d3ee",   # cyan
    "accent3":  "#f97316",   # orange
    "accent4":  "#22c55e",   # green
    "text":     "#e2e8f0",
    "subtext":  "#94a3b8",
}

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor=COLORS["card"],
        plot_bgcolor =COLORS["bg"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif", size=13),
        colorway=[COLORS["accent1"], COLORS["accent2"], COLORS["accent3"],
                  COLORS["accent4"], "#f43f5e", "#eab308"],
        xaxis=dict(gridcolor="#2d3148", zeroline=False),
        yaxis=dict(gridcolor="#2d3148", zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=20, t=40, b=40),
    )
)

# ── Helper builders ────────────────────────────────────────────────────────────
def kpi_card(title, value, icon, color, sub=None):
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Span(icon, style={"fontSize": "2rem"}),
                    html.Div([
                        html.P(title, className="mb-0",
                               style={"color": COLORS["subtext"], "fontSize": "0.8rem",
                                      "textTransform": "uppercase", "letterSpacing": "0.05em"}),
                        html.H3(value, className="mb-0",
                                style={"color": color, "fontWeight": "700", "fontSize": "1.8rem"}),
                        html.Small(sub or "", style={"color": COLORS["subtext"]}),
                    ], style={"marginLeft": "1rem"}),
                ], style={"display": "flex", "alignItems": "center"}),
            ])
        ], style={"backgroundColor": COLORS["card"], "border": f"1px solid {color}33",
                  "borderRadius": "12px", "boxShadow": f"0 0 12px {color}22"}),
        xs=12, sm=6, md=3, className="mb-3"
    )


def section_header(title, subtitle=""):
    return html.Div([
        html.H5(title, style={"color": COLORS["text"], "fontWeight": "600", "marginBottom": "2px"}),
        html.Small(subtitle, style={"color": COLORS["subtext"]}),
    ], className="mb-3 mt-2")


# ── Pre-compute KPIs ──────────────────────────────────────────────────────────
total_revenue   = completed["revenue"].sum()
total_orders    = len(completed)
total_customers = completed["customer_id"].nunique()
avg_order_val   = total_revenue / total_orders if total_orders else 0
return_rate     = len(orders[orders["status"] == "Returned"]) / len(orders) * 100

# Monthly trend
monthly = (
    completed.groupby("month_str")
    .agg(revenue=("revenue", "sum"), orders=("order_id", "count"))
    .reset_index()
    .sort_values("month_str")
)

# ── App layout ────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="BI Dashboard",
    suppress_callback_exceptions=True,
)
app.layout = html.Div(style={"backgroundColor": COLORS["bg"], "minHeight": "100vh",
                              "fontFamily": "Inter, sans-serif", "color": COLORS["text"]}, children=[

    # ── Header ────────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Span("📊", style={"fontSize": "2rem", "marginRight": "0.75rem"}),
            html.Div([
                html.H4("Business Intelligence Dashboard",
                        style={"margin": 0, "fontWeight": "700", "color": COLORS["text"]}),
                html.Small("End-to-End Data Pipeline  ·  2022–2024 Sales Analytics",
                           style={"color": COLORS["subtext"]}),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div([
            dbc.Badge("LIVE", color="success", className="me-2"),
            html.Small("Data refreshed at pipeline run", style={"color": COLORS["subtext"]}),
        ]),
    ], style={"backgroundColor": COLORS["card"], "padding": "1rem 2rem",
              "display": "flex", "justifyContent": "space-between", "alignItems": "center",
              "borderBottom": f"2px solid {COLORS['accent1']}"}),

    # ── Tabs ──────────────────────────────────────────────────────────────────
    dbc.Container(fluid=True, style={"padding": "1.5rem"}, children=[
        dcc.Tabs(id="tabs", value="overview", style={"marginBottom": "1.5rem"},
                 colors={"border": COLORS["accent1"], "primary": COLORS["accent1"],
                         "background": COLORS["card"]},
                 children=[
            dcc.Tab(label="🏠 Overview",          value="overview"),
            dcc.Tab(label="📈 Sales Trends",       value="trends"),
            dcc.Tab(label="📦 Product Analysis",   value="products"),
            dcc.Tab(label="👥 Customer Segments",  value="customers"),
            dcc.Tab(label="🔍 Pipeline Quality",   value="quality"),
        ]),
        html.Div(id="tab-content"),
    ]),
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
def render_overview():
    # Revenue by channel donut
    ch_rev = completed.groupby("channel")["revenue"].sum().reset_index()
    fig_channel = go.Figure(go.Pie(
        labels=ch_rev["channel"], values=ch_rev["revenue"],
        hole=0.55, textinfo="label+percent",
    ))
    fig_channel.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue by Channel")

    # Monthly revenue mini sparkline
    fig_spark = go.Figure(go.Scatter(
        x=monthly["month_str"], y=monthly["revenue"],
        fill="tozeroy", mode="lines",
        line=dict(color=COLORS["accent1"], width=2),
        fillcolor=COLORS["accent1"] + "33",
    ))
    fig_spark.update_layout(**PLOTLY_TEMPLATE["layout"], title="Monthly Revenue Trend",
                            xaxis=dict(tickangle=45, showgrid=False),
                            height=250)

    # Orders by status
    status_cnt = orders.groupby("status").size().reset_index(name="count")
    fig_status = px.bar(status_cnt, x="status", y="count", color="status",
                        color_discrete_sequence=[COLORS["accent4"], COLORS["accent2"],
                                                 COLORS["accent3"], "#f43f5e"])
    fig_status.update_layout(**PLOTLY_TEMPLATE["layout"], title="Orders by Status",
                             showlegend=False, height=250)

    return html.Div([
        # KPI row
        dbc.Row([
            kpi_card("Total Revenue",     f"${total_revenue:,.0f}",    "💰", COLORS["accent4"],
                     f"{total_orders:,} completed orders"),
            kpi_card("Total Orders",      f"{total_orders:,}",         "🛒", COLORS["accent1"],
                     f"Return rate {return_rate:.1f}%"),
            kpi_card("Unique Customers",  f"{total_customers:,}",      "👤", COLORS["accent2"],
                     f"Avg {total_orders//total_customers} orders each"),
            kpi_card("Avg Order Value",   f"${avg_order_val:,.2f}",    "📊", COLORS["accent3"]),
        ]),

        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_spark),   md=8, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_channel), md=4, className="mb-3"),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_status),  md=6, className="mb-3"),
            dbc.Col([
                section_header("Quick Stats"),
                _quick_stats_table(),
            ], md=6, className="mb-3"),
        ]),
    ])


def _quick_stats_table():
    by_region = completed.groupby("region")["revenue"].sum().sort_values(ascending=False)
    rows = [{"Region": r, "Revenue": f"${v:,.0f}"} for r, v in by_region.items()]
    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in ["Region", "Revenue"]],
        style_table={"overflowX": "auto"},
        style_cell={"backgroundColor": COLORS["card"], "color": COLORS["text"],
                    "border": f"1px solid #2d3148", "textAlign": "left", "padding": "8px"},
        style_header={"backgroundColor": COLORS["bg"], "fontWeight": "bold",
                      "color": COLORS["accent1"]},
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SALES TRENDS
# ══════════════════════════════════════════════════════════════════════════════
def render_trends():
    # Revenue + orders dual-axis by month
    fig_dual = go.Figure()
    fig_dual.add_trace(go.Scatter(
        x=monthly["month_str"], y=monthly["revenue"],
        name="Revenue (\$)", mode="lines+markers",
        line=dict(color=COLORS["accent1"], width=2),
    ))
    fig_dual.add_trace(go.Bar(
        x=monthly["month_str"], y=monthly["orders"],
        name="Orders", yaxis="y2",
        marker_color=COLORS["accent2"] + "88",
        opacity=0.7,
    ))
    fig_dual.update_layout(
        **PLOTLY_TEMPLATE["layout"],
        title="Monthly Revenue & Order Volume",
        yaxis=dict(title="Revenue (\$)", gridcolor="#2d3148"),
        yaxis2=dict(title="Orders", overlaying="y", side="right", showgrid=False),
        xaxis=dict(tickangle=45),
        height=380,
    )

    # Revenue by year bar
    yearly = completed.groupby("year")["revenue"].sum().reset_index()
    fig_yoy = px.bar(yearly, x="year", y="revenue", text_auto=".2s",
                     color_discrete_sequence=[COLORS["accent3"]])
    fig_yoy.update_layout(**PLOTLY_TEMPLATE["layout"], title="Year-over-Year Revenue",
                          yaxis_title="Revenue (\$)")

    # Revenue by quarter heatmap
    hm = completed.groupby(["year", "quarter"])["revenue"].sum().reset_index()
    hm_pivot = hm.pivot(index="year", columns="quarter", values="revenue")
    fig_hm = px.imshow(hm_pivot, text_auto=".2s", aspect="auto",
                       color_continuous_scale="Purples",
                       labels=dict(color="Revenue (\$)"))
    fig_hm.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue Heatmap by Year × Quarter")

    # Revenue by weekday
    wd_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    wd = completed.groupby("weekday")["revenue"].mean().reindex(wd_order).reset_index()
    fig_wd = px.bar(wd, x="weekday", y="revenue",
                    color_discrete_sequence=[COLORS["accent4"]])
    fig_wd.update_layout(**PLOTLY_TEMPLATE["layout"], title="Avg Revenue by Weekday",
                         yaxis_title="Avg Revenue (\$)")

    return html.Div([
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_dual), md=12, className="mb-3")]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_yoy), md=4, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_hm),  md=4, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_wd),  md=4, className="mb-3"),
        ]),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def render_products():
    # Revenue by category
    cat_rev = completed.groupby("category")["revenue"].sum().sort_values(ascending=True).reset_index()
    fig_cat = px.bar(cat_rev, x="revenue", y="category", orientation="h",
                     color="revenue", color_continuous_scale="Purples",
                     text_auto=".2s")
    fig_cat.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue by Category",
                          xaxis_title="Revenue (\$)", yaxis_title="")

    # Top 15 products
    prod_rev = (
        completed.merge(products[["product_id", "product_name", "category"]], on="product_id")
        .groupby(["product_name", "category"])["revenue"].sum()
        .nlargest(15).reset_index()
    )
    fig_top = px.bar(prod_rev, x="revenue", y="product_name", orientation="h",
                     color="category",
                     color_discrete_sequence=[COLORS["accent1"], COLORS["accent2"],
                                              COLORS["accent3"], COLORS["accent4"],
                                              "#f43f5e", "#eab308", "#a855f7"])
    fig_top.update_layout(**PLOTLY_TEMPLATE["layout"], title="Top 15 Products by Revenue",
                          xaxis_title="Revenue (\$)", yaxis_title="", height=500)

    # Category × Channel heat
    cc = completed.groupby(["category", "channel"])["revenue"].sum().reset_index()
    cc_piv = cc.pivot(index="category", columns="channel", values="revenue").fillna(0)
    fig_cc = px.imshow(cc_piv, text_auto=".2s", color_continuous_scale="Teal",
                       aspect="auto")
    fig_cc.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue: Category × Channel")

    # Margin distribution
    fig_margin = px.box(products, x="category", y="margin_pct",
                        color="category",
                        color_discrete_sequence=[COLORS["accent1"], COLORS["accent2"],
                                                 COLORS["accent3"], COLORS["accent4"],
                                                 "#f43f5e", "#eab308", "#a855f7"])
    fig_margin.update_layout(**PLOTLY_TEMPLATE["layout"], title="Margin % Distribution by Category",
                             showlegend=False, yaxis_title="Margin (%)")

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_cat),    md=5, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_margin), md=7, className="mb-3"),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_top), md=7, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_cc),  md=5, className="mb-3"),
        ]),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CUSTOMER SEGMENTS
# ══════════════════════════════════════════════════════════════════════════════
def render_customers():
    # RFM segment pie
    seg_counts = rfm.groupby("segment").size().reset_index(name="count")
    fig_seg = px.pie(seg_counts, names="segment", values="count", hole=0.45,
                     color_discrete_sequence=[COLORS["accent1"], COLORS["accent2"],
                                              COLORS["accent3"], COLORS["accent4"],
                                              "#f43f5e", "#eab308"])
    fig_seg.update_layout(**PLOTLY_TEMPLATE["layout"], title="RFM Customer Segments")

    # RFM scatter
    rfm_plot = rfm.merge(completed.groupby("customer_id")["revenue"].sum().reset_index(),
                         on="customer_id", how="left")
    fig_rfm = px.scatter(rfm_plot, x="recency", y="monetary", size="frequency",
                         color="segment", hover_data=["customer_id"],
                         color_discrete_sequence=[COLORS["accent1"], COLORS["accent2"],
                                                  COLORS["accent3"], COLORS["accent4"],
                                                  "#f43f5e", "#eab308"],
                         size_max=20)
    fig_rfm.update_layout(**PLOTLY_TEMPLATE["layout"],
                          title="RFM Scatter: Recency vs Monetary (bubble=Frequency)",
                          xaxis_title="Recency (days since last order)",
                          yaxis_title="Total Revenue (\$)", height=420)

    # Revenue by loyalty tier
    lt_rev = completed.groupby("loyalty_tier")["revenue"].sum().sort_values(ascending=False).reset_index()
    fig_lt = px.bar(lt_rev, x="loyalty_tier", y="revenue", text_auto=".2s",
                    color="loyalty_tier",
                    color_discrete_sequence=[COLORS["accent1"], COLORS["accent2"],
                                             COLORS["accent3"], COLORS["accent4"]])
    fig_lt.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue by Loyalty Tier",
                         yaxis_title="Revenue (\$)", showlegend=False)

    # Revenue by region
    reg_rev = completed.groupby("region")["revenue"].sum().sort_values(ascending=True).reset_index()
    fig_reg = px.bar(reg_rev, x="revenue", y="region", orientation="h",
                     color="revenue", color_continuous_scale="Blues", text_auto=".2s")
    fig_reg.update_layout(**PLOTLY_TEMPLATE["layout"], title="Revenue by Region",
                          xaxis_title="Revenue (\$)", yaxis_title="")

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_seg), md=4, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_lt),  md=4, className="mb-3"),
            dbc.Col(dcc.Graph(figure=fig_reg), md=4, className="mb-3"),
        ]),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_rfm), md=12, className="mb-3")]),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — PIPELINE QUALITY
# ══════════════════════════════════════════════════════════════════════════════
def render_quality():
    cards = []
    for tbl, info in dq_report.items():
        dups = info.get("duplicates_removed", 0)
        raw  = info["raw_rows"]
        clean= info["clean_rows"]
        null_items = [(c, n) for c, n in info["null_counts_raw"].items() if n > 0]

        cards.append(dbc.Col(dbc.Card([
            dbc.CardHeader(html.H6(f"📄 {tbl.upper()}",
                                   style={"color": COLORS["accent1"], "margin": 0}),
                           style={"backgroundColor": COLORS["bg"]}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([html.P("Raw rows",   className="mb-0 text-muted small"),
                             html.H5(f"{raw:,}", style={"color": COLORS["text"]})]),
                    dbc.Col([html.P("Clean rows", className="mb-0 text-muted small"),
                             html.H5(f"{clean:,}", style={"color": COLORS["accent4"]})]),
                    dbc.Col([html.P("Dupes removed", className="mb-0 text-muted small"),
                             html.H5(f"{dups:,}", style={"color": COLORS["accent3"]})]),
                ]),
                html.Hr(style={"borderColor": "#2d3148"}),
                html.P("Null columns (raw):", className="mb-1 small text-muted"),
                html.Ul([
                    html.Li(f"{c}: {n} nulls ({n/raw*100:.1f}%)",
                            style={"fontSize": "0.85rem", "color": COLORS["subtext"]})
                    for c, n in null_items
                ] or [html.Li("None ✅", style={"color": COLORS["accent4"], "fontSize": "0.85rem"})]),
            ]),
        ], style={"backgroundColor": COLORS["card"], "border": f"1px solid #2d3148",
                  "borderRadius": "10px"}), md=4, className="mb-3"))

    # DQ summary bar chart
    summary = pd.DataFrame([
        {"Table": t, "Metric": "Rows Removed", "Count": info["raw_rows"] - info["clean_rows"]}
        for t, info in dq_report.items()
    ] + [
        {"Table": t, "Metric": "Duplicates", "Count": info["duplicates_removed"]}
        for t, info in dq_report.items()
    ])
    fig_dq = px.bar(summary, x="Table", y="Count", color="Metric", barmode="group",
                    color_discrete_sequence=[COLORS["accent3"], COLORS["accent1"]])
    fig_dq.update_layout(**PLOTLY_TEMPLATE["layout"],
                         title="Data Quality Issues by Table",
                         yaxis_title="Row Count")

    return html.Div([
        section_header("Data Quality Report", "Stats captured from the last pipeline run"),
        dbc.Row(cards),
        dbc.Row([dbc.Col(dcc.Graph(figure=fig_dq), md=8, className="mb-3")]),
    ])


# ── Routing callback ──────────────────────────────────────────────────────────
@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    if tab == "overview":   return render_overview()
    if tab == "trends":     return render_trends()
    if tab == "products":   return render_products()
    if tab == "customers":  return render_customers()
    if tab == "quality":    return render_quality()
    return html.Div("Tab not found")


if __name__ == "__main__":
    print("\n" + "-"*55)
    print("  BI Dashboard running at  http://127.0.0.1:8050")
    print("-"*55 + "\n")
    app.run(debug=False, host="127.0.0.1", port=8050)
