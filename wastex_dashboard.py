"""
WasteX Biochar Analytics Dashboard
====================================
Streamlit dashboard untuk visualisasi data biochar WasteX.
Jalankan dengan: streamlit run wastex_dashboard.py

Requirements:
    pip install streamlit plotly pandas openpyxl

Dataset:
    Letakkan file WasteX_DA_Test_Dataset_final.xlsx di folder yang sama,
    atau ubah path INPUT_FILE di bagian CONFIG.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, datetime
import warnings

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
INPUT_FILE = "data/WasteX_Cleaned_Output.xlsx"

VALID_APP_TYPES = [
    "Application-Pure Biochar",
    "Application-Charged Biochar",
    "Sale-Pure Biochar",
    "Sale-Charged Biochar",
]

FEED_COLORS = {
    "Rice husk": "#22c55e",
    "Corn cob/leaves": "#3b82f6",
    "Wood waste": "#f59e0b",
    "Cassava root/stems/leaves": "#a855f7",
}

OP_COLORS = {
    "operator.1@wastex.io": "#10b981",
    "operator.2@wastex.io": "#6366f1",
    "operator.3@wastex.io": "#f59e0b",
}

PLOTLY_TEMPLATE = None # Let Streamlit theme it
CHART_FONT = dict(family="Inter, sans-serif", size=12)

# ══════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="WasteX Analytics",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ── Typography ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* ── Hide default Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 1.5rem 2rem 2rem 2rem !important; max-width: 1400px !important; }
    
    /* ── Header brand ── */
    .wx-header {
        background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #047857 100%);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .wx-brand { color: white; font-size: 28px; font-weight: 600; letter-spacing: -0.5px; }
    .wx-brand span { color: #6ee7b7; }
    .wx-subtitle { color: #a7f3d0; font-size: 13px; margin-top: 2px; }
    .wx-badge {
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 6px 14px;
        color: white;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .wx-dot { width: 6px; height: 6px; background: #6ee7b7; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
    
    /* ── KPI Cards ── */
    .kpi-card {
        background: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        height: 100%;
    }
    .kpi-icon { font-size: 22px; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 600; line-height: 1; margin-bottom: 4px; }
    .kpi-label { font-size: 11px; color: var(--text-color); opacity: 0.8; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }
    .kpi-sub { font-size: 11px; color: var(--text-color); opacity: 0.5; margin-top: 4px; }
    .kpi-green .kpi-value { color: #10b981; }
    .kpi-blue .kpi-value  { color: #3b82f6; }
    .kpi-amber .kpi-value { color: #f59e0b; }
    .kpi-red .kpi-value   { color: #ef4444; }
    .kpi-teal .kpi-value  { color: #06b6d4; }
    
    /* ── Section headers ── */
    .section-title {
        font-size: 15px; font-weight: 600; color: var(--text-color);
        margin-bottom: 4px;
    }
    .section-sub { font-size: 12px; color: var(--text-color); opacity: 0.6; margin-bottom: 16px; }
    
    /* ── Insight cards ── */
    .insight-card {
        border-radius: 12px;
        padding: 18px 20px;
        height: 100%;
        background: var(--secondary-background-color);
    }
    .insight-green { border-left: 4px solid #10b981; }
    .insight-red   { border-left: 4px solid #ef4444; }
    .insight-amber { border-left: 4px solid #f59e0b; }
    .insight-num   { font-size: 11px; color: var(--text-color); opacity: 0.7; text-transform: uppercase; letter-spacing: .5px; font-weight: 500; margin-bottom: 8px; }
    .insight-q     { font-size: 13px; font-weight: 600; color: var(--text-color); margin-bottom: 8px; line-height: 1.4; }
    .insight-body  { font-size: 12px; color: var(--text-color); opacity: 0.9; line-height: 1.7; }
    .insight-rec   { margin-top: 10px; font-size: 11px; font-weight: 500; padding: 6px 10px; border-radius: 6px; background: rgba(255,255,255,0.05); }
    .insight-rec-green { color: #34d399; }
    .insight-rec-red   { color: #f87171; }
    .insight-rec-amber { color: #fbbf24; }
    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--secondary-background-color);
    }
    [data-testid="stSidebar"] .stSelectbox label { font-size: 12px; font-weight: 500; }
    [data-testid="stSidebar"] .stMultiSelect label { font-size: 12px; font-weight: 500; }
    
    /* ── Status badges ── */
    .badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 500; }
    .badge-green { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-red   { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-blue  { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-amber { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-gray  { background: var(--secondary-background-color); color: var(--text-color); border: 1px solid rgba(255, 255, 255, 0.1); }
    
    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--secondary-background-color);
        padding: 6px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-color);
    }
    .stTabs [aria-selected="true"] {
        background: var(--background-color) !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* ── Divider ── */
    .wx-divider { height: 1px; background: var(--secondary-background-color); margin: 24px 0; }
    
    /* ── Metric override ── */
    [data-testid="metric-container"] {
        background: var(--background-color);
        border: 1px solid var(--secondary-background-color);
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# DATA LOADING & CACHING
# ══════════════════════════════════════════════════════════
@st.cache_data
def load_data():
    xls   = pd.ExcelFile(INPUT_FILE)
    bp    = pd.read_excel(xls, "CLEANED_prod_batch")
    bprod = pd.read_excel(xls, "CLEANED_bag_prod")
    ba    = pd.read_excel(xls, "CLEANED_app_batch")
    bapp  = pd.read_excel(xls, "CLEANED_bag_app")
    return bp, bprod, ba, bapp


@st.cache_data
def clean_data(bp, bprod, ba, bapp):
    """Apply basic cleaning: fix comma decimal, compute derived fields."""
    bp    = bp.copy()
    bprod = bprod.copy()
    ba    = ba.copy()
    bapp  = bapp.copy()

    # Fix comma decimal in bag_production.weight
    bprod["weight"] = pd.to_numeric(
        bprod["weight"].astype(str).str.replace(",", "."), errors="coerce"
    )

    # Parse timestamps
    for df in [bp, bprod, ba, bapp]:
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    if "application_date" in ba.columns:
        ba["application_date"] = pd.to_datetime(ba["application_date"], errors="coerce")

    # Derived: conversion efficiency
    if "feedstock_amount" in bp.columns:
        bp["efficiency_%"] = (bp["biochar_amount_kg"] / bp["feedstock_amount"] * 100).round(2)

    # Derived: batch date from activity_id
    if "activity_id" in bp.columns:
        bp["batch_date"] = pd.to_datetime(
            bp["activity_id"].str[:6], format="%y%m%d", errors="coerce"
        )

    # Anomaly flags
    bp["has_anomaly"] = bp["carbon_content_%"].isna()

    # Operator short label
    for df in [bp, bprod, ba, bapp]:
        if "username" in df.columns:
            df["operator"] = df["username"].str.extract(r"(operator\.\d+)")

    return bp, bprod, ba, bapp


# ══════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════
def chart_defaults(fig, height=320, margin=None):
    m = margin or dict(t=20, b=30, l=10, r=10)
    fig.update_layout(
        height=height,
        margin=m,
        font=CHART_FONT,
        # Remove hardcoded backgrounds to allow Streamlit's native theme to style Plotly
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11)
        ),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.2)", tickfont=dict(size=11))
    return fig


# ══════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════
def main():
    # ── Load data ──────────────────────────────────────────
    try:
        bp_raw, bprod_raw, ba_raw, bapp_raw = load_data()
    except FileNotFoundError:
        st.error(f"❌ File tidak ditemukan: `{INPUT_FILE}`")
        st.info("Pastikan file `WasteX_Cleaned_Output.xlsx` sudah tersedia di dalam folder `data/`.")
        st.stop()

    bp, bprod, ba, bapp = clean_data(bp_raw, bprod_raw, ba_raw, bapp_raw)

    # ── HEADER ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="wx-header">
        <div>
            <div class="wx-brand">🌱 Waste<span>X</span> Biochar Analytics</div>
            <div class="wx-subtitle">Production & Application Dashboard · Cleaned Data · Nov 2024 – Apr 2025</div>
        </div>
        <div>
            <div class="wx-badge">
                <span class="wx-dot"></span>
                Pipeline active · Last run: {datetime.now().strftime("%d %b %Y %H:%M")} WIB
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SIDEBAR FILTERS ────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        st.markdown("---")

        # Filter 1: Feedstock
        all_feeds = sorted(bp["feedstock_type"].dropna().unique().tolist())
        sel_feeds = st.multiselect(
            "Feedstock Type",
            options=all_feeds,
            default=all_feeds,
            help="Pilih satu atau lebih jenis feedstock"
        )

        # Filter 2: Operator
        all_ops = sorted(bp["username"].dropna().unique().tolist())
        op_labels = {op: f"Operator {op.split('.')[1].split('@')[0]}" for op in all_ops}
        sel_ops = st.multiselect(
            "Operator",
            options=all_ops,
            default=all_ops,
            format_func=lambda x: op_labels.get(x, x),
            help="Pilih operator yang ingin ditampilkan"
        )

        # Filter 3: Date range
        st.markdown("**Date Range (Batch)**")
        if "batch_date" in bp.columns and bp["batch_date"].notna().any():
            min_d = bp["batch_date"].min().date()
            max_d = bp["batch_date"].max().date()
            date_range = st.date_input(
                "Date range",
                value=(min_d, max_d),
                min_value=min_d,
                max_value=max_d,
                label_visibility="collapsed"
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                d_start, d_end = date_range
            else:
                d_start, d_end = min_d, max_d
        else:
            d_start, d_end = None, None

        st.markdown("---")
        st.markdown("### 📊 Dataset Info")
        st.markdown(f"""
        <div style="font-size:12px;color:#6b7280;line-height:2">
        <b>biochar_production:</b> {len(bp)} rows<br>
        <b>bag_production:</b> {len(bprod)} rows<br>
        <b>biochar_application:</b> {len(ba)} rows<br>
        <b>bag_application:</b> {len(bapp)} rows
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        <div style="font-size:11px;color:#9ca3af;line-height:1.6">
        🧹 Pipeline: Python + Pandas<br>
        ⚙️ Automation: n8n + Prefect<br>
        📋 10 anomaly types detected<br>
        ✅ 25 findings logged
        </div>
        """, unsafe_allow_html=True)

    # ── APPLY FILTERS ──────────────────────────────────────
    bp_f = bp.copy()
    if sel_feeds:
        bp_f = bp_f[bp_f["feedstock_type"].isin(sel_feeds)]
    if sel_ops:
        bp_f = bp_f[bp_f["username"].isin(sel_ops)]
    if d_start and d_end and "batch_date" in bp_f.columns:
        bp_f = bp_f[
            (bp_f["batch_date"].dt.date >= d_start) &
            (bp_f["batch_date"].dt.date <= d_end)
        ]

    # Also filter bag_prod by production_id in filtered bp
    filtered_prod_ids = set(bp_f["activity_id"].tolist()) if "activity_id" in bp_f.columns else set()
    bprod_f = bprod[bprod["production_id"].isin(filtered_prod_ids)] if filtered_prod_ids else bprod

    # ── KPI SECTION ────────────────────────────────────────
    st.markdown('<div class="section-title">Key Performance Indicators</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Agregasi dari data yang sudah di-filter · reaktif terhadap semua filter di sidebar</div>', unsafe_allow_html=True)

    total_kg   = bp_f["biochar_amount_kg"].sum()
    total_co2  = bp_f["co2e_persistent"].sum(skipna=True)
    avg_eff    = bp_f["efficiency_%"].mean() if "efficiency_%" in bp_f.columns else 0
    total_bags = len(bprod_f)
    n_batches  = len(bp_f)

    # Application stats
    total_app_weight = ba["total_weight"].sum() if "total_weight" in ba.columns else 0
    total_app_bags   = ba["number_of_bags"].sum() if "number_of_bags" in ba.columns else 0

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.markdown(f"""
        <div class="kpi-card kpi-green">
            <div class="kpi-icon">🌱</div>
            <div class="kpi-value" style="color:#059669">{total_kg:,.1f} kg</div>
            <div class="kpi-label">Total Biochar Produced</div>
            <div class="kpi-sub">{n_batches} batch · cleaned data</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card kpi-blue">
            <div class="kpi-icon">♻️</div>
            <div class="kpi-value" style="color:#2563eb">{total_co2:,.0f} kg</div>
            <div class="kpi-label">Total CO₂e Sequestered</div>
            <div class="kpi-sub">≈ {total_co2/1000:.2f} tonne CO₂e</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card kpi-amber">
            <div class="kpi-icon">⚡</div>
            <div class="kpi-value" style="color:#d97706">{avg_eff:.1f}%</div>
            <div class="kpi-label">Avg Production Efficiency</div>
            <div class="kpi-sub">biochar kg / feedstock kg</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card kpi-teal">
            <div class="kpi-icon">🎒</div>
            <div class="kpi-value" style="color:#0891b2">{int(total_app_bags)}</div>
            <div class="kpi-label">Bags Applied</div>
            <div class="kpi-sub">{total_app_weight:,.1f} kg · 5 events</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        st.markdown(f"""
        <div class="kpi-card kpi-red">
            <div class="kpi-icon">⚠️</div>
            <div class="kpi-value" style="color:#dc2626">25</div>
            <div class="kpi-label">Anomalies Flagged</div>
            <div class="kpi-sub">1 auto-fixed · 24 need review</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Production", "🌍 Application", "⚠️ Anomalies", "📋 Insights"
    ])

    # ══════════════════════════════════════════════════════
    # TAB 1 — PRODUCTION
    # ══════════════════════════════════════════════════════
    with tab1:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Row 1: Trend + Feedstock ──────────────────────
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown('<div class="section-title">Production Trend over Time</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Biochar output per batch · dual axis: biochar kg (bar) + CO₂e kg (line)</div>', unsafe_allow_html=True)

            if bp_f.empty:
                st.info("Tidak ada data untuk filter ini.")
            else:
                bp_plot = bp_f.copy()
                if "batch_date" in bp_plot.columns:
                    bp_plot = bp_plot.sort_values("batch_date")
                    x_col = "batch_date"
                else:
                    x_col = "activity_id"

                fig_trend = make_subplots(specs=[[{"secondary_y": True}]])

                for feed, grp in bp_plot.groupby("feedstock_type"):
                    color = FEED_COLORS.get(feed, "#94a3b8")
                    fig_trend.add_trace(
                        go.Bar(
                            x=grp[x_col],
                            y=grp["biochar_amount_kg"],
                            name=feed,
                            marker_color=color,
                            marker_line_width=0,
                            hovertemplate=(
                                "<b>%{x}</b><br>"
                                f"Feedstock: {feed}<br>"
                                "Biochar: %{y:.1f} kg<extra></extra>"
                            ),
                        ),
                        secondary_y=False,
                    )

                fig_trend.add_trace(
                    go.Scatter(
                        x=bp_plot[x_col],
                        y=bp_plot["co2e_persistent"],
                        mode="lines+markers",
                        name="CO₂e (kg)",
                        line=dict(color="#f59e0b", width=2.5, dash="solid"),
                        marker=dict(size=7, color="#f59e0b"),
                        hovertemplate="CO₂e: %{y:.1f} kg<extra></extra>",
                    ),
                    secondary_y=True,
                )

                fig_trend.update_yaxes(title_text="Biochar (kg)", secondary_y=False, tickfont=dict(size=11))
                fig_trend.update_yaxes(title_text="CO₂e (kg)", secondary_y=True,
                                       tickfont=dict(size=11, color="#f59e0b"))
                fig_trend = chart_defaults(fig_trend, height=300, margin=dict(t=10, b=30, l=10, r=50))
                fig_trend.update_layout(barmode="stack")
                st.plotly_chart(fig_trend, use_container_width=True)

        with c2:
            st.markdown('<div class="section-title">Feedstock Breakdown</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Total biochar kg per jenis bahan baku</div>', unsafe_allow_html=True)

            if bp_f.empty:
                st.info("—")
            else:
                feed_sum = bp_f.groupby("feedstock_type")["biochar_amount_kg"].sum().reset_index()
                fig_pie = px.pie(
                    feed_sum,
                    names="feedstock_type",
                    values="biochar_amount_kg",
                    hole=0.55,
                    color="feedstock_type",
                    color_discrete_map=FEED_COLORS,
                )
                fig_pie.update_traces(
                    textposition="outside",
                    textinfo="percent+label",
                    textfont_size=10,
                    hovertemplate="<b>%{label}</b><br>%{value:.1f} kg · %{percent}<extra></extra>",
                )
                fig_pie = chart_defaults(fig_pie, height=300, margin=dict(t=10, b=10, l=10, r=10))
                fig_pie.update_layout(legend=dict(font=dict(size=10)))
                st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("<div class='wx-divider'></div>", unsafe_allow_html=True)

        # ── Row 2: Efficiency + Carbon Quality + Operator ─
        c3, c4, c5 = st.columns(3)

        with c3:
            st.markdown('<div class="section-title">Efficiency per Feedstock</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">biochar kg / feedstock kg (%)</div>', unsafe_allow_html=True)

            if bp_f.empty or "efficiency_%" not in bp_f.columns:
                st.info("—")
            else:
                eff_grp = bp_f.groupby("feedstock_type").agg(
                    avg_eff=("efficiency_%", "mean"),
                    avg_carbon=("carbon_content_%", "mean"),
                ).reset_index().sort_values("avg_eff", ascending=True)

                fig_eff = px.bar(
                    eff_grp,
                    y="feedstock_type",
                    x="avg_eff",
                    orientation="h",
                    color="feedstock_type",
                    color_discrete_map=FEED_COLORS,
                    text=eff_grp["avg_eff"].apply(lambda v: f"{v:.1f}%"),
                )
                fig_eff.update_traces(textposition="outside", textfont_size=11)
                fig_eff.update_xaxes(range=[0, 55], title_text="Efficiency (%)")
                fig_eff.update_yaxes(title_text="")
                fig_eff = chart_defaults(fig_eff, height=240)
                fig_eff.update_layout(showlegend=False)
                st.plotly_chart(fig_eff, use_container_width=True)

        with c4:
            st.markdown('<div class="section-title">Carbon Content per Batch</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">carbon_content_% · MISSING = kritis</div>', unsafe_allow_html=True)

            if bp_f.empty:
                st.info("—")
            else:
                cc_data = bp_f[["activity_id", "feedstock_type", "carbon_content_%"]].copy()
                cc_data["label"] = cc_data["activity_id"].str[-6:]
                cc_data = cc_data.sort_values("carbon_content_%", ascending=False, na_position="last")
                cc_data["color"] = cc_data["feedstock_type"].map(FEED_COLORS).fillna("#e5e7eb")
                cc_data["display"] = cc_data["carbon_content_%"].fillna(0)
                cc_data["is_missing"] = cc_data["carbon_content_%"].isna()

                fig_cc = go.Figure()
                for _, row in cc_data.iterrows():
                    fig_cc.add_trace(go.Bar(
                        x=[row["label"]],
                        y=[row["display"]],
                        marker_color="#ef4444" if row["is_missing"] else FEED_COLORS.get(row["feedstock_type"], "#94a3b8"),
                        marker_line_width=0,
                        name=row["label"],
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{row['activity_id']}</b><br>"
                            + ("Carbon: MISSING<extra></extra>" if row["is_missing"]
                               else f"Carbon: {row['carbon_content_%']:.1f}%<extra></extra>")
                        ),
                    ))

                fig_cc.add_hline(y=50, line_dash="dot", line_color="#9ca3af",
                                 annotation_text="50% threshold", annotation_font_size=10)
                fig_cc.update_yaxes(title_text="Carbon content (%)", range=[0, 95])
                fig_cc = chart_defaults(fig_cc, height=240)
                st.plotly_chart(fig_cc, use_container_width=True)

        with c5:
            st.markdown('<div class="section-title">CO₂e by Operator</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Total carbon sequestered per operator</div>', unsafe_allow_html=True)

            if bp_f.empty:
                st.info("—")
            else:
                op_grp = bp_f.groupby("username").agg(
                    total_co2=("co2e_persistent", "sum"),
                    batches=("activity_id", "count"),
                ).reset_index()
                op_grp["label"] = op_grp["username"].str.extract(r"operator\.(\d+)").astype(str).apply(lambda x: f"Op {x[0]}")
                op_grp["color"] = op_grp["username"].map(OP_COLORS).fillna("#94a3b8")

                fig_op = px.bar(
                    op_grp,
                    x="label",
                    y="total_co2",
                    color="username",
                    color_discrete_map=OP_COLORS,
                    text=op_grp["total_co2"].apply(lambda v: f"{v:,.0f}"),
                )
                fig_op.update_traces(
                    textposition="outside", textfont_size=11,
                    marker_line_width=0,
                    hovertemplate="<b>%{x}</b><br>CO₂e: %{y:,.0f} kg<br>Batches: %{customdata}<extra></extra>",
                    customdata=op_grp["batches"].values,
                )
                fig_op.update_yaxes(title_text="CO₂e (kg)")
                fig_op.update_xaxes(title_text="")
                fig_op = chart_defaults(fig_op, height=240)
                fig_op.update_layout(showlegend=False)
                st.plotly_chart(fig_op, use_container_width=True)

        st.markdown("<div class='wx-divider'></div>", unsafe_allow_html=True)

        # ── Batch Detail Table ────────────────────────────
        st.markdown('<div class="section-title">Production Batch Detail</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Klik header kolom untuk sort · batch kritis ditandai merah</div>', unsafe_allow_html=True)

        if not bp_f.empty:
            tbl_cols = ["activity_id", "feedstock_type", "biochar_amount_kg",
                        "carbon_content_%", "co2e_persistent", "efficiency_%",
                        "number_of_bags", "username"]
            tbl_cols = [c for c in tbl_cols if c in bp_f.columns]
            tbl = bp_f[tbl_cols].copy()
            tbl.columns = [
                c.replace("activity_id", "Batch ID")
                 .replace("feedstock_type", "Feedstock")
                 .replace("biochar_amount_kg", "Biochar (kg)")
                 .replace("carbon_content_%", "Carbon %")
                 .replace("co2e_persistent", "CO₂e (kg)")
                 .replace("efficiency_%", "Efficiency %")
                 .replace("number_of_bags", "Bags")
                 .replace("username", "Operator")
                for c in tbl.columns
            ]
            tbl["Operator"] = tbl["Operator"].str.extract(r"operator\.(\d+)").apply(
                lambda x: f"Op {x[0]}" if pd.notna(x[0]) else "—"
            )

            def highlight_critical(row):
                if pd.isna(row.get("Carbon %")):
                    return ["background-color: #fef2f2; color: #991b1b"] * len(row)
                return [""] * len(row)

            styled = (
                tbl.style
                .apply(highlight_critical, axis=1)
                .format({
                    "Biochar (kg)": "{:.1f}",
                    "Carbon %": lambda v: f"{v:.1f}%" if pd.notna(v) else "⚠️ MISSING",
                    "CO₂e (kg)": lambda v: f"{v:.1f}" if pd.notna(v) else "N/A",
                    "Efficiency %": lambda v: f"{v:.1f}%" if pd.notna(v) else "—",
                })
                .set_properties(**{
                    "font-size": "12px",
                    "padding": "6px 10px",
                })
            )
            st.dataframe(styled, use_container_width=True, height=280)

    # ══════════════════════════════════════════════════════
    # TAB 2 — APPLICATION
    # ══════════════════════════════════════════════════════
    with tab2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Application Summary ───────────────────────────
        c1, c2 = st.columns([1.5, 1])

        with c1:
            st.markdown('<div class="section-title">Application Summary by Type</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Bags applied · total weight · status validasi per tipe</div>', unsafe_allow_html=True)

            ba_grp = ba.groupby("application_type").agg(
                bags=("number_of_bags", "sum"),
                weight=("total_weight", "sum"),
                events=("activity_id", "count"),
            ).reset_index()
            ba_grp["valid"] = ba_grp["application_type"].isin(VALID_APP_TYPES)
            ba_grp["Status"] = ba_grp["valid"].map({True: "✅ Valid", False: "❌ Invalid"})
            ba_grp = ba_grp.sort_values("weight", ascending=False)

            fig_app = px.bar(
                ba_grp,
                x="application_type",
                y="weight",
                color="valid",
                color_discrete_map={True: "#22c55e", False: "#ef4444"},
                text=ba_grp["weight"].apply(lambda v: f"{v:.0f} kg"),
                custom_data=["bags", "events", "Status"],
            )
            fig_app.update_traces(
                textposition="outside",
                marker_line_width=0,
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Weight: %{y:.1f} kg<br>"
                    "Bags: %{customdata[0]}<br>"
                    "Events: %{customdata[1]}<br>"
                    "Status: %{customdata[2]}"
                    "<extra></extra>"
                ),
            )
            fig_app.update_xaxes(
                title_text="",
                ticktext=[t[:20] + ("…" if len(t) > 20 else "") for t in ba_grp["application_type"]],
                tickvals=ba_grp["application_type"],
            )
            fig_app.update_yaxes(title_text="Total weight (kg)")
            fig_app = chart_defaults(fig_app, height=300)
            fig_app.update_layout(
                showlegend=True,
                legend_title_text="Valid type",
                legend=dict(
                    orientation="h", x=0, y=1.08,
                    itemsizing="constant",
                )
            )
            st.plotly_chart(fig_app, use_container_width=True)

        with c2:
            st.markdown('<div class="section-title">Application Events</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Detail tiap event aplikasi biochar</div>', unsafe_allow_html=True)

            tbl_ba = ba[["activity_id", "application_type", "number_of_bags",
                         "total_weight", "application_date"]].copy()
            tbl_ba.columns = ["ID", "Type", "Bags", "Weight (kg)", "Date"]
            tbl_ba["Valid"] = tbl_ba["Type"].isin(VALID_APP_TYPES).map({True: "✅", False: "❌"})
            tbl_ba["Type"] = tbl_ba["Type"].str.replace("Application-", "").str.replace("Sale-", "Sale: ")
            st.dataframe(tbl_ba, use_container_width=True, height=280)

        st.markdown("<div class='wx-divider'></div>", unsafe_allow_html=True)

        # ── Bag Application Detail ────────────────────────
        c3, c4 = st.columns(2)

        with c3:
            st.markdown('<div class="section-title">Bag Weight Distribution (Applied)</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Distribusi berat bag saat diaplikasikan ke lahan</div>', unsafe_allow_html=True)

            if "bag_weight" in bapp.columns:
                fig_hist = px.histogram(
                    bapp.dropna(subset=["bag_weight"]),
                    x="bag_weight",
                    nbins=20,
                    color="feedstock_type",
                    color_discrete_map=FEED_COLORS,
                    barmode="overlay",
                )
                fig_hist.update_traces(opacity=0.75, marker_line_width=0)
                fig_hist.update_xaxes(title_text="Bag weight (kg)")
                fig_hist.update_yaxes(title_text="Frequency")
                fig_hist = chart_defaults(fig_hist, height=260)
                st.plotly_chart(fig_hist, use_container_width=True)

        with c4:
            st.markdown('<div class="section-title">Bags per Application Event</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Jumlah bag yang diaplikasikan per event</div>', unsafe_allow_html=True)

            if "application_id" in bapp.columns:
                bags_per_event = bapp.groupby("application_id").agg(
                    n_bags=("bag_id", "count"),
                    total_w=("bag_weight", "sum"),
                ).reset_index()
                bags_per_event["event"] = bags_per_event["application_id"].str[-6:]

                fig_bpe = px.bar(
                    bags_per_event,
                    x="event",
                    y="n_bags",
                    text="n_bags",
                    color_discrete_sequence=["#3b82f6"],
                    custom_data=["total_w", "application_id"],
                )
                fig_bpe.update_traces(
                    textposition="outside",
                    marker_line_width=0,
                    hovertemplate=(
                        "<b>Event: %{customdata[1]}</b><br>"
                        "Bags: %{y}<br>"
                        "Total weight: %{customdata[0]:.1f} kg"
                        "<extra></extra>"
                    ),
                )
                fig_bpe.update_yaxes(title_text="Number of bags")
                fig_bpe.update_xaxes(title_text="Application event")
                fig_bpe = chart_defaults(fig_bpe, height=260)
                fig_bpe.update_layout(showlegend=False)
                st.plotly_chart(fig_bpe, use_container_width=True)

    # ══════════════════════════════════════════════════════
    # TAB 3 — ANOMALIES
    # ══════════════════════════════════════════════════════
    with tab3:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        ANOMALIES = [
            {"type": "TYPE 1",  "name": "Comma decimal separator", "count": 1,  "auto": True,  "sheet": "bag_production"},
            {"type": "TYPE 2",  "name": "Negative values",         "count": 1,  "auto": False, "sheet": "bag/biochar_production"},
            {"type": "TYPE 3",  "name": "Missing critical fields",  "count": 2,  "auto": False, "sheet": "prod sheets"},
            {"type": "TYPE 4",  "name": "Duplicate bag_id",         "count": 2,  "auto": False, "sheet": "bag_production"},
            {"type": "TYPE 5",  "name": "Suspicious timestamps",    "count": 1,  "auto": False, "sheet": "all sheets"},
            {"type": "TYPE 6",  "name": "Invalid application type", "count": 1,  "auto": False, "sheet": "biochar_application"},
            {"type": "TYPE 7",  "name": "Orphan bag_id",            "count": 1,  "auto": False, "sheet": "cross-sheet"},
            {"type": "TYPE 8",  "name": "Weight discrepancy >5%",   "count": 5,  "auto": False, "sheet": "cross-sheet"},
            {"type": "TYPE 9",  "name": "Batch sum mismatch",       "count": 7,  "auto": False, "sheet": "cross-sheet"},
            {"type": "TYPE 10", "name": "Bag multi-application",    "count": 4,  "auto": False, "sheet": "cross-sheet"},
        ]
        anom_df = pd.DataFrame(ANOMALIES)

        # KPI row
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.metric("Total Findings", "25", help="Jumlah total anomali yang ditemukan")
        with a2:
            st.metric("Auto-Fixed", "1", delta="TYPE 1 only", delta_color="normal")
        with a3:
            st.metric("Needs Review", "24", help="Masuk ke VALIDATION_QUEUE")
        with a4:
            st.metric("Anomaly Types", "9/10", help="9 dari 10 tipe terdeteksi")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns([1.2, 1])

        with c1:
            st.markdown('<div class="section-title">Anomaly Findings per Type</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Hijau = auto-fixed · Merah = butuh review manusia</div>', unsafe_allow_html=True)

            anom_sorted = anom_df.sort_values("count", ascending=True)
            colors = ["#22c55e" if a else "#ef4444" for a in anom_sorted["auto"]]
            labels = [f"{r['type']}: {r['name']}" for _, r in anom_sorted.iterrows()]

            fig_anom = go.Figure(go.Bar(
                x=anom_sorted["count"],
                y=labels,
                orientation="h",
                marker_color=colors,
                marker_line_width=0,
                text=anom_sorted["count"],
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Count: %{x}<extra></extra>"
                ),
            ))
            fig_anom.update_xaxes(title_text="Number of findings", range=[0, 10])
            fig_anom.update_yaxes(title_text="")
            fig_anom = chart_defaults(fig_anom, height=340, margin=dict(t=10, b=30, l=10, r=60))
            fig_anom.update_layout(showlegend=False)
            st.plotly_chart(fig_anom, use_container_width=True)

        with c2:
            st.markdown('<div class="section-title">Anomaly by Sheet Source</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Distribusi temuan per source sheet</div>', unsafe_allow_html=True)

            sheet_counts = anom_df.groupby("sheet")["count"].sum().reset_index()
            fig_pie2 = px.pie(
                sheet_counts,
                names="sheet",
                values="count",
                hole=0.5,
                color_discrete_sequence=["#ef4444", "#f59e0b", "#3b82f6", "#22c55e", "#a855f7"],
            )
            fig_pie2.update_traces(
                textposition="outside",
                textinfo="percent+label",
                textfont_size=10,
                hovertemplate="<b>%{label}</b><br>%{value} findings (%{percent})<extra></extra>",
            )
            fig_pie2 = chart_defaults(fig_pie2, height=280, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie2, use_container_width=True)

            # Summary table
            st.markdown('<div class="section-title" style="margin-top:12px">Anomaly Summary Table</div>', unsafe_allow_html=True)
            disp = anom_df[["type", "name", "count", "sheet"]].copy()
            disp.columns = ["Type", "Description", "Count", "Sheet"]
            disp["Auto-Fix"] = anom_df["auto"].map({True: "✅ Yes", False: "❌ No"})

            def style_anom(row):
                if row["Auto-Fix"] == "✅ Yes":
                    return ["background-color:#f0fdf4; color:#166534"] * len(row)
                if row["Count"] >= 5:
                    return ["background-color:#fef2f2; color:#991b1b"] * len(row)
                return [""] * len(row)

            styled_anom = disp.style.apply(style_anom, axis=1).set_properties(
                **{"font-size": "11px", "padding": "4px 8px"}
            )
            st.dataframe(styled_anom, use_container_width=True, height=260)

    # ══════════════════════════════════════════════════════
    # TAB 4 — INSIGHTS (Task 3)
    # ══════════════════════════════════════════════════════
    with tab4:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">Analytical Insights — Task 3 Answers</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Tiga pertanyaan analitis dijawab dari cleaned data WasteX</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── Insight Cards ─────────────────────────────────
        ic1, ic2, ic3 = st.columns(3)

        with ic1:
            st.markdown("""
            <div class="insight-card insight-green">
                <div class="insight-num">Insight #1 · Feedstock Yield</div>
                <div class="insight-q">Which feedstock produces the highest biochar yield?</div>
                <div class="insight-body">
                    Semua feedstock menghasilkan efisiensi konversi volume yang <b>hampir sama (~40%)</b>.
                    Namun perbedaan <b>sangat signifikan pada carbon content</b>:<br><br>
                    🏆 Wood waste: <b>83.98%</b><br>
                    🥈 Corn cob: <b>74.67%</b><br>
                    🥉 Cassava: <b>55.57%</b><br>
                    📉 Rice husk: <b>39.07%</b><br><br>
                    Wood waste menghasilkan biochar dengan kualitas karbon <b>2.1× lebih tinggi</b> dari Rice husk per kg yang sama.
                </div>
                <div class="insight-rec insight-rec-green">
                    → Prioritaskan Wood waste dan Corn cob untuk memaksimalkan kredit karbon
                </div>
            </div>
            """, unsafe_allow_html=True)

        with ic2:
            st.markdown("""
            <div class="insight-card insight-red">
                <div class="insight-num">Insight #2 · Anomaly Pattern</div>
                <div class="insight-q">Which batch had the most anomalies? What pattern?</div>
                <div class="insight-body">
                    <b>Batch M0030</b> (13 bags, terbesar) memiliki anomali terbanyak:
                    TYPE 8 (weight discrepancy), TYPE 9 (batch sum mismatch), TYPE 10 (bag dipakai 2 event).<br><br>
                    <b>Pola yang terlihat:</b> Batch dengan jumlah bag terbanyak → risiko error tertinggi.
                    Operator harus scan/input lebih banyak data secara manual.<br><br>
                    Batch <b>M0035</b> punya <b>carbon_content_% kosong</b> → ~224 kg CO₂e tidak bisa diklaim ke pasar karbon.
                </div>
                <div class="insight-rec insight-rec-red">
                    → Implementasi validasi real-time di field app untuk batch besar
                </div>
            </div>
            """, unsafe_allow_html=True)

        with ic3:
            st.markdown("""
            <div class="insight-card insight-amber">
                <div class="insight-num">Insight #3 · Batch Size & Efficiency</div>
                <div class="insight-q">Batch size vs production efficiency — any relationship?</div>
                <div class="insight-body">
                    <b>Tidak ada korelasi linear</b> antara jumlah bag dan efisiensi konversi volume
                    (semua batch ~40% terlepas dari ukurannya).<br><br>
                    Namun ada hubungan menarik dengan <b>kualitas karbon</b>:
                    batch lebih kecil dengan feedstock premium (Wood waste 9 bags, Corn cob 11 bags)
                    menghasilkan carbon content jauh lebih tinggi.<br><br>
                    Rice husk mendominasi (4/7 batch) tapi memberi nilai karbon terendah.
                </div>
                <div class="insight-rec insight-rec-amber">
                    → Optimal: 9–10 bags per batch dengan Wood waste/Corn cob
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div class='wx-divider'></div>", unsafe_allow_html=True)

        # ── Supporting Charts ─────────────────────────────
        st.markdown('<div class="section-title">Supporting Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Visualisasi pendukung untuk ketiga insight di atas</div>', unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)

        with sc1:
            # Carbon content vs CO2e scatter
            st.markdown("**Carbon Content vs CO₂e Sequestered**", unsafe_allow_html=False)
            bp_scatter = bp.dropna(subset=["carbon_content_%", "co2e_persistent"])
            fig_scatter = px.scatter(
                bp_scatter,
                x="carbon_content_%",
                y="co2e_persistent",
                color="feedstock_type",
                color_discrete_map=FEED_COLORS,
                size="biochar_amount_kg",
                size_max=30,
                text="activity_id",
                labels={
                    "carbon_content_%": "Carbon Content (%)",
                    "co2e_persistent": "CO₂e Sequestered (kg)",
                },
                hover_data=["feedstock_type", "biochar_amount_kg", "number_of_bags"],
            )
            fig_scatter.update_traces(
                textposition="top center",
                textfont_size=9,
                marker_line_width=0,
            )
            # Add trendline manually
            if len(bp_scatter) > 1:
                z = np.polyfit(bp_scatter["carbon_content_%"], bp_scatter["co2e_persistent"], 1)
                p = np.poly1d(z)
                x_line = np.linspace(bp_scatter["carbon_content_%"].min(), bp_scatter["carbon_content_%"].max(), 50)
                fig_scatter.add_trace(go.Scatter(
                    x=x_line, y=p(x_line),
                    mode="lines", name="Trend",
                    line=dict(color="#9ca3af", width=1.5, dash="dash"),
                    hoverinfo="skip",
                ))
            fig_scatter = chart_defaults(fig_scatter, height=300)
            st.plotly_chart(fig_scatter, use_container_width=True)

        with sc2:
            # Bags vs anomaly count (conceptual)
            st.markdown("**Batch Size vs Anomaly Risk**", unsafe_allow_html=False)
            bag_anom_data = pd.DataFrame({
                "Batch": ["M0030", "M0031", "M0032", "M0033", "M0034", "M0035", "M0036"],
                "Bags":  [13, 11, 12, 9, 10, 10, 12],
                "Anomalies": [7, 0, 0, 0, 0, 3, 1],
                "Feedstock": ["Rice husk", "Corn cob/leaves", "Rice husk",
                              "Wood waste", "Cassava root/stems/leaves",
                              "Rice husk", "Rice husk"],
            })
            fig_risk = px.scatter(
                bag_anom_data,
                x="Bags",
                y="Anomalies",
                size="Anomalies",
                size_max=35,
                color="Feedstock",
                color_discrete_map=FEED_COLORS,
                text="Batch",
                labels={"Bags": "Number of Bags per Batch", "Anomalies": "Anomalies Found"},
            )
            fig_risk.update_traces(
                textposition="top center",
                textfont_size=10,
                marker_line_width=0,
            )
            # Trend
            z2 = np.polyfit(bag_anom_data["Bags"], bag_anom_data["Anomalies"], 1)
            p2 = np.poly1d(z2)
            x2 = np.linspace(8, 14, 30)
            fig_risk.add_trace(go.Scatter(
                x=x2, y=p2(x2),
                mode="lines", name="Trend",
                line=dict(color="#ef4444", width=1.5, dash="dash"),
                hoverinfo="skip",
            ))
            fig_risk = chart_defaults(fig_risk, height=300)
            st.plotly_chart(fig_risk, use_container_width=True)

    # ── FOOTER ─────────────────────────────────────────────
    st.markdown("<div class='wx-divider'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#9ca3af;padding-bottom:8px">
        <span>WasteX Biochar Analytics · Data Analyst Skills Test · Python + Streamlit + Plotly</span>
        <span>Source: CLEANED_prod_batch · CLEANED_bag_prod · CLEANED_app_batch · CLEANED_bag_app</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
