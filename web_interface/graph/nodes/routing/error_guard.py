# 에러 처리 노드

def error_guard_node(state: dict) -> dict:
    logs = state.get("logs", [])
    error = state.get("error", "UNKNOWN_ERROR")

    logs.append(f"[error_guard] caught error={error}")

    # TODO: 여기서 복구 전략 제안/재시도 로직 넣을 수 있음
    return {"logs": logs, "error": error}