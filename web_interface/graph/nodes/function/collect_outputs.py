# web_interface/graph/nodes/function/collect_outputs.py
from __future__ import annotations

"""
function/collect_outputs.py

역할:
- 우선 result_base_dir(이번 실행 폴더)에서 필수 산출물을 수집한다.
- 그다음 시각화 기본 경로(visualization/simulation/public/data)를 본다.
- 그다음 simul_result/scenario_base 아래의 최신 simulation_* 폴더를 본다.
- 그다음 simul_result/latest를 본다.
- 그래도 없으면 프로젝트 루트 전체를 fuzzy 탐색한다.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import os

from ...state import GraphStateV1
from ...utils.config import REQUIRED_OUTPUTS, SIMUL_LATEST_DIR, PROJECT_ROOT
from ...utils.io import exists_nonempty
from ...utils.log import log_event

NODE_METADATA = {
    "type": "function",
    "timeout": 15,
    "retries": 0,
    "description": "Collect output files from run_dir → viz_data → scenario_base → latest → fuzzy(project)",
}

# 이름 유사 매핑 후보 (필요시 추가)
FUZZY_ALIASES = {
    "result.json": ["result.json", "results.json", "output.json"],
    "trip.json": ["trip.json", "trips.json", "trip_data.json"],
    "passenger_marker.json": ["passenger_marker.json", "passengers.json", "passenger_markers.json"],
    "vehicle_marker.json": ["vehicle_marker.json", "vehicles.json", "vehicle_markers.json"],
    "record.csv": ["record.csv", "records.csv", "log.csv", "metrics.csv"],
}

def _collect_exact(base: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for fname in REQUIRED_OUTPUTS:
        p = base / fname
        if exists_nonempty(p):
            out[fname] = str(p)
    return out

def _score_dir(base: Path) -> Tuple[int, float]:
    """
    디렉토리 안에서 REQUIRED_OUTPUTS 중 존재/비지 않은 파일 개수 + 가장 최신 mtime
    (정렬/선택용 스코어)
    """
    count = 0
    newest = 0.0
    for fname in REQUIRED_OUTPUTS:
        p = base / fname
        try:
            if exists_nonempty(p):
                count += 1
                mt = p.stat().st_mtime
                if mt > newest:
                    newest = mt
        except Exception:
            pass
    return count, newest

def _latest_scenario_dir(root: Path) -> Path | None:
    """ simul_result/scenario_base 아래에서 가장 '충분히' 채워진 최신 simulation_* 폴더 선택 """
    if not root.is_dir():
        return None
    cands = []
    for d in root.glob("simulation_*"):
        if d.is_dir():
            score = _score_dir(d)
            cands.append((score, d))
    if not cands:
        return None
    # 개수(desc) → 최신 mtime(desc)
    cands.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)
    return cands[0][1]

def _collect_fuzzy_in(root: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for canon, cands in FUZZY_ALIASES.items():
        best = None
        best_mtime = -1
        for cand in cands:
            for f in root.rglob(cand):
                try:
                    if exists_nonempty(f):
                        mt = f.stat().st_mtime
                        if mt > best_mtime:
                            best, best_mtime = f, mt
                except Exception:
                    pass
        if best:
            out[canon] = str(best)
    return out

def collect_outputs(state: GraphStateV1) -> GraphStateV1:
    run_id = state.get("run_id", "no-runid")

    outputs: Dict[str, str] = {}

    # 1) 이번 실행 폴더 우선
    run_base = state.get("result_base_dir")
    if run_base:
        outputs.update(_collect_exact(Path(run_base)))
        if outputs:
            log_event(run_id, "function/collect_outputs", "INFO",
                      f"collected from run_dir ({len(outputs)}/{len(REQUIRED_OUTPUTS)})",
                      extra={"base": run_base, "files": outputs})
            return {"result_paths": outputs}

    # 2) 시각화 기본 경로 (정은주님 프로젝트에 실제 파일 존재)
    viz_data = Path(PROJECT_ROOT) / "visualization" / "simulation" / "public" / "data"
    if viz_data.is_dir():
        outputs.update(_collect_exact(viz_data))
        if outputs:
            log_event(run_id, "function/collect_outputs", "INFO",
                      f"collected from viz_data ({len(outputs)}/{len(REQUIRED_OUTPUTS)})",
                      extra={"base": str(viz_data), "files": outputs})
            return {"result_paths": outputs}

    # 3) scenario_base 아래 최신 simulation_* 폴더
    scenario_base = Path(SIMUL_LATEST_DIR).parent / "scenario_base"
    latest_sim = _latest_scenario_dir(scenario_base) if scenario_base.exists() else None
    if latest_sim:
        outputs.update(_collect_exact(latest_sim))
        if outputs:
            log_event(run_id, "function/collect_outputs", "INFO",
                      f"collected from scenario_base ({len(outputs)}/{len(REQUIRED_OUTPUTS)})",
                      extra={"base": str(latest_sim), "files": outputs})
            return {"result_paths": outputs}

    # 4) latest 폴더
    latest_dir = Path(SIMUL_LATEST_DIR)
    outputs.update(_collect_exact(latest_dir))
    if outputs:
        log_event(run_id, "function/collect_outputs", "INFO",
                  f"collected from latest ({len(outputs)}/{len(REQUIRED_OUTPUTS)})",
                  extra={"base": str(latest_dir), "files": outputs})
        return {"result_paths": outputs}

    # 5) 최후의 수단: 프로젝트 루트 전체 fuzzy 탐색
    outputs.update(_collect_fuzzy_in(Path(PROJECT_ROOT)))
    if outputs:
        log_event(run_id, "function/collect_outputs", "INFO",
                  f"collected via fuzzy search ({len(outputs)}/{len(REQUIRED_OUTPUTS)})",
                  extra={"files": outputs})
        return {"result_paths": outputs}

    log_event(run_id, "function/collect_outputs", "ERROR",
              "no outputs found (run_dir, viz_data, scenario_base, latest, fuzzy all empty)")
    return {
        "result_paths": {},
        "errors": (state.get("errors") or []) + ["no outputs found (global search)"],
    }