"""Customer Retention & Revenue Dashboard — Streamlit UI.

Run:  streamlit run app/streamlit_app.py
All analytics come from app/data.py (DuckDB SQL over a Parquet extract).
"""
import pathlib
import sys

import plotly.express as px
import streamlit as st

sys.path.append(str(pathlib.Path(__file__).resolve().parent))
import data  # noqa: E402

st.set_page_config(page_title="Retention & Revenue", page_icon="🛒", layout="wide")

if not data.PARQUET.exists():
    st.error("No data yet. Run: `python scripts/build_features.py` (see README).")
    st.stop()

st.title("🛒 Customer Retention & Revenue Dashboard")
st.caption("RFM segmentation · churn · cohort retention — DuckDB SQL over ~1M transactions")

# ---- Sidebar filters ------------------------------------------------------
lo, hi = data.date_bounds()
with st.sidebar:
    st.header("Filters")
    countries = st.multiselect("Country", data.country_list(), default=[])
    dr = st.date_input("Date range", value=(lo.date(), hi.date()),
                       min_value=lo.date(), max_value=hi.date())
    churn_days = st.slider("Churn threshold (days since last order)", 30, 365, 90, 15)

flt = {}
if countries:
    flt["countries"] = countries
if isinstance(dr, (list, tuple)) and len(dr) == 2:
    flt["date_range"] = (str(dr[0]), str(dr[1]))

# ---- KPI strip ------------------------------------------------------------
k = data.kpis(**flt)
churn = data.churn_rate(churn_days, **flt)
def compact(v, prefix=""):
    """17068583 -> 17.07M so the KPI tiles fit on narrow screens."""
    if not v:
        return f"{prefix}0"
    for div, suffix in ((1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            return f"{prefix}{v / div:,.2f}{suffix}"
    return f"{prefix}{v:,.0f}"


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", compact(k["revenue"], "£"), help=f"£{k['revenue'] or 0:,.0f}")
c2.metric("Customers", f"{k['customers']:,}")
c3.metric("Orders", f"{k['orders']:,}")
c4.metric("Avg order value", f"£{k['avg_order_value'] or 0:,.0f}", help=f"£{k['avg_order_value'] or 0:,.2f}")
c5.metric(f"Churn (>{churn_days}d)", f"{churn}%")

st.divider()

# ---- Row 1: revenue trend + RFM segments ----------------------------------
mr = data.monthly_revenue(**flt)
left, right = st.columns(2)
with left:
    st.subheader("Monthly revenue")
    if not mr.empty:
        fig = px.line(mr, x="month", y="revenue", markers=True, labels={"revenue": "Revenue (£)", "month": ""})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340)
        st.plotly_chart(fig, use_container_width=True)
        if mr["month"].max().month == 12 and mr["month"].max().year == 2011:
            st.caption("December 2011 is a partial month: the data ends on 9 December.")

with right:
    st.subheader("Customers by RFM segment")
    seg = data.segment_summary(**flt)
    if not seg.empty:
        fig = px.bar(seg, x="customers", y="segment", orientation="h",
                     color="total_monetary", color_continuous_scale="Blues",
                     labels={"total_monetary": "Total £"})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340,
                          yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

# ---- Row 2: order value trend + LTV by segment -----------------------------
left, right = st.columns(2)
with left:
    st.subheader("Average order value by month")
    if not mr.empty:
        fig = px.line(mr, x="month", y="avg_order_value", markers=True,
                      labels={"avg_order_value": "Avg order value (£)", "month": ""})
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Historical LTV by segment")
    if not seg.empty:
        fig = px.bar(seg.sort_values("avg_ltv"), x="avg_ltv", y="segment", orientation="h",
                     text_auto=",.0f", labels={"avg_ltv": "Avg revenue per customer to date (£)", "segment": ""})
        fig.update_traces(marker_color="#2a78d6")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Historical LTV = total revenue per customer over the selected period, not a forecast.")

# ---- Row 3: cohort retention heatmap --------------------------------------
st.subheader("Cohort retention (%)")
piv = data.cohort_pivot(**flt)
if not piv.empty:
    piv = piv.loc[:, [c for c in piv.columns if c <= 12]]  # first 12 months
    fig = px.imshow(piv, text_auto=".0f", aspect="auto",
                    color_continuous_scale="Blues",
                    labels=dict(x="Months since first order", y="Cohort", color="% retained"))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No cohort data for the current filters.")

# ---- Row 4: segment table -------------------------------------------------
st.subheader("Segment detail")
if not seg.empty:
    st.dataframe(
        seg[["segment", "customers", "share_of_customers", "total_monetary", "share_of_revenue",
             "avg_ltv", "avg_orders", "avg_recency_days"]]
        .style.format({"share_of_customers": "{:.1%}", "total_monetary": "£{:,.0f}",
                       "share_of_revenue": "{:.1%}", "avg_ltv": "£{:,.0f}",
                       "avg_orders": "{:.1f}", "avg_recency_days": "{:.0f}"}),
        use_container_width=True, hide_index=True)
