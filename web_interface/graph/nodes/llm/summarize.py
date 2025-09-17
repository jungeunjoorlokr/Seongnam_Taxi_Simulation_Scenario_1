# web_interface/graph/nodes/llm/summarize.py
from __future__ import annotations

"""
llm/summarize.py

역할:
- state.message / analysis / errors / intent / params / result_paths 를 종합하여
  사용자에게 보여줄 최종 응답 문장을 LLM으로 생성한다.

입력(state에서 참조):
- message: str
- analysis: dict
- errors: list[str]
- intent: str
- params: dict
- result_paths: dict

출력(partial state):
- message: str (최종본)

데이터 I/O:
- LLM API 호출
"""

from typing import Dict, Any
from openai import OpenAI
import json

from ...state import GraphStateV1
from ...utils.log import log_event

NODE_METADATA = {
    "type": "llm",
    "timeout": 20,
    "retries": 1,
    "description": "Summarize simulation result or error into a final user-facing message",
}

client = OpenAI()

SYSTEM_PROMPT = """You are a summarizer for a taxi simulation system.
Your job:
1. Read the state data (intent, params, message, errors, analysis, result_paths).
2. If there are errors, write a concise warning + cause + what user can try next.
3. If successful:
   - Confirm what action was taken (run simulation / edit config / update viz).
   - Summarize the main parameters used (num_taxis, time_range, dispatch_mode).
   - Highlight 1–2 key results or outputs.
4. Keep the answer short, clear, and user-friendly.
Output only plain text in Korean, no JSON.
"""


def llm_summarize(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")

    # context 준비
    context = {
        "intent": state.get("intent"),
        "params": state.get("params"),
        "message": state.get("message"),
        "analysis": state.get("analysis"),
        "errors": state.get("errors"),
        "result_paths": state.get("result_paths"),
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 필요시 교체
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        summary = response.choices[0].message.content.strip()
    except Exception as e:
        msg = f"LLM summarize failed: {e}"
        log_event(run_id, "llm/summarize", "ERROR", msg)
        return {
            "message": "결과 요약에 실패했습니다. 로그를 확인해주세요.",
            "errors": (state.get("errors") or []) + [msg],
        }

    # 로그 남기기
    log_event(
        run_id,
        "llm/summarize",
        "INFO",
        "final summary generated",
        extra={"summary": summary[:200]},  # 앞부분만
    )

    return {
        "message": summary,
    }