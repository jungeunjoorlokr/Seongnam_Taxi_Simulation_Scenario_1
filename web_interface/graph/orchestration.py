# web_interface/graph/orchestration.py
from __future__ import annotations

"""
orchestration.py

역할:
- 전체 StateGraph 정의
- 노드 등록 및 엣지 연결
- intent 기반 분기 / 후처리 / 요약까지 왕복 가능

명령 흐름:
1. llm/parse_intent
2. routing/route → intent별 경로
   - RUN_SIM → fn_run_simulation → fn_collect_outputs → fn_validate_outputs → llm/summarize
   - EDIT_CONFIG → fn_edit_config → llm/summarize
   - UPDATE_VIZ → fn_update_visualization → llm/summarize
   - UNKNOWN → llm/summarize
"""

from langgraph.graph import StateGraph, END

from .state import GraphStateV1, GRAPH_STATE_VERSION
# LLM nodes
from .nodes.llm.parse_intent import llm_parse_intent
from .nodes.llm.summarize import llm_summarize
# Function nodes
from .nodes.function.run_simulation import run_simulation
from .nodes.function.collect_outputs import collect_outputs
from .nodes.function.validate_outputs import validate_outputs
from .nodes.function.edit_config import edit_config
from .nodes.function.update_visualization import update_visualization
# Routing nodes
from .nodes.routing.route import route_by_intent, select_next_by_intent

from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv(dotenv_path="../../.env")

# 이제 OPENAI_API_KEY 환경변수 사용 가능

def build_orchestrator():
    """
    전체 그래프(StateGraph)를 구성하고 compile()한 앱을 반환.
    """
    graph = StateGraph(GraphStateV1)

    # ── 노드 등록 ────────────────────────────────────────
    graph.add_node("llm/parse_intent", llm_parse_intent)
    graph.add_node("llm/summarize", llm_summarize)

    graph.add_node("function/run_simulation", run_simulation)
    graph.add_node("function/collect_outputs", collect_outputs)
    graph.add_node("function/validate_outputs", validate_outputs)
    graph.add_node("function/edit_config", edit_config)
    graph.add_node("function/update_visualization", update_visualization)

    graph.add_node("routing/route", route_by_intent)

    # ── 엣지 연결 ────────────────────────────────────────
    # Entry
    graph.add_edge("llm/parse_intent", "routing/route")

    # routing/route → intent별 경로 (조건부 엣지)
    graph.add_conditional_edges(
        "routing/route",
        select_next_by_intent,
        {
            "RUN_SIM": "function/run_simulation",
            "EDIT_CONFIG": "function/edit_config",
            # intent 키는 그대로 UPDATE_VIZ를 사용하지만, 실제 노드명은 update_visualization로 매핑
            "UPDATE_VIZ": "function/update_visualization",
            "UNKNOWN": "llm/summarize",
        },
    )

    # RUN_SIM 경로
    graph.add_edge("function/run_simulation", "function/collect_outputs")
    graph.add_edge("function/collect_outputs", "function/validate_outputs")
    graph.add_edge("function/validate_outputs", "llm/summarize")

    # EDIT_CONFIG 경로
    graph.add_edge("function/edit_config", "llm/summarize")

    # UPDATE_VIZ 경로
    graph.add_edge("function/update_visualization", "llm/summarize")

    # Summarize → END
    graph.add_edge("llm/summarize", END)

    # ── Entry/Exit 지정 ─────────────────────────────────
    graph.set_entry_point("llm/parse_intent")

    return graph.compile()


# 편의 함수
def invoke(user_input: str):
    """
    오케스트레이터를 실행하는 헬퍼 함수.
    """
    app = build_orchestrator()
    state = {
        "version": GRAPH_STATE_VERSION,
        "user_input": user_input,
    }
    return app.invoke(state)