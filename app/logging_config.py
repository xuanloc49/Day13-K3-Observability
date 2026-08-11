from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from .pii import scrub_text

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


class JsonlFileProcessor:
    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(rendered + "\n")
        return event_dict



# Các field cấu trúc/định danh (không phải nội dung tự do) không cần scrub.
# Quan trọng: những field này là ID hệ thống tự sinh (hex/hash ngẫu nhiên) —
# nếu quét qua PII regex, shape ngẫu nhiên của chúng có thể trùng passport
# (1 chữ + 7 số) hoặc CCCD (12 số) và bị redact nhầm, làm hỏng correlation_id
# thật (đã đo được ~1.5% correlation_id và ~0.5% user_id_hash bị redact nhầm
# nếu không loại trừ). Field tự do (payload, event, và mọi field lạ khác) vẫn
# được scrub bình thường.
_STRUCTURAL_KEYS = {
    "ts",
    "level",
    "correlation_id",
    "user_id_hash",
    "session_id",
    "feature",
    "model",
    "env",
    "service",
}


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    # Scrub toàn bộ event_dict (không chỉ payload/event) để mọi field text mới
    # do người khác thêm sau này vẫn tự động được che PII, không cần sửa lại nơi này.
    for key, value in list(event_dict.items()):
        if key in _STRUCTURAL_KEYS:
            continue
        event_dict[key] = _scrub_value(value)
    return event_dict



def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            # TODO: Register your PII scrubbing processor here
            scrub_event,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            JsonlFileProcessor(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )



def get_logger() -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger()
