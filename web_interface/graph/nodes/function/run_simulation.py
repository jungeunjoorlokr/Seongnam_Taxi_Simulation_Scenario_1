# web_interface/graph/nodes/function/run_simulation.py
from __future__ import annotations

"""
function/run_simulation.py

역할:
- main.py를 서브프로세스로 실행한다.
- state.params의 값(NUM_TAXIS, TIME_RANGE, DISPATCH_MODE)을 ENV로 전달한다.
- 실행 전용 폴더(run_{run_id})를 만들고 ENV(RUN_DIR)로 전달한다.
- 성공 후에는 시각화 기본 저장소(visualization/simulation/public/data)의 산출물을
  이번 실행 폴더(run_dir)로 사후 복사(post-copy)하여 실행별 아카이브를 보존한다.
- 종료코드/표준출력/표준오류/실행시간 로깅 및 결과 경로를 state에 반영한다.

입력(state에서 참조):
- params: dict (예: {"num_taxis": 900, "time_range": [1380,1560], "dispatch_mode": "default"})
- run_id: str (없으면 여기서 생성)

출력(partial state):
- run_id: str
- message: str
- result_base_dir: str (이번 실행 결과 폴더 경로)
- result_paths: dict[str, str] (사후 복사한 파일 경로 매핑)
- errors: list[str] (실패 시)

데이터 I/O:
- 서브프로세스로 프로젝트 루트의 main.py 실행
- stdout/stderr 캡처
- 시각화 기본 저장소 → run_dir 사후 복사
"""

from typing import Dict, Any, List
import os, sys, time, shutil, subprocess
from pathlib import Path

from ...state import GraphStateV1
from ...utils.log import new_run_id, log_event
from ...utils.config import PROJECT_ROOT
from ...utils.io import ensure_run_dir

NODE_METADATA = {
    "type": "function",
    "timeout": 1800,
    "retries": 0,
    "description": "Run main.py (subprocess) with ENV; archive outputs into run_dir (post-copy).",
}

# 사후 복사 대상 파일명(파이프라인 스펙)
REQUIRED_FILES: List[str] = [
    "result.json",
    "trip.json",
    "passenger_marker.json",
    "vehicle_marker.json",
    "record.csv",
]


def _build_env_from_params(params: Dict[str, Any]) -> Dict[str, str]:
    env = os.environ.copy()

    # num_taxis
    nt = params.get("num_taxis")
    if isinstance(nt, int) and nt > 0:
        env["NUM_TAXIS"] = str(nt)

    # time_range: [start_min, end_min]
    tr = params.get("time_range")
    if isinstance(tr, (list, tuple)) and len(tr) == 2:
        try:
            start, end = int(tr[0]), int(tr[1])
            env["TIME_RANGE_START"] = str(start)
            env["TIME_RANGE_END"] = str(end)
        except Exception:
            pass

    # dispatch_mode
    dm = params.get("dispatch_mode")
    if isinstance(dm, str):
        env["DISPATCH_MODE"] = dm.strip().lower()

    return env


def _copy_outputs_to_run_dir(run_dir: Path) -> Dict[str, str]:
    """
    시각화 기본 저장소(visualization/simulation/public/data)에 있는 산출물을
    run_dir로 복사한다. 존재하는 파일만 복사.
    """
    src_dir = PROJECT_ROOT / "visualization" / "simulation" / "public" / "data"
    result_paths: Dict[str, str] = {}

    if not src_dir.exists():
        return result_paths

    run_dir.mkdir(parents=True, exist_ok=True)

    for fname in REQUIRED_FILES:
        src = src_dir / fname
        if src.is_file() and src.stat().st_size > 0:
            dst = run_dir / fname
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            result_paths[fname] = str(dst)

    return result_paths


def run_simulation(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id") or new_run_id()
    params = state.get("params") or {}

    # 실행 전용 폴더 (예: simul_result/run_YYYYMMDD-HHMMSS)
    run_dir = Path(ensure_run_dir(run_id))

    timeout_sec = int(os.getenv("RUN_SIM_TIMEOUT", "60"))  # 필요 시 환경변수로 조절

    log_event(
        run_id=run_id,
        node="function/run_simulation",
        level="INFO",
        message=f"starting main.py (timeout={timeout_sec}s)",
        extra={"params": params, "run_dir": str(run_dir)},
    )

    # 실행 대상 경로
    main_py = PROJECT_ROOT / "main.py"
    if not main_py.is_file():
        msg = f"main.py not found at {main_py}"
        log_event(run_id, "function/run_simulation", "ERROR", msg)
        return {
            "run_id": run_id,
            "message": "시뮬레이션 실행 실패",
            "result_base_dir": str(run_dir),
            "errors": (state.get("errors") or []) + [msg],
        }

    # ENV 구성 + RUN_DIR 전달 (메인이 사용할 수도 있음)
    env = _build_env_from_params(params)
    env["RUN_DIR"] = str(run_dir)

    # venv의 파이썬으로 실행
    cmd = [sys.executable, str(main_py)]

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        duration = round(time.time() - t0, 2)
        msg = f"main.py timed out after {timeout_sec}s"
        stdout_tail = (getattr(e, "stdout", "") or "")[-500:]
        log_event(
            run_id,
            "function/run_simulation",
            "ERROR",
            msg,
            extra={"stdout_tail": stdout_tail, "duration_s": duration},
        )
        return {
            "run_id": run_id,
            "message": "시뮬레이션 실행 타임아웃",
            "result_base_dir": str(run_dir),
            "errors": (state.get("errors") or []) + [msg],
        }

    duration = round(time.time() - t0, 2)
    stdout_tail = (proc.stdout or "").strip()[-500:]
    stderr_tail = (proc.stderr or "").strip()[-500:]

    if proc.returncode != 0:
        msg = f"main.py returned non-zero exit code={proc.returncode}"
        log_event(
            run_id,
            "function/run_simulation",
            "ERROR",
            msg,
            extra={"stderr_tail": stderr_tail, "duration_s": duration},
        )
        return {
            "run_id": run_id,
            "message": "시뮬레이션 실행 실패",
            "result_base_dir": str(run_dir),
            "errors": (state.get("errors") or []) + [msg, stderr_tail],
        }

    # ── 성공: 사후 복사(Post-copy)로 실행별 아카이브 보존 ─────────────────
    copied = _copy_outputs_to_run_dir(run_dir)
    copied_count = len(copied)

    log_event(
        run_id,
        "function/run_simulation",
        "INFO",
        f"main.py finished successfully; archived {copied_count} files into run_dir",
        extra={"stdout_tail": stdout_tail, "duration_s": duration, "archived": copied},
    )

    msg_ok = f"시뮬레이션 실행 완료 ({duration}s), 결과 {copied_count}개 보존됨"
    return {
        "run_id": run_id,
        "message": msg_ok,
        "result_base_dir": str(run_dir),
        "result_paths": copied,  # 사후 복사된 경로를 바로 넘겨, 다음 노드가 이 경로를 활용 가능
    }