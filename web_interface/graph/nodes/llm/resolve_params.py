# 파라미터 기본값/보정 노드

def resolve_params_node(state: dict) -> dict:
    logs = state.get("logs", [])
    params = state.get("params", {}) or {}

    # 기본값 채워넣기
    if "num_taxis" not in params:
        params["num_taxis"] = 100
        logs.append("[resolve_params] default num_taxis=100")

    if "time_range" not in params:
        params["time_range"] = [1380, 1440]  # 23:00~24:00
        logs.append("[resolve_params] default time_range=[1380,1440]")

    return {"params": params, "logs": logs}