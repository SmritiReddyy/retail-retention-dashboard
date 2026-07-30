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
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", f"£{k['revenue']:,.0f}" if k["revenue"] else "£0")
c2.metric("Customers", f"{k['customers']:,}")
c3.metric("Orders", f"{k['orders']:,}")
c4.metric("Avg order value", f"£{k['avg_order_value']:,.2f}" if k["avg_order_value"] else "£0")
c5.metric(f"Churn (>{churn_days}d)", f"{churn}%")

st.divider()

# ---- Row 1: revenue trend + RFM segments ----------------------------------
left, right = st.columns(2)
with left:
    st.subheader("Monthly revenue")
    mr = data.monthly_revenue(**flt)
    if not mr.empty:
        fig = px.line(mr, x="month", y="revenue", markers=True)
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=340)
        st.plotly_chart(fig, use_container_width=True)

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

# ---- Row 2: cohort retention heatmap --------------------------------------
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

# ---- Row 3: segment table -------------------------------------------------
with st.expander("Segment detail (RFM value table)"):
    if not seg.empty:
        st.dataframe(seg.style.format({"avg_monetary": "£{:,.0f}",
                                       "total_monetary": "£{:,.0f}"}),
                     use_container_width=True)
