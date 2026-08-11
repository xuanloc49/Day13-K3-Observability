import json
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import yaml

plt.style.use("dark_background")

CONFIG_PATH = Path("config/dashboard.yaml")
LOG_PATH = Path("data/logs.jsonl")
EVIDENCE_DIR = Path("submission/evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


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


def render_dashboard(output_filename: str):
    df = load_logs()
    
    # Filter 60 min if timestamps exist
    if not df.empty and "datetime" in df.columns:
        now = df["datetime"].max()
        cutoff = now - pd.Timedelta(minutes=60)
        df_filtered = df[df["datetime"] >= cutoff]
    else:
        df_filtered = df

    resp_df = df_filtered[df_filtered["event"] == "response_sent"] if not df_filtered.empty and "event" in df_filtered.columns else pd.DataFrame()
    req_df = df_filtered[df_filtered["event"] == "request_received"] if not df_filtered.empty and "event" in df_filtered.columns else pd.DataFrame()
    fail_df = df_filtered[df_filtered["event"] == "request_failed"] if not df_filtered.empty and "event" in df_filtered.columns else pd.DataFrame()

    # Figure setup
    fig = plt.figure(figsize=(16, 10), facecolor="#0f172a")
    fig.suptitle("Day 13 AI Observability — Dashboard 6 Panels", fontsize=20, fontweight="bold", color="#f8fafc", y=0.97)
    
    # Subtitle info
    plt.figtext(
        0.5, 0.935,
        "Time Range: Last 60 Minutes | Refresh Interval: 30s | Data Source: data/logs.jsonl",
        ha="center", fontsize=11, color="#94a3b8"
    )

    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.25, left=0.06, right=0.94, top=0.90, bottom=0.07)

    # Colors
    CARD_BG = "#1e293b"
    BORDER_COLOR = "#334155"
    TEXT_MUTED = "#94a3b8"
    PASS_COLOR = "#10b981"
    ALERT_COLOR = "#ef4444"

    # Helper styling function
    def style_ax(ax, title, status_text, is_alert):
        ax.set_facecolor(CARD_BG)
        for spine in ax.spines.values():
            spine.set_color(BORDER_COLOR)
            spine.set_linewidth(1.5)
        
        status_c = ALERT_COLOR if is_alert else PASS_COLOR
        ax.set_title(f"{title}  [{status_text}]", fontsize=12, fontweight="bold", color=status_c, pad=10, loc="left")
        ax.tick_params(colors=TEXT_MUTED, labelsize=9)
        ax.grid(True, linestyle="--", alpha=0.2, color="#64748b")

    # -------------------------------------------------------------
    # PANEL 1: Latency percentiles
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    p50, p95, p99 = 0, 0, 0
    if not resp_df.empty and "latency_ms" in resp_df.columns:
        p50 = resp_df["latency_ms"].quantile(0.50)
        p95 = resp_df["latency_ms"].quantile(0.95)
        p99 = resp_df["latency_ms"].quantile(0.99)
        ax1.plot(resp_df["datetime"], resp_df["latency_ms"], color="#38bdf8", marker="o", markersize=4, linewidth=1.5, label="Latency (ms)")
    
    ax1.axhline(y=3000, color=ALERT_COLOR, linestyle="--", linewidth=1.5, label="SLO Threshold (3000ms)")
    is_alert_1 = p95 > 3000
    status_1 = f"P95={p95:.1f}ms > 3000ms ALERT" if is_alert_1 else f"P50={p50:.0f}ms | P95={p95:.0f}ms (≤ 3000ms OK)"
    style_ax(ax1, "1. Latency Percentiles (ms)", status_1, is_alert_1)
    ax1.set_ylabel("ms", color=TEXT_MUTED, fontsize=9)
    ax1.legend(loc="upper left", fontsize=8, facecolor=CARD_BG, edgecolor=BORDER_COLOR)
    if not resp_df.empty and "datetime" in resp_df.columns:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    # -------------------------------------------------------------
    # PANEL 2: Request traffic
    # -------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    total_reqs = len(req_df)
    rpm = float(total_reqs)
    if not req_df.empty and "datetime" in req_df.columns:
        span_min = max(1.0, (req_df["datetime"].max() - req_df["datetime"].min()).total_seconds() / 60.0)
        rpm = total_reqs / span_min
        req_df_copy = req_df.copy()
        req_df_copy.set_index("datetime", inplace=True)
        counts = req_df_copy.resample("1min").size()
        ax2.bar(counts.index, counts.values, width=0.0005, color="#818cf8", alpha=0.8, label="reqs/min")

    is_alert_2 = rpm < 1.0
    status_2 = f"Rate={rpm:.1f} reqs/min (≥ 1 reqs/min OK)"
    style_ax(ax2, "2. Request Traffic (reqs/min)", status_2, is_alert_2)
    ax2.set_ylabel("requests_per_minute", color=TEXT_MUTED, fontsize=9)
    if not req_df.empty and "datetime" in req_df.columns:
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    # -------------------------------------------------------------
    # PANEL 3: Error rate and breakdown
    # -------------------------------------------------------------
    ax3 = fig.add_subplot(gs[0, 2])
    num_reqs = len(req_df)
    num_fails = len(fail_df)
    err_rate = (num_fails / num_reqs * 100) if num_reqs > 0 else 0.0
    is_alert_3 = err_rate > 2.0
    status_3 = f"Error Rate={err_rate:.1f}% (≤ 2% OK)"
    style_ax(ax3, "3. Error Rate & Breakdown (%)", status_3, is_alert_3)
    
    if not fail_df.empty and "error_type" in fail_df.columns:
        err_counts = fail_df["error_type"].value_counts()
        ax3.pie(err_counts.values, labels=err_counts.index, autopct="%1.1f%%", colors=["#f472b6", "#fbbf24", "#a78bfa"])
    else:
        ax3.text(0.5, 0.5, "0 Errors Detected (100% Success)", ha="center", va="center", color=PASS_COLOR, fontsize=11, fontweight="bold")
        ax3.set_xticks([])
        ax3.set_yticks([])

    # -------------------------------------------------------------
    # PANEL 4: Cost over time
    # -------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 0])
    total_cost = resp_df["cost_usd"].sum() if not resp_df.empty and "cost_usd" in resp_df.columns else 0.0
    is_alert_4 = total_cost > 2.50
    status_4 = f"Total Cost=${total_cost:.4f} USD (≤ $2.50 OK)"
    style_ax(ax4, "4. Cost Over Time (USD)", status_4, is_alert_4)
    
    if not resp_df.empty and "cost_usd" in resp_df.columns and "datetime" in resp_df.columns:
        resp_df_copy = resp_df.copy()
        resp_df_copy.set_index("datetime", inplace=True)
        cost_min = resp_df_copy.resample("1min")["cost_usd"].sum()
        ax4.plot(cost_min.index, cost_min.values, color="#34d399", marker="s", markersize=4, linewidth=1.5, label="Cost/min")
        ax4.fill_between(cost_min.index, cost_min.values, color="#34d399", alpha=0.15)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax4.set_ylabel("usd", color=TEXT_MUTED, fontsize=9)

    # -------------------------------------------------------------
    # PANEL 5: Input and output tokens
    # -------------------------------------------------------------
    ax5 = fig.add_subplot(gs[1, 1])
    tokens_in = int(resp_df["tokens_in"].sum()) if not resp_df.empty and "tokens_in" in resp_df.columns else 0
    tokens_out = int(resp_df["tokens_out"].sum()) if not resp_df.empty and "tokens_out" in resp_df.columns else 0
    total_tokens = tokens_in + tokens_out
    is_alert_5 = total_tokens > 50000
    status_5 = f"Total={total_tokens:,} tokens (≤ 50k OK)"
    style_ax(ax5, "5. Input & Output Tokens", status_5, is_alert_5)
    
    bars = ax5.bar(["Tokens In", "Tokens Out"], [tokens_in, tokens_out], color=["#a78bfa", "#f472b6"], width=0.4)
    ax5.set_ylabel("tokens", color=TEXT_MUTED, fontsize=9)
    for bar in bars:
        height = bar.get_height()
        ax5.annotate(f"{height:,}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", color="#f8fafc", fontsize=9, fontweight="bold")

    # -------------------------------------------------------------
    # PANEL 6: Quality proxy
    # -------------------------------------------------------------
    ax6 = fig.add_subplot(gs[1, 2])
    mean_q = resp_df["quality_score"].mean() if not resp_df.empty and "quality_score" in resp_df.columns else 0.0
    is_alert_6 = mean_q < 0.75
    status_6 = f"Mean Score={mean_q:.2f} (≥ 0.75 OK)"
    style_ax(ax6, "6. Quality Proxy (score_0_to_1)", status_6, is_alert_6)
    
    if not resp_df.empty and "quality_score" in resp_df.columns and "datetime" in resp_df.columns:
        ax6.plot(resp_df["datetime"], resp_df["quality_score"], color="#facc15", marker="^", markersize=4, linewidth=1.5, label="Quality Score")
        ax6.axhline(y=0.75, color=PASS_COLOR, linestyle="--", linewidth=1.5, label="SLO Threshold (0.75)")
        ax6.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax6.legend(loc="lower left", fontsize=8, facecolor=CARD_BG, edgecolor=BORDER_COLOR)
    ax6.set_ylabel("score", color=TEXT_MUTED, fontsize=9)
    ax6.set_ylim(0.0, 1.05)

    # Save to both paths
    plt.savefig(output_filename, dpi=200, bbox_inches="tight")
    plt.savefig(EVIDENCE_DIR / Path(output_filename).name, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"✅ Screenshot saved successfully: {output_filename} and submission/evidence/{Path(output_filename).name}")


if __name__ == "__main__":
    render_dashboard("dashboard_6_panels.png")
