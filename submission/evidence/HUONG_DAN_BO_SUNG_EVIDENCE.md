# Hướng dẫn bổ sung evidence — Nhóm A2

**Trạng thái: ĐÃ HOÀN TẤT** (ảnh prompt UI PR #6, dashboard PR #5, challenge/REPORT PR #4 đã merge `main`).

Người đã làm: **Đào Ngọc Bích** (Prompt Version UI), **Ngô Tuấn Hưng** (Dashboard UI), **Vũ Đức Anh** (gắn evidence + REPORT).

Repo: https://github.com/xuanloc49/Day13-K3-Observability

---

## Lịch sử yêu cầu (giữ để đối chiếu)

Người cần làm (lúc còn thiếu): **Đào Ngọc Bích** (Prompt Version UI) và **Ngô Tuấn Hưng** (Dashboard UI).  
Người nhận file: **Vũ Đức Anh**.

Nhánh nộp evidence: gửi ảnh cho Anh **hoặc** push lên nhánh của bạn rồi báo Anh.

---

## 1) Đào Ngọc Bích — Prompt versioning (ảnh UI Langfuse)

### Output bắt buộc (đặt tên file đúng)

Gửi **3 ảnh PNG/JPG** (không lộ secret key):

| # | Tên file đề xuất | Nội dung ảnh phải nhìn thấy |
|---|---|---|
| 1 | `prompt_versions_list.png` | Prompt `day13-chat` có **ít nhất 2 version** (v1 và v2) |
| 2 | `prompt_traces_baseline_vs_candidate.png` | Hai trace (hoặc 2 tab) hiện `prompt_label` / `prompt_version` khác nhau |
| 3 | `prompt_production_rollback.png` | Trước/sau (hoặc 1 ảnh rõ label) khi `production` gắn v2 rồi **rollback** về v1 |

Trace ID đã có sẵn trong REPORT (chỉ cần mở và chụp):

- Baseline v1: `682b700f5071d0da6a6b01836476d810` (session `sess-baseline`)
- Candidate v2: `0e2421066147c31d9af798f5377784bf` (session `sess-candidate`)
- Sau switch production→v2: `7464ee957fc04a5e19eb6dac7f458c34`
- Sau rollback production→v1: `ba56b897aa54e760f32be5047a454603`

### Step cụ thể

1. Đăng nhập **đúng project Langfuse** của nhóm (cùng key trong `.env` lab).
2. Vào **Prompts** → mở prompt tên `day13-chat`.
3. Chụp màn hình danh sách version → lưu `prompt_versions_list.png`.
4. Vào **Traces**:
   - Search/filter theo session `sess-baseline` hoặc paste trace ID `682b700f5071d0da6a6b01836476d810`.
   - Mở metadata: xác nhận `prompt_name=day13-chat`, `prompt_label=baseline`, `prompt_version=1`.
   - Làm tương tự với `0e2421066147c31d9af798f5377784bf` (`candidate` / version `2`).
   - Chụp 2 trace (ghép 1 ảnh hoặc 2 ảnh) → `prompt_traces_baseline_vs_candidate.png`.
5. Chụp evidence rollback:
   - Mở prompt `day13-chat`, nhìn label `production` đang gắn version nào.
   - Nếu cần minh họa lại nhanh:
     - Gắn `production` vào **v2** → chụp.
     - Gắn lại `production` vào **v1** → chụp.
   - Hoặc mở 2 trace `7464ee95…` và `ba56b897…` cạnh nhau để chứng minh trước/sau.
   - Lưu `prompt_production_rollback.png`.
6. Gửi 3 file cho Vũ Đức Anh (Zalo/Drive) **hoặc** copy vào:

```text
submission/evidence/prompt_versions_list.png
submission/evidence/prompt_traces_baseline_vs_candidate.png
submission/evidence/prompt_production_rollback.png
```

### Checklist tự kiểm

- [ ] Thấy rõ tên prompt `day13-chat`
- [ ] Thấy rõ 2 version
- [ ] Thấy rõ label `baseline` / `candidate` / `production`
- [ ] Không lộ `LANGFUSE_SECRET_KEY` / `.env`

---

## 2) Ngô Tuấn Hưng — Dashboard runtime (6 panel)

> **Đã dựng sẵn bởi nhóm:** Streamlit app `scripts/dashboard_app.py` + ảnh `submission/evidence/dashboard_6_panels.png`.
> Hưng chỉ cần review ảnh/contract; nếu muốn tự chụp lại:

### Chạy lại UI

```bash
pip install -r requirements-dashboard.txt
streamlit run scripts/dashboard_app.py
# mở http://127.0.0.1:8501
```

---

## Sau khi nhận ảnh — Vũ Đức Anh sẽ làm

1. Copy file vào `submission/evidence/`
2. Cập nhật `submission/REPORT.md` mục 4 và 5 (đường dẫn ảnh)
3. Push nhánh `01191-VuDucAnh` / PR https://github.com/xuanloc49/Day13-K3-Observability/pull/4

**Đã xong:** ảnh đã có trong `submission/evidence/`, REPORT đã cập nhật, PR #4 đã merge `main`.
