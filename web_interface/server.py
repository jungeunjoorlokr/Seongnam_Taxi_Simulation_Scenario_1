# server.py — PART 1/4: imports, app, globals
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Literal, Optional

import pandas as pd
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

# --- ensure project root on sys.path ---
_THIS_FILE = Path(__file__).resolve()
# 부모 디렉토리 여러 단계 추가(어디에 두었든 안전하게)
for p in [_THIS_FILE.parent, *_THIS_FILE.parents]:
    s = str(p)
    if s not in sys.path:
        sys.path.append(s)

# Local imports
from web_interface.graph.state.schema import State
from web_interface.graph.nodes.flow import run_natural_language_command
from web_interface.graph.orchestrator import run_once, run_via_graph
from web_interface.graph.nodes.intent import (
    parse_command_simple,
    parse_command_legacy,
    parse_command_hybrid,
    IntentResult,
)
from web_interface.graph.tools.visualization import build_chart_series

app = FastAPI(title="Seongnam Simulation Server")

# 필요 시 CORS 허용 (index.html 파일/다른 포트에서 열 경우)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Globals ----
GLOBAL_STATE: Optional[State] = None
LOCK = threading.Lock()
BG_THREAD: Optional[threading.Thread] = None

PROGRESS: Dict[str, Any] = {
    "running": False,
    "progress": 0,
    "message": "",
    "estimated_time": None,
    "tick": 0,
    "total_ticks": 0,
}

# server.py — PART 2/4: CSV 경로 & 초기화
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # 이미 있으면 그대로 사용
INDEX_HTML = os.path.join(PROJECT_ROOT, "index.html")
FAVICON_ICO = os.path.join(PROJECT_ROOT, "favicon.ico")  # 있으면 서빙, 없으면 204
# 기본 데이터 경로 (환경변수로 오버라이드 가능)
# 프로젝트 구조 기준: .../data/agents/{passenger,vehicle}/...
PROJECT_ROOT = _THIS_FILE.parents[1]    # .../Seongnam_Scenario_1

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
PASSENGER_CSV = os.getenv(
    "PASSENGER_CSV",
    str(DEFAULT_DATA_DIR / "agents" / "passenger" / "passenger_data.csv"),
)
VEHICLE_CSV = os.getenv(
    "VEHICLE_CSV",
    str(DEFAULT_DATA_DIR / "agents" / "vehicle" / "vehicle_data.csv"),
)

def init_state() -> State:
    s = State()
    s.simul_configs.update({
        "dispatch_mode": "ortools",
        "use_eta": False,
        "matrix_mode": "DIST",
        "end_time": 60,
        "monitor_match_threshold": 95.0,
        "ortools_time_limit_sec": 5,
        "max_problem_size": 40000,
    })

    # 존재 확인 + 친절한 오류
    if not os.path.exists(PASSENGER_CSV):
        raise FileNotFoundError(f"PASSENGER_CSV not found: {PASSENGER_CSV}")
    if not os.path.exists(VEHICLE_CSV):
        raise FileNotFoundError(f"VEHICLE_CSV not found: {VEHICLE_CSV}")

    p_df = pd.read_csv(PASSENGER_CSV).head(50)
    v_df = pd.read_csv(VEHICLE_CSV).head(50)

    s.time = int(p_df["ride_time"].min()) if ("ride_time" in p_df.columns and len(p_df)) else 0
    s.active_passenger = p_df.to_dict("records")
    s.empty_vehicle    = v_df.to_dict("records")
    s.paths.update({"save": "./tmp_results"})
    return s

@app.on_event("startup")
def _on_startup():
    global GLOBAL_STATE
    os.makedirs("./tmp_results", exist_ok=True)
    print("[startup] PROJECT_ROOT =", PROJECT_ROOT)
    print("[startup] PASSENGER_CSV =", PASSENGER_CSV)
    print("[startup] VEHICLE_CSV  =", VEHICLE_CSV)
    GLOBAL_STATE = init_state()


# server.py — PART 3/4: tick, background loop, saving
import time
import json

def _summarize_status(state: State) -> str:
    """콘솔/대시보드용 짧은 상태 요약 문자열."""
    rec = (state.records or [{}])[-1] if getattr(state, "records", None) else {}
    ana = getattr(state, "analysis", {}) or {}
    assigned = rec.get("assigned", 0)
    unassigned = rec.get("unassigned", 0)
    last_rate = ana.get("last_match_rate")
    cum_rate  = ana.get("cum_match_rate")
    return f"assigned={assigned}, unassigned={unassigned}, last={last_rate}%, cum={cum_rate}%"

def _save_outputs(state: State):
    """파일 저장(요약/시계열/차트). 실패해도 서버는 계속 동작."""
    try:
        os.makedirs("./tmp_results", exist_ok=True)
        # records
        if getattr(state, "records", None):
            pd.DataFrame(state.records).to_csv("./tmp_results/records.csv", index=False)
        # analysis history (없으면 마지막 한 개라도)
        hist = getattr(state, "analysis_history", []) or []
        if not hist and getattr(state, "analysis", None):
            hist = [state.analysis]
        if hist:
            pd.DataFrame(hist).to_csv("./tmp_results/analysis.csv", index=False)
            with open("./tmp_results/analysis.json", "w") as f:
                json.dump(hist, f, ensure_ascii=False, indent=2)
        # chart series
        try:
            series = build_chart_series(state.records, hist)
            with open("./tmp_results/chart_series.json", "w") as f:
                json.dump(series, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # chart는 선택 항목이니 실패해도 무시
            print("[chart_series] skip:", e)
    except Exception as e:
        print("[save_outputs] error:", e)

def tick_once(total_ticks: int):
    """
    틱 1회 실행:
      - run_dispatch -> analyze -> history append -> time += 5
      - PROGRESS 갱신
    """
    global GLOBAL_STATE, PROGRESS
    with LOCK:
        # 핵심 계산
        GLOBAL_STATE = run_once("run_dispatch", GLOBAL_STATE)
        GLOBAL_STATE = run_once("analyze", GLOBAL_STATE)
        # history
        h = getattr(GLOBAL_STATE, "analysis_history", []) or []
        h.append(getattr(GLOBAL_STATE, "analysis", {}) or {})
        GLOBAL_STATE.analysis_history = h
        # 시간 전진(필요시 조정)
        GLOBAL_STATE.time = int(GLOBAL_STATE.time or 0) + 5

        # 진행률/메시지 업데이트
        PROGRESS["tick"] += 1
        PROGRESS["progress"] = int(100 * PROGRESS["tick"] / max(1, total_ticks))
        PROGRESS["message"] = _summarize_status(GLOBAL_STATE)

def _bg_loop(total_ticks: int, sleep_sec: float = 0.0):
    """
    백그라운드 루프: total_ticks 회 tick_once 실행.
    예외 발생 시 진행중 플래그 초기화하고 메시지 기록.
    """
    global PROGRESS, BG_THREAD
    started_at = time.time()
    try:
        for _ in range(total_ticks):
            # 추정 남은 시간 단순 계산(선택)
            elapsed = max(0.001, time.time() - started_at)
            per_tick = elapsed / max(1, PROGRESS["tick"])
            remain   = (total_ticks - PROGRESS["tick"]) * per_tick if PROGRESS["tick"] > 0 else None
            PROGRESS["estimated_time"] = int(remain) if remain is not None else None

            tick_once(total_ticks)

            if sleep_sec > 0:
                time.sleep(sleep_sec)
    except Exception as e:
        with LOCK:
            PROGRESS["running"] = False
            PROGRESS["message"] = f"error: {e}"
        print("[bg_loop] error:", e)
    finally:
        with LOCK:
            PROGRESS["progress"] = 100
            PROGRESS["running"] = False
            PROGRESS["estimated_time"] = 0
        # 마지막 산출물 저장
        _save_outputs(GLOBAL_STATE)
        BG_THREAD = None


# server.py — PART 4/4: models & endpoints
from fastapi import BackgroundTasks, HTTPException
from typing import List

# ---------- Pydantic Models ----------
class CommandIn(BaseModel):
    text: str

class ProcessCommandOut(BaseModel):
    intent_type: str
    message: str

class StartSimIn(BaseModel):
    total_ticks: int = 12      # 기본 12틱 (원하면 프론트에서 조절)
    sleep_sec: float = 0.0     # 틱 사이 딜레이(시연용)

class StatusOut(BaseModel):
    running: bool
    progress: int
    message: str
    estimated_time: Optional[int] = None
    tick: int
    total_ticks: int

class AnalysisOut(BaseModel):
    last: dict
    history_len: int

# ---------- Intent routing helper ----------
def _detect_intent(text: str) -> str:
    t = (text or "").strip().lower()
    # 아주 단순한 규칙 기반 (필요시 확장)
    if any(k in t for k in ["시작", "실행", "run", "start", "simulate", "simulation"]):
        return "START_SIMULATION"
    if any(k in t for k in ["상태", "진행", "진도", "progress", "status", "매칭률"]):
        return "STATUS_CHECK"
    if any(k in t for k in ["분석", "리포트", "report", "analysis"]):
        return "ANALYZE"
    return "GENERAL"

def _status_message() -> str:
    global GLOBAL_STATE
    if GLOBAL_STATE is None:
        return "state not initialized"
    return _summarize_status(GLOBAL_STATE)

# ---------- Endpoints ----------
@app.post("/process-command", response_model=ProcessCommandOut)
def process_command(cmd: CommandIn):
    """
    프론트 채팅 입력 → 간단 intent 분류 후 메시지 반환
    - START_SIMULATION 이면 프론트가 /start-simulation 호출/폴링 시작
    - STATUS_CHECK 이면 현재 진행 요약 반환
    - ANALYZE 이면 즉석 분석 1회 후 요약 반환
    """
    global GLOBAL_STATE
    intent = _detect_intent(cmd.text)

    if intent == "START_SIMULATION":
        return ProcessCommandOut(intent_type="START_SIMULATION",
                                 message="시뮬레이션을 시작합니다. 진행률을 표시할게요.")

    if intent == "STATUS_CHECK":
        return ProcessCommandOut(intent_type="STATUS_CHECK",
                                 message=_status_message())

    if intent == "ANALYZE":
        with LOCK:
            GLOBAL_STATE = run_once("analyze", GLOBAL_STATE)
            # history에 누적
            h = getattr(GLOBAL_STATE, "analysis_history", []) or []
            h.append(getattr(GLOBAL_STATE, "analysis", {}) or {})
            GLOBAL_STATE.analysis_history = h
        return ProcessCommandOut(intent_type="ANALYZE",
                                 message="분석 완료: " + _status_message())

    # GENERAL/기타
    return ProcessCommandOut(
        intent_type="GENERAL",
        message="명령 예) '시뮬 시작', '상태 보여줘', '분석 갱신' 등"
    )

@app.post("/start-simulation")
def start_simulation(body: StartSimIn, background_tasks: BackgroundTasks):
    """
    백그라운드로 total_ticks 만큼 틱을 실행.
    실행 중이면 바로 안내하고 종료.
    """
    global PROGRESS, BG_THREAD
    with LOCK:
        if PROGRESS["running"]:
            return {"status": "already_running",
                    "message": _status_message(),
                    "tick": PROGRESS["tick"],
                    "total_ticks": PROGRESS["total_ticks"]}

        PROGRESS["running"] = True
        PROGRESS["progress"] = 0
        PROGRESS["message"] = "starting..."
        PROGRESS["tick"] = 0
        PROGRESS["total_ticks"] = int(body.total_ticks or 12)
        PROGRESS["estimated_time"] = None

    # FastAPI BackgroundTasks 로도 가능하지만, 상태 공유가 편한 스레드 사용
    def _runner():
        _bg_loop(PROGRESS["total_ticks"], sleep_sec=float(body.sleep_sec or 0.0))

    # 이미 BG_THREAD 전역이 있다면 무시하고 새로 교체
    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    BG_THREAD = th

    return {"status": "started",
            "total_ticks": PROGRESS["total_ticks"],
            "sleep_sec": body.sleep_sec}

@app.get("/simulation-status", response_model=StatusOut)
def simulation_status():
    """프론트가 폴링하는 진행률/메시지 엔드포인트."""
    return StatusOut(
        running=bool(PROGRESS["running"]),
        progress=int(PROGRESS["progress"]),
        message=str(PROGRESS["message"]),
        estimated_time=PROGRESS.get("estimated_time"),
        tick=int(PROGRESS["tick"]),
        total_ticks=int(PROGRESS["total_ticks"]),
    )

@app.get("/analysis-latest", response_model=AnalysisOut)
def analysis_latest():
    """
    최신 분석 스냅샷 반환 (대시보드 숫자 갱신용).
    """
    global GLOBAL_STATE
    if GLOBAL_STATE is None:
        raise HTTPException(status_code=500, detail="state not initialized")
    last = getattr(GLOBAL_STATE, "analysis", {}) or {}
    h = getattr(GLOBAL_STATE, "analysis_history", []) or []
    return AnalysisOut(last=last, history_len=len(h))

# --- ADD: top imports ---
from pathlib import Path
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- ADD: CORS (유연하게 전부 허용) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 엄격히 하려면 후에 http://127.0.0.1:8000 만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ADD: serve index.html at "/" (이미 있다면 건너뛰기) ---
THIS_DIR = Path(__file__).resolve().parent
INDEX_FILE = THIS_DIR / "index.html"
STATIC_DIR = THIS_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=FileResponse)
def serve_index():
    return FileResponse(str(INDEX_FILE))

@app.get("/", response_class=HTMLResponse)
def _serve_index():
    return FileResponse(INDEX_HTML, media_type="text/html")

@app.get("/favicon.ico")
def _favicon():
    if os.path.exists(FAVICON_ICO):
        return FileResponse(FAVICON_ICO, media_type="image/x-icon")
    return HTMLResponse(status_code=204)

class CommandIn(BaseModel):
    text: str



class CommandIn(BaseModel):
    text: str
    # 어떤 파서를 쓸지 선택 (기본값: hybrid)
    parser: Literal["simple", "legacy", "hybrid"] = "hybrid"

@app.post("/process-command")
def process_command(req: CommandIn = Body(...)) -> Dict[str, Any]:
    global GLOBAL_STATE
    if GLOBAL_STATE is None:
        GLOBAL_STATE = init_state()

    text = (req.text or "").strip()

    # 1) 파서 선택
    if req.parser == "simple":
        res = parse_command_simple(text)
    elif req.parser == "legacy":
        res = parse_command_legacy(text)
    else:  # "hybrid"
        res = parse_command_hybrid(text)

    intent_type = res.intent
    slots: Dict[str, Any] = res.slots or {}

    # 2) 즉시 반영 가능한 설정 업데이트
    cfg = GLOBAL_STATE.simul_configs
    if "dispatch_mode" in slots: cfg["dispatch_mode"] = slots["dispatch_mode"]
    if "matrix_mode"   in slots: cfg["matrix_mode"]   = slots["matrix_mode"]
    if "use_eta"       in slots: cfg["use_eta"]       = bool(slots["use_eta"])
    if "end_time"      in slots: cfg["end_time"]      = int(slots["end_time"])

    # CSV 교체(옵션)
    import pandas as pd
    if "passenger_csv" in slots:
        try:
            p_df = pd.read_csv(slots["passenger_csv"])
            GLOBAL_STATE.active_passenger = p_df.to_dict("records")
        except Exception as e:
            return {"intent_type": "ERROR", "message": f"승객 CSV 로드 실패: {e}"}

    if "vehicle_csv" in slots:
        try:
            v_df = pd.read_csv(slots["vehicle_csv"])
            GLOBAL_STATE.empty_vehicle = v_df.to_dict("records")
        except Exception as e:
            return {"intent_type": "ERROR", "message": f"차량 CSV 로드 실패: {e}"}

    # 3) 인텐트 실행 (LangGraph 스타일 실행기)
    # orchestrator.act_on_intent 을 쓰는 버전:
    from web_interface.graph.orchestrator import act_on_intent
    GLOBAL_STATE, payload = act_on_intent(intent_type, slots, GLOBAL_STATE)

    # 사용자가 이해하기 쉬운 안내 메시지 보강
    payload.setdefault("intent_type", intent_type)
    payload.setdefault("message", res.reason or f"{intent_type} 처리됨")
    payload["slots"] = slots
    payload["parser"] = req.parser
    return payload