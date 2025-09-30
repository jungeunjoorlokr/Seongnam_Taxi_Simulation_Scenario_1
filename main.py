"""
Seongnam TAXI Simulation - Main Execution Script
대한민국 경기도 성남시 택시 시뮬레이션 메인 실행 스크립트

This script serves as the orchestrator of the simulation pipeline,
delegating detailed logic to individual modules.
이 스크립트는 시뮬레이션 파이프라인의 orchestrator 역할을 수행하며,
세부 로직은 각 모듈에 위임됩니다.
"""

# =========== External Library Imports ===========

import os
import sys
import json
import time
import warnings
from datetime import datetime
import pandas as pd

warnings.filterwarnings('ignore')

# =========== Internal Module Imports ===========


from modules.engine.simulator import Simulator
from modules.engine.config_manager import base_configs
from modules.preprocess.data_preprocessor import get_preprocessed_data
from modules.analytics.dashboard import ( generate_dashboard_materials, dashboard_config, generate_simulation_result_json)
from modules.analytics.dashboard import generate_html_js_files
from modules.analytics.dashboard import sync_to_npm
# =========== CONFIGURATION ===========

NUM_TAXIS = 950  # 시뮬레이션에 사용할 택시 수
TIME_RANGE_START = 1380  # 23:00
TIME_RANGE_END   = 1440  # 26:00
DASHBOARD_TEMPLATE = "./visualization/dashboard/index_simulation_base.html"

print("\n" + "=" * 40)
print("Seongnam Taxi Simulation System")

# =========== CONFIGURATION ===========

simul_configs = base_configs.copy()

simul_configs['target_region'] = 'Seongnam, South Korea'
simul_configs['relocation_region'] = 'seongnam'
simul_configs['additional_path'] = 'scenario_base'
simul_configs['dispatch_mode'] = 'in_order'
simul_configs['time_range'] = [TIME_RANGE_START, TIME_RANGE_END] # data time range in minutes
simul_configs['matrix_mode'] = 'haversine_distance'
simul_configs['add_board_time'] = 0.2
simul_configs['add_disembark_time'] = 0.2

# =========== DATA LOADING ===========

passengers = pd.read_csv('./data/agents/passenger/passenger_data.csv')
vehicles   = pd.read_csv('./data/agents/vehicle/vehicle_data.csv')

if NUM_TAXIS and NUM_TAXIS < len(vehicles):
        vehicles = vehicles.head(NUM_TAXIS).reset_index(drop=True)
        print(f"[Setting] Vehicles = {NUM_TAXIS}, Time = {TIME_RANGE_START//60:02d}:00~{TIME_RANGE_END//60:02d}:00")

else :
        print("[Setting] Vehicles = {NUM_TAXIS}, Time = {TIME_RANGE_START//60:02d}:00~{TIME_RANGE_END//60:02d}:00")
passengers, vehicles = get_preprocessed_data(passengers, vehicles, simul_configs)

# =========== SIMULATION ===========

start_time = time.time()
simulator = Simulator(passengers=passengers, vehicles=vehicles, configs=simul_configs)
simulator.run()


# =========== RESULTS ===========

save_path = simul_configs['save_path']
passengers_j = pd.read_json(os.path.join(save_path, 'passenger_marker.json'))
trip_j       = pd.read_json(os.path.join(save_path, 'trip.json'))
records_csv  = pd.read_csv(os.path.join(save_path, 'record.csv'))

result = generate_simulation_result_json(passengers_j, trip_j, records_csv)
result.to_json(os.path.join(save_path, 'result.json'), orient='records')

# =========== DASHBOARD ===========

simulation_name = os.path.basename(simul_configs['save_path'])
print(f"Simulation name: {simulation_name}")

# Dashboard configuration   (dashboard_config is in modules/analytics/dashboard.py)
dash_config = dashboard_config.copy()
dash_config['time_range'] = simul_configs['time_range']
dash_config['base_path'] = './simul_result/scenario_base/'
dash_config['save_figure_path'] = f"./visualization/dashboard/assets/figure/{os.path.basename(save_path)}_figures/"
dash_config['save_file_path']   = f"./visualization/dashboard/assets/data/{os.path.basename(save_path)}_data/"
dash_config['save_html_path'] = "./visualization/dashboard/assets/html/index_{simulation_name}.html"

os.makedirs(dash_config['save_figure_path'], exist_ok=True)
os.makedirs(dash_config['save_file_path'], exist_ok=True)
os.makedirs(dash_config['save_html_path'], exist_ok=True) 


generate_dashboard_materials(dash_config, os.path.basename(save_path))

generate_html_js_files(simulation_name)

sync_to_npm(simul_configs)


print("\n Result:")
print(f"→ Dashboard: open ./visualization/dashboard/assets/html/index_{simulation_name}.html")
print("→ npm run : cd visualization/simulation && npm run dev")
print("=" * 40)