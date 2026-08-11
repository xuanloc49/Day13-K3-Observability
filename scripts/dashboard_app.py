"""Day 13 observability dashboard — 6 panels from data/logs.jsonl.

Run:
  pip install -r requirements-dashboard.txt
  streamlit run scripts/dashboard_app.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "data" / "logs.jsonl"
CONTRACT_PATH = ROOT / "config" / "dashboard.yaml"


def load_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)["dashboard"]


def load_logs(path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    if not path.exists():
        return pd.DataFrame()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


def filter_window(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if df.empty or "ts" not in df.columns:
        return df
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return df[df["ts"] >= cutoff].copy()


def percentile(series: pd.Series, q: float) -> float:
    if series.empty:
        return float("nan")
    return float(series.quantile(q / 100.0))


def main() -> None:
    contract = load_contract()
    title = contract.get("title", "Day 13 AI Observability")
    minutes = int(contract.get("time_range_minutes", 60))
    refresh = int(contract.get("refresh_seconds", 30))
    panels = {p["id"]: p for p in contract["panels"]}

    st.set_page_config(page_title=title, layout="wide")
    st.markdown(f"## {title}")
    st.caption(
        f"Source: `data/logs.jsonl` · Time range: **{minutes} minutes** · "
        f"Refresh: **{refresh}s** · Contract: `config/dashboard.yaml`"
    )

    df = filter_window(load_logs(LOG_PATH), minutes)
    if df.empty:
        st.warning("No log records in window. Run API + `python scripts/load_test.py` first.")
        return

    responses = df[df["event"] == "response_sent"] if "event" in df.columns else pd.DataFrame()
    received = df[df["event"] == "request_received"] if "event" in df.columns else pd.DataFrame()
    failed = df[df["event"] == "request_failed"] if "event" in df.columns else pd.DataFrame()

    r1c1, r1c2, r1c3 = st.columns(3)

    # 1 Latency
    with r1c1:
        p = panels["latency"]
        thr = p["threshold"]["value"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: P95 {p['threshold']['operator']} **{thr} {p['unit']}**")
        if responses.empty or "latency_ms" not in responses.columns:
            st.info("No latency data")
        else:
            lat = responses["latency_ms"].dropna().astype(float)
            p50, p95, p99 = percentile(lat, 50), percentile(lat, 95), percentile(lat, 99)
            st.write(f"P50 **{p50:.0f}** · P95 **{p95:.0f}** · P99 **{p99:.0f}** ms")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=responses["ts"], y=responses["latency_ms"], mode="lines+markers", name="latency_ms"))
            fig.add_hline(y=thr, line_dash="dash", line_color="red", annotation_text=f"SLO {thr}")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="ms")
            st.plotly_chart(fig, use_container_width=True)

    # 2 Traffic
    with r1c2:
        p = panels["traffic"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: rate_per_minute >= **{p['threshold']['value']}**")
        if received.empty:
            st.info("No traffic data")
        else:
            count = len(received)
            rate = count / max(minutes, 1)
            st.write(f"Count **{count}** · avg rate **{rate:.2f}**/min")
            by_min = received.set_index("ts").resample("1min").size().rename("requests").reset_index()
            fig = px.bar(by_min, x="ts", y="requests")
            fig.add_hline(y=p["threshold"]["value"], line_dash="dash", line_color="orange")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # 3 Errors
    with r1c3:
        p = panels["errors"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: error_rate_pct <= **{p['threshold']['value']}%**")
        recv_n, fail_n = len(received), len(failed)
        rate_pct = (fail_n / recv_n * 100.0) if recv_n else 0.0
        st.write(f"Error rate **{rate_pct:.2f}%** (failed={fail_n})")
        if failed.empty or "error_type" not in failed.columns:
            fig = go.Figure(go.Indicator(mode="number", value=rate_pct, number={"suffix": "%"}))
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            breakdown = failed["error_type"].fillna("unknown").value_counts().reset_index()
            breakdown.columns = ["error_type", "count"]
            fig = px.bar(breakdown, x="error_type", y="count")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    r2c1, r2c2, r2c3 = st.columns(3)

    # 4 Cost
    with r2c1:
        p = panels["cost"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: total <= **{p['threshold']['value']} {p['unit']}**")
        if responses.empty or "cost_usd" not in responses.columns:
            st.info("No cost data")
        else:
            total = float(responses["cost_usd"].fillna(0).sum())
            st.write(f"Total **${total:.4f}**")
            by_min = responses.set_index("ts")["cost_usd"].resample("1min").sum().rename("cost_usd").reset_index()
            fig = px.line(by_min, x="ts", y="cost_usd", markers=True)
            fig.add_hline(y=p["threshold"]["value"], line_dash="dash", line_color="red")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="usd")
            st.plotly_chart(fig, use_container_width=True)

    # 5 Tokens
    with r2c2:
        p = panels["tokens"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: sum_by_field <= **{p['threshold']['value']}**")
        if responses.empty:
            st.info("No token data")
        else:
            tin = float(responses.get("tokens_in", pd.Series(dtype=float)).fillna(0).sum())
            tout = float(responses.get("tokens_out", pd.Series(dtype=float)).fillna(0).sum())
            st.write(f"in **{tin:.0f}** · out **{tout:.0f}**")
            fig = go.Figure(
                data=[
                    go.Bar(name="tokens_in", x=["sum"], y=[tin]),
                    go.Bar(name="tokens_out", x=["sum"], y=[tout]),
                ]
            )
            fig.add_hline(y=p["threshold"]["value"], line_dash="dash", line_color="orange")
            fig.update_layout(barmode="group", height=220, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

    # 6 Quality
    with r2c3:
        p = panels["quality"]
        st.markdown(f"**{p['title']} ({p['unit']})**")
        st.caption(f"Threshold: mean >= **{p['threshold']['value']}**")
        if responses.empty or "quality_score" not in responses.columns:
            st.info("No quality data")
        else:
            mean_q = float(responses["quality_score"].dropna().astype(float).mean())
            st.write(f"Mean **{mean_q:.3f}**")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(x=responses["ts"], y=responses["quality_score"], mode="lines+markers", name="quality")
            )
            fig.add_hline(y=p["threshold"]["value"], line_dash="dash", line_color="green", annotation_text="SLO 0.75")
            fig.update_layout(height=220, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="score_0_to_1")
            st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Loaded {len(df)} rows · responses={len(responses)} · {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
