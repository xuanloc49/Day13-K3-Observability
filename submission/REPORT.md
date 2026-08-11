# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py` (baseline CP0, sau khi hoàn thiện PII scrubbing nhưng **trước** khi Member A hoàn thiện middleware/correlation ID ở CP1): **30/100**
  - Nguồn: 21/21 bản ghi JSON hợp lệ, sinh từ 10 request qua `data/sample_queries.jsonl`.
  - Breakdown: `-30` thiếu `correlation_id` hợp lệ (đang là `"MISSING"` — chờ CP1 middleware), `-20` thiếu enrichment (`user_id_hash`, `session_id`, `feature`, `model` — chờ CP1 context binding), `-20` correlation ID propagation (<2 ID duy nhất). `PII scrubbing: PASSED` (0 leak).
  - Mốc đối chiếu: sau khi Member A xong CP1, chạy lại lệnh này để xác nhận điểm tăng lên (kỳ vọng ≥80/100 theo tiêu chí Checkpoint 1).
- Tổng số traces: **14** trên Langfuse (10 từ `load_test.py` + 4 từ test prompt versioning), verify qua `GET /api/public/traces` (`totalItems: 14`), không chỉ suy luận từ code.
- Số PII leak còn lại: **0/21** bản ghi (đã test thêm thủ công với email, số điện thoại, số thẻ, CCCD, hộ chiếu và địa chỉ VN có dấu/không dấu — toàn bộ bị redact đúng).
- Link/đường dẫn dashboard: (chưa có — thuộc CP2, Member C/D phụ trách)

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name: `day13-chat` (type `text`), tạo qua Langfuse API `POST /api/public/v2/prompts`.
- Version/label baseline: **v1**, labels `baseline` + `production` (ban đầu). Nội dung: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`.
- Version/label candidate: **v2**, label `candidate`. Thay đổi nhỏ về format: thêm dòng `Answer in at most 2 concise sentences.` (không đổi 3 biến bắt buộc).
- Trace ID của mỗi version (cùng input `"What is the refund policy?"`, feature `refund`):
  - `682b700f5071d0da6a6b01836476d810` — session `sess-baseline` — `prompt_label=baseline`, `prompt_version=1`, `prompt_source=langfuse`, `tokens_in=28`.
  - `0e2421066147c31d9af798f5377784bf` — session `sess-candidate` — `prompt_label=candidate`, `prompt_version=2`, `prompt_source=langfuse`, `tokens_in=38` (dài hơn do prompt v2 có thêm câu chỉ dẫn).
- Bằng chứng đổi label / rollback:
  1. Chuyển `production` từ v1 → v2 qua `PATCH /api/public/v2/prompts/day13-chat/versions/2` (`newLabels: ["candidate", "production"]`) → xác nhận GET `?label=production` trả về `version: 2`.
  2. Request thật với `LANGFUSE_PROMPT_LABEL=production` sau khi chuyển → trace `7464ee957fc04a5e19eb6dac7f458c34` (session `sess-prod-after-switch`) cho `prompt_label=production`, `prompt_version=2`.
  3. Rollback `production` về v1 qua `PATCH .../versions/1` (`newLabels: ["baseline", "production"]`) → GET `?label=production` trả về `version: 1`.
  4. Request thật sau rollback (phải **restart app process** vì SDK cache prompt phía client, `cache_ttl_seconds=60`, không tự invalidate ngay khi label đổi trên server — lưu ý vận hành quan trọng) → trace `ba56b897aa54e760f32be5047a454603` (session `sess-prod-rollback-final`) xác nhận `prompt_label=production`, `prompt_version=1`, `prompt_source=langfuse`.
- Ghi chú vận hành: đổi label trên Langfuse có hiệu lực **ngay lập tức phía server**, nhưng client (SDK) có thể trả bản cache cũ tới khi cache hết hạn hoặc process được restart — cần tính đến khi rollback prompt trên production thật.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
