import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

# Page config
st.set_page_config(
    page_title="Day 13 AI Observability Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern aesthetic UI
st.markdown(
    """
    <style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-header {
        font-size: 0.95rem;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-unit {
        font-size: 0.85rem;
        color: #64748b;
        margin-left: 4px;
    }
    .status-badge-pass {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        float: right;
    }
    .status-badge-alert {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        float: right;
    }
    .threshold-info {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

CONFIG_PATH = Path("config/dashboard.yaml")
LOG_PATH = Path("data/logs.jsonl")

@st.cache_data(ttl=5)
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("dashboard", {})
    return {}

def load_logs():
    if not LOG_PATH.exists():
        return pd.DataFrame()
    records = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "ts" in df.columns:
        df["datetime"] = pd.to_datetime(df["ts"])
    return df

# Header
config = load_config()
title = config.get("title", "Day 13 AI Observability")
time_range_min = config.get("time_range_minutes", 60)
refresh_sec = config.get("refresh_seconds", 30)

st.title(f"🚀 {title}")
st.caption(f"⏱️ **Time Range:** Last {time_range_min} minutes | 🔄 **Auto-Refresh:** Every {refresh_sec}s | 📍 **Data Source:** `data/logs.jsonl`")

df = load_logs()

if df.empty:
    st.warning("⚠️ Chưa có dữ liệu log trong `data/logs.jsonl`. Vui lòng chạy API và `python scripts/load_test.py` để tạo dữ liệu!")
    st.stop()

# Filter by time range if available
now = pd.Timestamp.now(tz="UTC")
cutoff = now - pd.Timedelta(minutes=time_range_min)
if "datetime" in df.columns:
    df_filtered = df[df["datetime"] >= cutoff]
    if df_filtered.empty:
        df_filtered = df  # fallback to all data if none within timeframe
else:
    df_filtered = df

# Extract events
resp_df = df_filtered[df_filtered["event"] == "response_sent"] if "event" in df_filtered.columns else pd.DataFrame()
req_df = df_filtered[df_filtered["event"] == "request_received"] if "event" in df_filtered.columns else pd.DataFrame()
fail_df = df_filtered[df_filtered["event"] == "request_failed"] if "event" in df_filtered.columns else pd.DataFrame()

# Create 6 Panels Layout (2 rows x 3 cols)
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

# -------------------------------------------------------------
# PANEL 1: Latency percentiles
# -------------------------------------------------------------
with col1:
    p50, p95, p99 = 0, 0, 0
    if not resp_df.empty and "latency_ms" in resp_df.columns:
        p50 = float(resp_df["latency_ms"].quantile(0.50))
        p95 = float(resp_df["latency_ms"].quantile(0.95))
        p99 = float(resp_df["latency_ms"].quantile(0.99))
    
    threshold_val = 3000
    is_alert = p95 > threshold_val
    badge = f'<span class="{"status-badge-alert" if is_alert else "status-badge-pass"}">{"ALERT: P95 > 3000ms" if is_alert else "SLO OK"}</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">1. Latency Percentiles</span>{badge}</div>
            <div class="metric-value">{p95:.1f}<span class="metric-unit">ms (P95)</span></div>
            <div class="threshold-info"><b>P50:</b> {p50:.1f} ms | <b>P99:</b> {p99:.1f} ms<br><b>Threshold:</b> P95 ≤ 3000 ms</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not resp_df.empty and "latency_ms" in resp_df.columns and "datetime" in resp_df.columns:
        fig_lat = px.line(
            resp_df, x="datetime", y="latency_ms",
            title="Latency over Time (ms)",
            color_discrete_sequence=["#38bdf8"]
        )
        fig_lat.add_hline(y=3000, line_dash="dash", line_color="#ef4444", annotation_text="P95 Threshold (3000ms)")
        fig_lat.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
        st.plotly_chart(fig_lat, use_container_width=True)

# -------------------------------------------------------------
# PANEL 2: Request traffic
# -------------------------------------------------------------
with col2:
    total_reqs = len(req_df)
    # Rate per minute
    if not req_df.empty and "datetime" in req_df.columns:
        time_span_min = max(1.0, (req_df["datetime"].max() - req_df["datetime"].min()).total_seconds() / 60.0)
        rpm = total_reqs / time_span_min
    else:
        rpm = float(total_reqs)
        
    badge = '<span class="status-badge-pass">TRAFFIC OK</span>' if rpm >= 1 else '<span class="status-badge-alert">LOW TRAFFIC</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">2. Request Traffic</span>{badge}</div>
            <div class="metric-value">{rpm:.1f}<span class="metric-unit">reqs/min</span></div>
            <div class="threshold-info"><b>Total Requests:</b> {total_reqs}<br><b>Threshold:</b> rate_per_minute ≥ 1</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not req_df.empty and "datetime" in req_df.columns:
        req_df_copy = req_df.copy()
        req_df_copy.set_index("datetime", inplace=True)
        traffic_min = req_df_copy.resample("1min").size().reset_index(name="count")
        fig_trf = px.bar(
            traffic_min, x="datetime", y="count",
            title="Requests per Minute",
            color_discrete_sequence=["#818cf8"]
        )
        fig_trf.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
        st.plotly_chart(fig_trf, use_container_width=True)

# -------------------------------------------------------------
# PANEL 3: Error rate and breakdown
# -------------------------------------------------------------
with col3:
    num_reqs = len(req_df)
    num_fails = len(fail_df)
    err_rate = (num_fails / num_reqs * 100) if num_reqs > 0 else 0.0
    
    badge = '<span class="status-badge-pass">PASS</span>' if err_rate <= 2.0 else '<span class="status-badge-alert">HIGH ERROR</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">3. Error Rate & Breakdown</span>{badge}</div>
            <div class="metric-value">{err_rate:.2f}<span class="metric-unit">%</span></div>
            <div class="threshold-info"><b>Failed Requests:</b> {num_fails} / {num_reqs}<br><b>Threshold:</b> error_rate_pct ≤ 2%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not fail_df.empty and "error_type" in fail_df.columns:
        err_counts = fail_df["error_type"].value_counts().reset_index()
        err_counts.columns = ["error_type", "count"]
        fig_err = px.pie(err_counts, values="count", names="error_type", title="Error Breakdown", color_discrete_sequence=px.colors.qualitative.Pastel)
    else:
        fig_err = go.Figure()
        fig_err.add_annotation(text="0 Errors (100% Success)", showarrow=False, font=dict(size=14, color="#34d399"))
        fig_err.update_layout(title="Error Breakdown")
        
    fig_err.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
    st.plotly_chart(fig_err, use_container_width=True)

# -------------------------------------------------------------
# PANEL 4: Cost over time
# -------------------------------------------------------------
with col4:
    total_cost = float(resp_df["cost_usd"].sum()) if not resp_df.empty and "cost_usd" in resp_df.columns else 0.0
    badge = '<span class="status-badge-pass">COST OK</span>' if total_cost <= 2.5 else '<span class="status-badge-alert">COST SPIKE</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">4. Cost Over Time</span>{badge}</div>
            <div class="metric-value">${total_cost:.4f}<span class="metric-unit">USD</span></div>
            <div class="threshold-info"><b>Total USD:</b> ${total_cost:.4f}<br><b>Threshold:</b> total ≤ $2.50</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not resp_df.empty and "cost_usd" in resp_df.columns and "datetime" in resp_df.columns:
        resp_df_copy = resp_df.copy()
        resp_df_copy.set_index("datetime", inplace=True)
        cost_min = resp_df_copy.resample("1min")["cost_usd"].sum().reset_index()
        fig_cost = px.area(
            cost_min, x="datetime", y="cost_usd",
            title="Cost per Minute (USD)",
            color_discrete_sequence=["#34d399"]
        )
        fig_cost.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
        st.plotly_chart(fig_cost, use_container_width=True)

# -------------------------------------------------------------
# PANEL 5: Input and output tokens
# -------------------------------------------------------------
with col5:
    tokens_in = int(resp_df["tokens_in"].sum()) if not resp_df.empty and "tokens_in" in resp_df.columns else 0
    tokens_out = int(resp_df["tokens_out"].sum()) if not resp_df.empty and "tokens_out" in resp_df.columns else 0
    total_tokens = tokens_in + tokens_out
    
    badge = '<span class="status-badge-pass">TOKENS OK</span>' if total_tokens <= 50000 else '<span class="status-badge-alert">TOKEN OVERFLOW</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">5. Input & Output Tokens</span>{badge}</div>
            <div class="metric-value">{total_tokens:,}<span class="metric-unit">tokens</span></div>
            <div class="threshold-info"><b>In:</b> {tokens_in:,} | <b>Out:</b> {tokens_out:,}<br><b>Threshold:</b> total ≤ 50,000</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    token_data = pd.DataFrame({
        "Type": ["Tokens In", "Tokens Out"],
        "Count": [tokens_in, tokens_out]
    })
    fig_tok = px.bar(token_data, x="Type", y="Count", color="Type", title="Token Usage Breakdown", color_discrete_sequence=["#a78bfa", "#f472b6"])
    fig_tok.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
    st.plotly_chart(fig_tok, use_container_width=True)

# -------------------------------------------------------------
# PANEL 6: Quality proxy
# -------------------------------------------------------------
with col6:
    mean_quality = float(resp_df["quality_score"].mean()) if not resp_df.empty and "quality_score" in resp_df.columns else 0.0
    badge = '<span class="status-badge-pass">QUALITY OK</span>' if mean_quality >= 0.75 else '<span class="status-badge-alert">LOW QUALITY</span>'
    
    st.markdown(
        f"""
        <div class="metric-card">
            <div><span class="metric-header">6. Quality Proxy</span>{badge}</div>
            <div class="metric-value">{mean_quality:.2f}<span class="metric-unit">score</span></div>
            <div class="threshold-info"><b>Range:</b> 0.0 to 1.0<br><b>Threshold:</b> mean ≥ 0.75</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not resp_df.empty and "quality_score" in resp_df.columns and "datetime" in resp_df.columns:
        fig_q = px.line(resp_df, x="datetime", y="quality_score", title="Quality Score over Time", color_discrete_sequence=["#facc15"])
        fig_q.add_hline(y=0.75, line_dash="dash", line_color="#34d399", annotation_text="SLO (0.75)")
        fig_q.update_layout(height=220, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
        st.plotly_chart(fig_q, use_container_width=True)
