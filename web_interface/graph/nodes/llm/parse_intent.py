# web_interface/graph/nodes/llm/parse_intent.py
from __future__ import annotations

"""
llm/parse_intent.py

역할:
- 사용자 원문 명령(user_input)을 LLM에 전달하여 intent와 params를 추출한다.
- Intent: RUN_SIM / EDIT_CONFIG / UPDATE_VIZ / UNKNOWN
- Params: num_taxis, time_range, dispatch_mode 등 dict 형태

입력(state에서 참조):
- user_input: str

출력(partial state):
- intent: str
- params: dict

데이터 I/O:
- LLM API 호출 (예: OpenAI, Anthropic 등)
"""

from typing import Dict, Any
# 예시: OpenAI ChatCompletion 사용
from openai import OpenAI

from ...state import GraphStateV1, Intent
from ...utils.log import log_event
from ...utils.config import normalize_params

NODE_METADATA = {
    "type": "llm",
    "timeout": 20,
    "retries": 1,
    "description": "Parse user natural language into intent and params",
}

# --- LLM 클라이언트 (실제 API 키는 환경변수에서 불러옴) ---
client = OpenAI()


SYSTEM_PROMPT = """You are an intent parser for a taxi simulation system.
Your job:
1. Classify the user's request into one of:
   - RUN_SIM: Run a new simulation
   - EDIT_CONFIG: Change simulation configuration (num_taxis, dispatch_mode, etc.)
   - UPDATE_VIZ: Update or adjust visualization
   - UNKNOWN: Anything else
2. Extract key parameters if mentioned:
   - num_taxis (integer)
   - time_range (two times like '23:00-02:00', '1380,1560')
   - dispatch_mode (default/greedy/balanced)
3. Output JSON with keys: intent, params
"""

def llm_parse_intent(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")
    user_input = state.get("user_input") or ""

    if not user_input.strip():
        msg = "empty user_input"
        log_event(run_id, "llm/parse_intent", "ERROR", msg)
        return {
            "intent": "UNKNOWN",
            "params": {},
            "errors": (state.get("errors") or []) + [msg],
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 필요시 교체
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    except Exception as e:
        msg = f"LLM call failed: {e}"
        log_event(run_id, "llm/parse_intent", "ERROR", msg)
        return {
            "intent": "UNKNOWN",
            "params": {},
            "errors": (state.get("errors") or []) + [msg],
        }

    # JSON 파싱
    try:
        import json
        parsed = json.loads(content)
        intent = parsed.get("intent", "UNKNOWN")
        params_raw = parsed.get("params", {})
    except Exception as e:
        msg = f"parse error: {e}"
        log_event(run_id, "llm/parse_intent", "ERROR", msg)
        return {
            "intent": "UNKNOWN",
            "params": {},
            "errors": (state.get("errors") or []) + [msg],
        }

    # params 정규화
    params = normalize_params(params_raw)

    log_event(
        run_id,
        "llm/parse_intent",
        "INFO",
        f"intent={intent}, params={params}",
    )

    return {
        "intent": intent,
        "params": params,
    }