# web_interface/graph/nodes/function/validate_outputs.py
from __future__ import annotations

"""
function/validate_outputs.py

역할:
- state.result_paths에 기록된 산출물들을 검증한다.
- 파일 존재/크기/JSON 파싱 가능 여부를 확인한다.
- 누락되거나 잘못된 경우 state.errors에 기록한다.

입력(state에서 참조):
- result_paths: dict[str, str]

출력(partial state):
- errors: list[str] (검증 실패 시 추가)

데이터 I/O:
- 파일 존재 여부 확인
- JSON 파일은 로드 시도
"""

from pathlib import Path
from typing import List

from ...state import GraphStateV1
from ...utils.config import REQUIRED_OUTPUTS
from ...utils.io import exists_nonempty, read_json
from ...utils.log import log_event

NODE_METADATA = {
    "type": "function",
    "timeout": 15,
    "retries": 0,
    "description": "Validate output files (existence, size, JSON parsing)",
}


def validate_outputs(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")
    result_paths = state.get("result_paths") or {}

    errors: List[str] = []

    # 필수 산출물 누락 확인
    for fname in REQUIRED_OUTPUTS:
        path = result_paths.get(fname)
        if not path or not exists_nonempty(path):
            errors.append(f"missing or empty: {fname}")
            continue

        # JSON 파싱 체크
        if fname.endswith(".json"):
            data = read_json(path)
            if data is None:
                errors.append(f"invalid JSON: {fname}")

    # 결과 로깅
    if errors:
        log_event(
            run_id,
            "function/validate_outputs",
            "ERROR",
            f"validation failed for {len(errors)} files",
            extra={"errors": errors},
        )
        return {
            "errors": (state.get("errors") or []) + errors,
        }

    log_event(
        run_id,
        "function/validate_outputs",
        "INFO",
        "all outputs validated successfully",
    )
    return {}