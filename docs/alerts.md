# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: Critical
- SLI/SLO liên quan: `latency_p95_ms` (Mục tiêu SLO: <= 3000ms)
- Điều kiện và thời gian duy trì: Latency p95 > 3000ms duy trì liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng gặp phản hồi chậm từ chatbot, request timeout hoặc trải nghiệm tương tác bị ngắt quãng.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Latency trên Dashboard để xác định xu hướng tăng latency xảy ra ở bước nào (LLM call hay RAG retrieval).
  2. Mở Langfuse Trace xem span `retrieve` và `generation` để khoanh vùng latency bất thường.
  3. Kiểm tra log `data/logs.jsonl` lọc theo `event == "response_sent"` và xem trường `latency_ms` cùng `correlation_id`.
- Mitigation tạm thời: Chuyển hướng traffic sang fallback LLM model nhẹ hơn hoặc tắt bớt tính năng RAG retrieval sâu nếu phát hiện bế tắc tài nguyên.
- Owner: On-Call Observability Team

## Alert 2

- Tên: HighErrorRate
- Severity: Critical
- SLI/SLO liên quan: `error_rate_pct` (Mục tiêu SLO: <= 2.0%)
- Điều kiện và thời gian duy trì: Tỷ lệ lỗi (HTTP 500 / Request Failed) > 2.0% duy trì liên tục trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận phản hồi lỗi hệ thống, không gửi được tin nhắn hoặc gián đoạn dịch vụ.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors trên Dashboard để phân tích `error_breakdown` (loại lỗi xuất hiện phổ biến nhất như `ValueError`, `ConnectionError`).
  2. Tra cứu log `data/logs.jsonl` lọc các log entry có `event == "request_failed"` để lấy `correlation_id` và `error_type`.
  3. Tìm kiếm trace tương ứng trên Langfuse bằng `correlation_id` để xem chi tiết exception stacktrace.
- Mitigation tạm thời: Kích hoạt circuit breaker hoặc tự động retry ở client, kiểm tra lại kết nối dịch vụ LLM/RAG bên ngoài.
- Owner: On-Call API Team

## Alert 3

- Tên: LowQualityScore
- Severity: Warning
- SLI/SLO liên quan: `quality_score_avg` (Mục tiêu SLO: >= 0.75)
- Điều kiện và thời gian duy trì: Điểm chất lượng trung bình (Quality Score Proxy) < 0.75 duy trì liên tục trong 10 phút
- Ảnh hưởng tới người dùng: Câu trả lời chatbot suy giảm chất lượng, trả lời lan man hoặc chứa nhiều từ bị redact PII.
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Quality trên Dashboard để đánh giá mức độ sụt giảm điểm chất lượng.
  2. Kiểm tra Langfuse Prompt Versioning để xác định phiên bản prompt (`prompt_version`, `prompt_label`) đang chạy có bị thay đổi gần đây không.
  3. Mở các trace gần nhất có `quality_score` thấp để kiểm tra cặp prompt/response và xem có bị lỗi fetch prompt fallback hay không.
- Mitigation tạm thời: Thực hiện rollback prompt trên Langfuse về phiên bản `production` ổn định trước đó.
- Owner: AI Agent Team
