"""CP1 — Structured logging.

`print("user abc hỏi gì đó")` là log cho người đọc. Cloud (Railway, Render,
Cloud Run, Datadog...) đọc log bằng máy: một dòng = một JSON object thì mới
lọc/đếm/cảnh báo được. Đây là khác biệt lớn giữa localhost và production.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """CHO SẴN — thời điểm hiện tại theo ISO-8601, múi giờ UTC."""
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, level: str = "info", **fields) -> str:
    # 1. Tạo dictionary chứa dữ liệu theo yêu cầu
    log_data = {
        "event": event,
        "level": level.lower(),
        "timestamp": utc_now_iso(),
    }
    
    # Gộp thêm các trường truyền thêm vào (**fields)
    log_data.update(fields)

    # 2. Chuyển sang chuỗi JSON (trên 1 dòng) và xử lý tiếng Việt
    log_str = json.dumps(log_data, ensure_ascii=False)
    
    # 3. In ra stdout và return kết quả
    print(log_str)
    return log_str
