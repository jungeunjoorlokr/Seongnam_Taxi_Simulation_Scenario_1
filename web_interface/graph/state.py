# web_interface/graph/state.py
from __future__ import annotations

"""
GraphStateV1 정의

- LangGraph에서 모든 노드가 읽고/쓰고 공유하는 상태
- TypedDict 기반으로 스키마를 강제하고, 버전 태깅 포함
"""

from typing import TypedDict, Literal, Optional, Dict, Any, List


# Intent 유형 정의
Intent = Literal["RUN_SIM", "EDIT_CONFIG", "UPDATE_VIZ", "UNKNOWN"]


class GraphStateV1(TypedDict, total=False):
    # 메타
    version: str                        # 스키마 버전 (예: "1.0.0")
    run_id: str                         # 실행 식별자 (logs/graph/에도 기록)

    # 사용자 입력/파싱
    user_input: str                     # 사용자 명령 원문
    intent: Intent                      # 파서 결과 의도
    params: Dict[str, Any]              # 파라미터 (num_taxis, time_range 등)

    # 실행 결과/산출물
    result_paths: Dict[str, str]        # 산출물 경로 모음
    analysis: Dict[str, Any]            # 분석/품질 체크 요약
    message: str                        # 사용자에게 보여줄 최종 문장

    # 에러 처리
    errors: List[str]                   # 실행 중 발생한 에러 누적

    # 추가 메타데이터
    meta: Dict[str, Any]                # 노드별 타이밍/메타정보 (옵션)


# 기본 버전 상수
GRAPH_STATE_VERSION = "1.0.0"