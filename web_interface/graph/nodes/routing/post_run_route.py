# 실행 후 성공/실패 분기

def post_run_route_node(state: dict) -> str:
    """
    LangGraph conditional edge router.
    return "validate_outputs" if 성공,
           "error_guard" if 실패
    """
    if state.get("error"):
        return "error_guard"
    return "validate_outputs"