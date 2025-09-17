# web_interface/graph/utils/config.py
from __future__ import annotations

"""
프로젝트 공통 설정/스키마/기본값 모음.

- 경로 상수(PATHS)
- 필수 산출물 목록(REQUIRED_OUTPUTS)
- 파라미터 스키마(PARAM_SCHEMA)
- 유틸 함수: get_defaults(), get_param_schema(), normalize_params()
"""

from pathlib import Path
from typing import Any, Dict, Mapping, List, Tuple, Optional
import re

# ──────────────────────────────────────────────────────────────────────────────
# 경로 설정 (프로젝트 트리 기준)
# 현재 파일: web_interface/graph/utils/config.py
# 프로젝트 루트는 이 파일에서 상위로 3단계(…/web_interface/graph/utils → …/)
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
WEB_INTERFACE_DIR: Path = PROJECT_ROOT / "web_interface"
SIMUL_RESULT_DIR: Path = PROJECT_ROOT / "simul_result"
SIMUL_LATEST_DIR: Path = SIMUL_RESULT_DIR / "latest"
LOG_DIR: Path = PROJECT_ROOT / "logs" / "graph"
VIS_ASSETS_DIR: Path = PROJECT_ROOT / "visualization" / "dashboard" / "assets"
VIS_FIGURE_DIR: Path = VIS_ASSETS_DIR / "figure"
VIS_DATA_DIR: Path = VIS_ASSETS_DIR / "data"

# ──────────────────────────────────────────────────────────────────────────────
# 산출물/스키마
# ──────────────────────────────────────────────────────────────────────────────

# 필수 산출물 파일명 (validate_outputs에서 체크)
REQUIRED_OUTPUTS: List[str] = [
    "result.json",
    "trip.json",
    "passenger_marker.json",
    "vehicle_marker.json",
    "record.csv",
]

# dispatch 모드 허용 값
DISPATCH_MODES: List[str] = ["default", "greedy", "balanced"]

# 파라미터 스키마(검증은 아님; 허용타입/범위 가이드)
PARAM_SCHEMA: Dict[str, Dict[str, Any]] = {
    "num_taxis": {
        "type": int,
        "min": 1,
        "max": 5000,
        "description": "시뮬레이션에 투입할 택시 수",
    },
    "time_range": {
        "type": list,  # [start_min, end_min], 분 단위. end는 start보다 클 수도(자정 넘김) 있음.
        "bounds": (0, 2880),  # 0~2880(최대 +하루)
        "length": 2,
        "description": "분 단위 시간 구간 [start, end], 예: [1380,1560] (=23:00~02:00(+1day))",
    },
    "dispatch_mode": {
        "type": str,
        "enum": DISPATCH_MODES,
        "description": "배차 정책 모드",
    },
}

# 경로 모음
PATHS: Dict[str, Path] = {
    "PROJECT_ROOT": PROJECT_ROOT,
    "WEB_INTERFACE_DIR": WEB_INTERFACE_DIR,
    "SIMUL_RESULT_DIR": SIMUL_RESULT_DIR,
    "SIMUL_LATEST_DIR": SIMUL_LATEST_DIR,
    "LOG_DIR": LOG_DIR,
    "VIS_ASSETS_DIR": VIS_ASSETS_DIR,
    "VIS_FIGURE_DIR": VIS_FIGURE_DIR,
    "VIS_DATA_DIR": VIS_DATA_DIR,
}

# ──────────────────────────────────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────────────────────────────────

def get_defaults() -> Dict[str, Any]:
    """
    공통 기본값/경로/필수 산출물/스키마 요약을 반환.
    """
    return {
        "paths": {k: str(v) for k, v in PATHS.items()},
        "required_outputs": list(REQUIRED_OUTPUTS),
        "param_schema": get_param_schema(),
        "dispatch_modes": list(DISPATCH_MODES),
    }


def get_param_schema() -> Dict[str, Any]:
    """
    파라미터 스키마 사전 반환 (검증 로직은 아님).
    """
    return PARAM_SCHEMA.copy()


def normalize_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """
    입력 params를 스키마에 맞춰 '형식만' 정규화.
    - 타입 캐스팅/간단 파싱만 수행 (기본값 채우거나 범위 검증은 하지 않음)
    - 예:
        {"num_taxis": "900"}               -> {"num_taxis": 900}
        {"time_range": "1380,1560"}        -> {"time_range": [1380, 1560]}
        {"time_range": "23:00-02:00"}      -> {"time_range": [1380, 1560]}  # end가 start보다 작으면 +1440
        {"dispatch_mode": "Greedy"}        -> {"dispatch_mode": "greedy"}
    """
    out: Dict[str, Any] = {}

    # num_taxis
    if "num_taxis" in params and params["num_taxis"] is not None:
        out["num_taxis"] = _to_int(params["num_taxis"])

    # time_range
    if "time_range" in params and params["time_range"] is not None:
        out["time_range"] = _normalize_time_range(params["time_range"])

    # dispatch_mode
    if "dispatch_mode" in params and params["dispatch_mode"] is not None:
        dm = str(params["dispatch_mode"]).strip().lower()
        out["dispatch_mode"] = dm

    return out

# ──────────────────────────────────────────────────────────────────────────────
# 내부 유틸 (normalize_params용)
# ──────────────────────────────────────────────────────────────────────────────

def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        # 정규화 단계에서는 실패 시 None 반환 (검증은 별도 단계에서)
        return None


def _normalize_time_range(value: Any) -> Optional[List[int]]:
    """
    time_range 입력을 [start_min, end_min] 리스트로 정규화.
    허용 입력:
      - [1380, 1560], ("1380","1560") 등 숫자/문자 배열
      - "1380,1560"
      - "23:00-02:00" 같은 HH:MM-HH:MM 형식(자정 넘김 자동 보정)
    반환:
      - 유효하면 [start, end] (int, 분 단위). end < start일 경우 end += 1440 처리.
      - 파싱 실패 시 None
    """
    # 1) 리스트/튜플 케이스
    if isinstance(value, (list, tuple)) and len(value) == 2:
        a, b = value[0], value[1]
        a_i = _to_int(a) if not _looks_like_time(str(a)) else _hhmm_to_min(str(a))
        b_i = _to_int(b) if not _looks_like_time(str(b)) else _hhmm_to_min(str(b))
        if a_i is None or b_i is None:
            return None
        if b_i <= a_i:
            b_i += 1440  # 자정 넘김 처리
        return [a_i, b_i]

    # 2) "start,end" 문자열
    if isinstance(value, str) and "," in value:
        parts = [p.strip() for p in value.split(",")]
        if len(parts) == 2:
            return _normalize_time_range(parts)

    # 3) "HH:MM-HH:MM" 문자열
    if isinstance(value, str) and "-" in value and _maybe_hhmm_range(value):
        start_s, end_s = [p.strip() for p in value.split("-", 1)]
        a_i = _hhmm_to_min(start_s)
        b_i = _hhmm_to_min(end_s)
        if a_i is None or b_i is None:
            return None
        if b_i <= a_i:
            b_i += 1440
        return [a_i, b_i]

    # 4) 실패
    return None


_HHMM_RE = re.compile(r"^\s*\d{1,2}:\d{2}\s*$")


def _looks_like_time(s: str) -> bool:
    return bool(_HHMM_RE.match(s))


def _maybe_hhmm_range(s: str) -> bool:
    parts = s.split("-", 1)
    return len(parts) == 2 and _looks_like_time(parts[0].strip()) and _looks_like_time(parts[1].strip())


def _hhmm_to_min(s: str) -> Optional[int]:
    """
    "HH:MM" → 분(minute) 변환. 00:00=0, 23:59=1439
    """
    if not _looks_like_time(s):
        return None
    try:
        hh, mm = s.strip().split(":")
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h * 60 + m
    except Exception:
        return None


__all__ = [
    "PROJECT_ROOT",
    "WEB_INTERFACE_DIR",
    "SIMUL_RESULT_DIR",
    "SIMUL_LATEST_DIR",
    "LOG_DIR",
    "VIS_ASSETS_DIR",
    "VIS_FIGURE_DIR",
    "VIS_DATA_DIR",
    "REQUIRED_OUTPUTS",
    "DISPATCH_MODES",
    "PARAM_SCHEMA",
    "PATHS",
    "get_defaults",
    "get_param_schema",
    "normalize_params",
]