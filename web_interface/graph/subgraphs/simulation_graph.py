from langgraph.graph import StateGraph
from ..state import GraphState
from ..nodes.llm.parse_intent import parse_intent_node
from ..nodes.llm.resolve_params import resolve_params_node
from ..nodes.llm.analyze_quality import analyze_quality_node
from ..nodes.function.run_simulation import run_simulation_node
from ..nodes.function.edit_config import edit_config_node
from ..nodes.function.update_visualization import update_visualization_node
from ..nodes.function.validate_outputs import validate_outputs_node
from ..nodes.routing.route import route_by_intent
from ..nodes.routing.post_run_route import post_run_route_node
from ..nodes.routing.error_guard import error_guard_node

def build_simulation_graph():
    g = StateGraph(GraphState)

    # 노드 등록
    g.add_node("parse_intent", parse_intent_node)
    g.add_node("resolve_params", resolve_params_node)
    g.add_node("run_simulation", run_simulation_node)
    g.add_node("edit_config", edit_config_node)
    g.add_node("update_visualization", update_visualization_node)
    g.add_node("validate_outputs", validate_outputs_node)
    g.add_node("analyze_quality", analyze_quality_node)
    g.add_node("error_guard", error_guard_node)

    # 진입점
    g.set_entry_point("parse_intent")

    # 분기
    g.add_edge("parse_intent", "resolve_params")
    g.add_conditional_edges("resolve_params", route_by_intent, {
        "RUN_SIM": "run_simulation",
        "EDIT_CONFIG": "edit_config",
        "UPDATE_VIZ": "update_visualization",
    })

    # 실행 후 라우팅
    g.add_edge("run_simulation", "post_run_route")
    g.add_conditional_edges("post_run_route", lambda s: post_run_route_node(s), {
        "validate_outputs": "validate_outputs",
        "error_guard": "error_guard",
    })

    # validate 이후 analyze 붙일 수 있음
    g.add_edge("validate_outputs", "analyze_quality")

    return g.compile()