# web_interface/graph/utils/io.py
from __future__ import annotations

"""
경로/파일 입출력 유틸 모음.

- latest_result_dir(): simul_result/latest 경로 반환
- exists_nonempty(path): 파일 존재 & 크기>0 확인
- read_json(path): JSON 안전 로드(예외 처리 포함)
- ensure_run_dir(run_id): simul_result/run_{run_id} 디렉토리 생성/반환
"""

from pathlib import Path
from typing import Any, Optional
import json
import os

# 내부 설정 상수는 config에서 가져옴
from .config import (
    SIMUL_RESULT_DIR,
    SIMUL_LATEST_DIR,
)

# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def latest_result_dir() -> str:
    """
    simul_result/latest 디렉토리의 실제 경로를 문자열로 반환.
    디렉토리가 없더라도 경로 문자열은 반환(존재 확인/생성은 호출 측 책임).
    """
    return str(SIMUL_LATEST_DIR)


def exists_nonempty(path: str | Path) -> bool:
    """
    파일 존재 & 크기 > 0 이면 True.
    디렉토리이거나 접근 불가하면 False.
    """
    try:
        p = Path(path)
        return p.is_file() and p.stat().st_size > 0
    except Exception:
        return False


def read_json(path: str | Path, *, encoding: str = "utf-8") -> Optional[Any]:
    """
    JSON 파일을 안전하게 로드하여 Python 객체로 반환.
    - 파일 미존재/파싱 실패 시 None 반환.
    """
    p = Path(path)
    if not p.is_file():
        return None
    try:
        with p.open("r", encoding=encoding) as f:
            return json.load(f)
    except Exception:
        return None


def ensure_run_dir(run_id: str) -> str:
    """
    simul_result/run_{run_id} 디렉토리를 생성(없으면)하고 경로 문자열을 반환.
    """
    if not run_id or not isinstance(run_id, str):
        raise ValueError("run_id must be a non-empty string.")
    run_dir = SIMUL_RESULT_DIR / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return str(run_dir)

# ──────────────────────────────────────────────────────────────────────────────

__all__ = [
    "latest_result_dir",
    "exists_nonempty",
    "read_json",
    "ensure_run_dir",
]