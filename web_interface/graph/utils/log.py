# web_interface/graph/utils/log.py
from __future__ import annotations

"""
그래프 실행 로깅 유틸.

- new_run_id(): 실행 run_id 생성
- log_event(): 노드 실행 이벤트 로깅 (INFO/WARN/ERROR)
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .config import LOG_DIR


# ──────────────────────────────────────────────────────────────────────────────
# run_id 생성
# ──────────────────────────────────────────────────────────────────────────────

def new_run_id() -> str:
    """
    실행 식별자(run_id)를 'YYYYMMDD-HHMMSS' 형태로 생성.
    """
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# ──────────────────────────────────────────────────────────────────────────────
# 이벤트 로깅
# ──────────────────────────────────────────────────────────────────────────────

def log_event(
    run_id: str,
    node: str,
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    실행 이벤트를 로그 파일에 남김.

    Args:
        run_id: 실행 식별자 (new_run_id()로 생성)
        node: 실행 중인 노드 이름
        level: 로그 레벨 ("INFO", "WARN", "ERROR")
        message: 메시지 문자열
        extra: 추가 데이터(dict). 있으면 JSON-style로 문자열화
    """
    # 로그 디렉토리 보장
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 로그 파일 경로: logs/graph/run_YYYYMMDD.log (하루 단위)
    day_tag = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"run_{day_tag}.log"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = f"[{timestamp}] [{run_id}] [{level}] {node} - {message}"
    if extra:
        try:
            kvs = " ".join([f"{k}={v}" for k, v in extra.items()])
            line += " | " + kvs
        except Exception:
            pass

    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # 로그 실패는 전체 실행을 멈추지 않음
        return


__all__ = [
    "new_run_id",
    "log_event",
]