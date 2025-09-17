# web_interface/graph/nodes/function/edit_config.py
from __future__ import annotations

"""
function/edit_config.py

역할:
- state.params를 읽어 설정 파일(main.py가 참조하는 config 등)에 반영한다.
- 현재는 간단히 state.message에 "설정이 수정되었습니다"만 반환하는 placeholder.
- 나중에 실제 config.json / runtime_config.py 업데이트 로직으로 확장 가능.
"""

from ...state import GraphStateV1
from ...utils.log import log_event

NODE_METADATA = {
    "type": "function",
    "timeout": 5,
    "retries": 0,
    "description": "Apply parameter changes to config files",
}


def edit_config(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")
    params = state.get("params") or {}

    # TODO: 실제 config 수정 로직 연결 (파일 쓰기/검증 등)
    msg = f"설정이 수정되었습니다. 적용된 파라미터: {params}"

    log_event(
        run_id,
        "function/edit_config",
        "INFO",
        msg,
        extra={"params": params},
    )

    return {
        "message": msg,
    }