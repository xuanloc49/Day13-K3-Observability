# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: A2
- Repository URL: https://github.com/xuanloc49/Day13-K3-Observability.git
- Commit SHA cuối: `d7d45b8bae348430cdf45318d1c81daaa574734d`
- Thành viên và vai trò (theo README repo):
  - Trần Xuân Lộc — **Logging & PII** (middleware, correlation ID, enrichment) — PR [#1](https://github.com/xuanloc49/Day13-K3-Observability/pull/1)
  - Đào Ngọc Bích — **Logging & PII** (PII) + prompt versioning evidence — PR [#2](https://github.com/xuanloc49/Day13-K3-Observability/pull/2), [#6](https://github.com/xuanloc49/Day13-K3-Observability/pull/6)
  - Ngô Tuấn Hưng — **Tracing & Prompt Version**; **Dashboard, SLO & Alert** — PR [#3](https://github.com/xuanloc49/Day13-K3-Observability/pull/3), [#5](https://github.com/xuanloc49/Day13-K3-Observability/pull/5)
  - Vũ Đức Anh — **Incident, Report & Demo** — PR [#4](https://github.com/xuanloc49/Day13-K3-Observability/pull/4)

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
  - Baseline CP0: **30/100** (`submission/evidence/logs_cp0_baseline.jsonl`, `validate_logs_baseline_note.txt`)
  - Sau Logging & PII (CP1): **100/100** (`submission/evidence/validate_logs.txt`)
- Tổng số traces: ≥10 load-test + prompt versioning + 5 challenge traces trên Langfuse (xem mục 4 và 6)
- Số PII leak còn lại: **0** theo validator + kiểm tra thủ công (email/phone/thẻ/CCCD/hộ chiếu/địa chỉ VN)
- Link/đường dẫn dashboard:
  - Contract `config/dashboard.yaml` + validator **6/6** (`submission/evidence/validate_dashboard.txt`)
  - Ảnh: `submission/evidence/dashboard_6_panels.png`, `submission/evidence/dashboard_after_rag_slow.png`
  - (Streamlit app nhóm D): `scripts/dashboard_app.py`, ảnh phụ `dashboard_6_panels_streamlit.png`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/log_correlation_and_enrichment_sample.jsonl`
- Evidence PII redaction: `submission/evidence/log_pii_redaction_sample.jsonl`
- Evidence trace waterfall: `submission/evidence/langfuse_trace_waterfall_sample.json`
  - Challenge sample: `6e122576146c87f9e5bb4830fef965b1` (session `k3-challenge-s04`)
- Giải thích span: generation `run` ~3.8s khi `rag_slow` — khớp metrics/log; chậm trên đường agent, không phải HTTP 5xx

## 4. Prompt versioning

- Prompt name: `day13-chat` (type `text`)
- Version/label baseline: **v1** — `baseline` + `production`
- Version/label candidate: **v2** — `candidate` (+ câu `Answer in at most 2 concise sentences.`)
- Trace ID (project hiện tại / evidence file `prompt_trace_ids.txt`):
  - `ed3506b0f82ad1921e2ec0763a1d079e` — `sess-baseline` — label `baseline`, version `1`
  - `1c287fc4737c7de5f8648b8b853f4b47` — `sess-candidate` — label `candidate`, version `2`
- Đổi label / rollback:
  - production→v2: `30a16872ac5e66a801f40e2175f99d10`
  - production→v1 (fresh process): `9048fc2c8eb071683acf5b2f9e1e6abc`
- Screenshot UI (PR #6):
  - `submission/evidence/Prompt_version_lis.png`
  - `submission/evidence/prompt_traces_baseline_vs_candidate - 1.png`
  - `submission/evidence/prompt_traces_baseline_vs_candidate - 2.png`
  - `submission/evidence/prompt_production_rollback_1.png`
  - `submission/evidence/prompt_production_rollback_2.png`
- Ghi chú: đổi label trên server có hiệu lực ngay; SDK client có cache (`cache_ttl_seconds=60`) — rollback cần restart process để chắc chắn

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**
- Evidence dashboard:
  - `submission/evidence/dashboard_6_panels.png` — baseline 6 panel theo contract
  - `submission/evidence/dashboard_after_rag_slow.png` — sau `rag_slow`, P95 tăng rõ / vượt SLO 3000ms
- SLO (`config/slo.yaml`): latency P95 ≤ 3000ms; error_rate ≤ 2%; daily_cost ≤ 2.5 USD; quality ≥ 0.75
- Alert/runbook: `config/alert_rules.yaml` + `docs/alerts.md` (HighLatencyP95, HighErrorRate, LowQualityScore)

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (incident `rag_slow`, feature `refund`, threshold 2000ms)
- Triệu chứng metrics (`challenge_metrics.json`): `latency_p95=3833ms`, không có error 5xx — triệu chứng **chậm**
- Trace IDs: `submission/evidence/challenge_trace_ids.txt` (ví dụ `6e122576146c87f9e5bb4830fef965b1`)
- Log/CID: `req-4be5226c`, `feature=refund`, `latency_ms=3833` (`challenge_log_line.jsonl`)
- Root cause: `rag_slow=true` → `app/mock_rag.py` `time.sleep(2.5)` trong `retrieve()`
- Fix: `POST /incidents/rag_slow/disable`; timeout/fallback retrieve; tách span retrieve/generate
- Preventive: alert HighLatencyP95; monitor theo feature; không để incident giả lập bật khi demo
- Demo: `submission/evidence/DEMO_SCRIPT.md`

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Trần Xuân Lộc | Logging & PII — middleware, correlation ID | [PR #1](https://github.com/xuanloc49/Day13-K3-Observability/pull/1) | |
| Đào Ngọc Bích | PII + prompt UI evidence | [PR #2](https://github.com/xuanloc49/Day13-K3-Observability/pull/2), [#6](https://github.com/xuanloc49/Day13-K3-Observability/pull/6) | |
| Ngô Tuấn Hưng | Dashboard/SLO/alert + ảnh runtime | [PR #3](https://github.com/xuanloc49/Day13-K3-Observability/pull/3), [#5](https://github.com/xuanloc49/Day13-K3-Observability/pull/5) | |
| Vũ Đức Anh | Incident/Report/Demo — challenge, evidence, REPORT | [PR #4](https://github.com/xuanloc49/Day13-K3-Observability/pull/4) | Metrics → traces → logs chứng minh `rag_slow` |
