# web_interface/graph/nodes/function/update_viz.py
from __future__ import annotations

"""
function/update_viz.py

역할:
- state.params나 명령을 바탕으로 시각화(trip.js, dashboard assets 등)를 업데이트한다.
- 현재는 placeholder: 단순히 "시각화가 업데이트되었습니다" 반환.
- 나중에 visualization/dashboard/assets 수정 로직으로 확장 가능.
"""

from ...state import GraphStateV1
from ...utils.log import log_event

NODE_METADATA = {
    "type": "function",
    "timeout": 5,
    "retries": 0,
    "description": "Update visualization assets",
}


def update_visualization(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")
    params = state.get("params") or {}

    # TODO: 실제 viz 파일 업데이트 로직 연결 (React dashboard assets 등)
    msg = f"시각화가 업데이트되었습니다. (params={params})"

    log_event(
        run_id,
        "function/update_visualization",
        "INFO",
        msg,
        extra={"params": params},
    )

    return {
        "message": msg,
    }