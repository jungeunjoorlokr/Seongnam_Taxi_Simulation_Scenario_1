# web_interface/graph/nodes/routing/route.py
from __future__ import annotations

"""
라우팅 노드: intent 기반 1차 분기

- route_by_intent(state): 그래프 노드로 등록되는 라우터(상태는 건드리지 않음)
- select_next_by_intent(state): add_conditional_edges 에서 쓰는 '선택 함수'
"""

from typing import Literal
from ...state import GraphStateV1, Intent
from ...utils.log import log_event

# 노드 메타데이터 (옵션: 관찰/대시보드용)
NODE_METADATA = {
    "type": "routing",
    "timeout": 5,
    "retries": 0,
    "description": "Route flow based on parsed intent",
}

# 조건부 엣지 매핑에서 사용할 '선택 키'
# - 이 값들을 orchestration.py의 add_conditional_edges()에서 실제 노드명에 매핑해 사용
RouteKey = Literal["RUN_SIM", "EDIT_CONFIG", "UPDATE_VIZ", "UNKNOWN"]


def select_next_by_intent(state: GraphStateV1) -> RouteKey:
    """
    조건부 엣지 선택 함수.
    LangGraph의 add_conditional_edges() 두 번째 인자로 넘겨, 다음 경로 키를 반환합니다.
    """
    intent = state.get("intent") or "RUN_SIM"  # 기본값: 실행
    if intent not in ("RUN_SIM", "EDIT_CONFIG", "UPDATE_VIZ", "UNKNOWN"):
        intent = "UNKNOWN"
    return intent  # 여기서 반환한 키를 orchestration에서 실제 노드로 매핑


def route_by_intent(state: GraphStateV1) -> GraphStateV1:
    """
    라우팅 '노드' 자체.
    - 상태를 변경하지 않고, 분기 결정을 로그에만 남깁니다.
    - 실제 분기는 add_conditional_edges(select_next_by_intent, mapping=...)에서 수행.
    """
    run_id = state.get("run_id", "no-runid")
    intent = state.get("intent") or "RUN_SIM"
    if intent not in ("RUN_SIM", "EDIT_CONFIG", "UPDATE_VIZ", "UNKNOWN"):
        intent = "UNKNOWN"

    log_event(
        run_id=run_id,
        node="routing/route",
        level="INFO",
        message=f"intent={intent} → selecting next path",
        extra={"intent": intent},
    )
    # 라우터 노드는 보통 상태를 수정하지 않는다.
    return {}