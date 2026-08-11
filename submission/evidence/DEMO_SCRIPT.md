# Demo script — Metrics → Traces → Logs → Root cause

1. Metrics: mở `/metrics` sau challenge — `latency_p95` ≈ 3833ms (> SLO 3000ms và threshold challenge 2000ms), feature refund chậm.
2. Traces: Langfuse filter tag `refund` / session `k3-challenge-s*` — generation `run` ~3.8s.
3. Logs: `data/logs.jsonl` filter `feature=refund` và `latency_ms>=2000` — ví dụ `correlation_id=req-4be5226c`.
4. Root cause: incident `rag_slow` bật → `mock_rag.retrieve` `time.sleep(2.5)` trong `app/mock_rag.py`.
5. Fix tạm: `POST /incidents/rag_slow/disable`; phòng ngừa: alert HighLatencyP95 + timeout/circuit breaker cho retriever.
