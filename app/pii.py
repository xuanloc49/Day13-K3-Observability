from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport": r"(?i)\b[a-z]\d{7}\b",
    # Hỗ trợ cả có dấu và không dấu vì user thường gõ tiếng Việt không dấu.
    # Bỏ "tổ/to" khỏi danh sách keyword vì "to" trùng từ thông dụng, gây false
    # positive tràn lan (vd "up to 5 items").
    "vn_address": (
        r"(?i)\b(?:s(?:ố|o)\s*\d+[a-z]?(?:/\d+)?\s*,?\s*)?"
        r"(?:đường|duong|phố|pho|ngõ|ngo|hẻm|hem|khu\s?phố|khu\s?pho|"
        r"phường|phuong|xã|xa|quận|quan|huyện|huyen|tỉnh|tinh|"
        r"thành\s?phố|thanh\s?pho)"
        r"\s+[^,\.\n]+"
    ),
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
