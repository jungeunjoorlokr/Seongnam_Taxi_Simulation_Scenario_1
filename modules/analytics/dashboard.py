import os 
import json 
import osmnx as ox
import numpy as np
import pandas as pd
import geopandas as gpd
import shutil
import os

from modules.engine.config_manager import base_configs

dashboard_config = {
                    # path
                    'base_path':'./simul_result/scenario_base/',
                    'save_figure_path': "./visualization/dashboard/assets/figure/",
                    'save_file_path': "./visualization/dashboard/assets/data/",
                    'region_boundary_file_path': "./data/etc/seongnam_boundary.geojson",
                    # time range
                    'time_range' : base_configs['time_range'], 
                    # target region
                    'target_region_name' : '성남시',
                    # mapboxkey
                    'mapboxKey' : "pk.eyJ1Ijoic3BlYXI1MzA2IiwiYSI6ImNremN5Z2FrOTI0ZGgycm45Mzh3dDV6OWQifQ.kXGWHPRjnVAEHgVgLzXn2g",
                    }



    

'''level_of_service'''
# import numpy as np 
from .service_charts import figure_1, figure_2, figure_3
def generate_level_of_service_figures(base_path, save_path, time_range, simulation_name=None):
    # Time variables
    time_bins = [tm for tm in range(time_range[0], time_range[1], 60)]
    time_bins.append(np.inf)
    time_single_labels = [str(int(tm/60)).zfill(2) + ":00" for tm in range(time_range[0], time_range[1], 60)]
    time_double_labels = [str(int(tm/60)).zfill(2) + '-' + str(int(tm/60)+1).zfill(2) for tm in range(time_range[0], time_range[1], 60)]

   # Figures
    figure_1(base_path, time_range=time_range, time_bins=time_bins, time_single_labels=time_single_labels, simulation_name=simulation_name, save_path=save_path)
    figure_2(base_path, time_bins=time_bins, time_single_labels=time_single_labels, time_double_labels=time_double_labels, simulation_name=simulation_name, save_path=save_path)
    figure_3(base_path, time_range=time_range, time_bins=time_bins, time_single_labels=time_single_labels, simulation_name=simulation_name, save_path=save_path)

'''vehicle_operation_status'''
# import numpy as np 
from .fleet_charts import figure_4, figure_5
def generate_vehicle_operation_figures(base_path, save_path, time_range, simulation_name=None):
    # Time variables
    time_bins = [tm for tm in range(time_range[0], time_range[1], 60)]
    time_bins.append(np.inf)
    time_single_labels = [str(int(tm/60)).zfill(2) + ":00" for tm in range(time_range[0], time_range[1], 60)]

    # Figures
    figure_4(base_path, time_range=time_range, time_single_labels=time_single_labels, simulation_name=simulation_name, save_path=save_path)
    figure_5(base_path, time_bins=time_bins, time_single_labels=time_single_labels, simulation_name=simulation_name, save_path=save_path)

'''spatial_distribution'''
# import osmnx as ox
# import numpy as np
# import geopandas as gpd
from .spatial_charts import figure_6_7_N_8_9, figure_10, figure_11
def generate_spatial_distribution_figures(base_path, save_path, region_boundary_file_path, time_range, target_region_name, mapboxKey, simulation_name=None):
    # Geometry
    place_geometry = ox.geocode_to_gdf([target_region_name])
    region_boundary = gpd.read_file(region_boundary_file_path)
    region_boundary = region_boundary.loc[region_boundary['SGG_NM'].str.contains(target_region_name)].reset_index(drop=True)
    
    # Figures
    figure_6_7_N_8_9(base_path, place_geometry, mapboxKey = mapboxKey, time_range=time_range, status='pickup', simulation_name=simulation_name, save_path = save_path)
    figure_6_7_N_8_9(base_path, place_geometry, mapboxKey = mapboxKey, time_range=time_range, status='dropoff', simulation_name=simulation_name, save_path = save_path)
    figure_10(base_path, place_geometry, region_boundary, mapboxKey = mapboxKey, simulation_name=simulation_name, save_path = save_path)
    figure_11(base_path, place_geometry, region_boundary, mapboxKey = mapboxKey, simulation_name=simulation_name, save_path = save_path)
    


'''simulation_configurations'''
def simulation_configuration_for_dashboard(base_path, save_path, simulation_name=None):
    simul_result_inf = {
        'total_calls': [],
        'failed_calls':[],
        'failure_rate':[],
        'vehicles_driven':[]
    }
    if simulation_name:
        folders_to_process = [simulation_name]
    else:
        folders_to_process = [fd for fd in os.listdir(base_path) 
                            if not fd.startswith('.') and 
                            os.path.isdir(os.path.join(base_path, fd)) and 
                            fd.startswith("simulation_")]
    for fd_nm in folders_to_process: 
        folder_path = os.path.join(base_path, fd_nm)

        passengers = pd.read_json(base_path + fd_nm + '/passenger_marker.json')
        passenger_number = len(set(passengers['passenger_id']))
        simul_result_inf['total_calls'].append(passenger_number)
        
        records = pd.read_csv(base_path + fd_nm + '/record.csv')
        records['operating_vehicle_cnt'] = records['empty_vehicle_cnt'] + records['driving_vehicle_cnt']
        failed_calls_num = records['fail_passenger_cnt'].iloc[-1]
        failure_rate = round((failed_calls_num / passenger_number) * 100, 2)    
        simul_result_inf['failed_calls'].append(failed_calls_num)
        simul_result_inf['failure_rate'].append(failure_rate)
        
        vehicles = pd.read_json(base_path + fd_nm + '/vehicle_marker.json')
        vehicle_id_1 = set(vehicles['vehicle_id'])
        trips = pd.read_json(base_path + fd_nm + '/trip.json')
        vehicle_id_2 = set(trips['vehicle_id'])
        vehicle_driven_num = len(vehicle_id_1 & vehicle_id_2)
        simul_result_inf['vehicles_driven'].append(vehicle_driven_num)

    simul_result_inf = pd.DataFrame(simul_result_inf)
    # 개별 시뮬레이션이면 평균 계산 안함
    if simulation_name:
        # 개별 시뮬레이션: 첫 번째 행만 사용 (평균 계산 안함)
        simul_result_inf = simul_result_inf.iloc[0:1]
    else:
        # 평균: 기존 방식대로 평균 계산
        simul_result_inf = pd.DataFrame(simul_result_inf.mean()).T

    simul_result_inf[['total_calls', 'failed_calls', 'vehicles_driven']] = simul_result_inf[['total_calls', 'failed_calls', 'vehicles_driven']].fillna(0).astype(int)  # NaN을 0으로 채움.astype(int))
    #simul_result_inf[['total_calls', 'failed_calls', 'vehicles_driven']] = simul_result_inf[['total_calls', 'failed_calls', 'vehicles_driven']].astype(int)
    simul_result_inf['failure_rate'] = round(simul_result_inf['failure_rate'], 2)

    if save_path != None:
        simul_result_inf.to_json(f'{save_path}stats.json', orient='records')
    else: 
        return simul_result_inf
def generate_simulation_result_json(passengers, trip, records, time_range=[0, 1440]):
    trip['start_time'] = [ts[0] for ts in trip['timestamp']]
    trip['end_time'] = [ts[-1] for ts in trip['timestamp']]
    passengers['start_time'] = [ts[0] for ts in passengers['timestamp']]
    passengers['end_time'] = [ts[-1] for ts in passengers['timestamp']]

    driving_vehicle_num_lst = []
    dispatched_vehicle_num_lst = []
    occupied_vehicle_num_lst = []
    empty_vehicle_num_lst = []
    fail_passenger_cumNum_lst = []
    waiting_passenger_num_lst = []
    average_waiting_time_lst = []
    current_waiting_time_dict_lst = []

    for tm in range(time_range[0], time_range[1]):
        current_record = records.loc[(records['time'] == tm)].reset_index(drop=True)

        if current_record.empty:
            driving_vehicle_num = 0
            dispatched_vehicle_num = 0
            occupied_vehicle_num = 0
            empty_vehicle_num = 0
            fail_passenger_cumNum = 0
            waiting_passenger_num = 0
            average_waiting_time = 0
            current_waiting_time_dict = {}
        else:
            empty_vehicle_num = current_record['empty_vehicle_cnt'].iloc[0]
            driving_vehicle_num = current_record['driving_vehicle_cnt'].iloc[0]
            fail_passenger_cumNum = current_record['fail_passenger_cnt'].iloc[0]

            operating_vehicle = trip.loc[(trip['start_time'] <= tm) & (trip['end_time'] >= tm)].drop_duplicates('vehicle_id')
            dispatched_vehicle = operating_vehicle.loc[operating_vehicle['board'] == 0]
            occupied_vehicle = operating_vehicle.loc[operating_vehicle['board'] == 1]

            dispatched_vehicle_num = len(dispatched_vehicle)
            occupied_vehicle_num = len(occupied_vehicle)

            waiting_passengers = passengers.loc[(passengers['start_time'] <= tm) & (passengers['end_time'] >= tm)].copy()
            waiting_passenger_num = len(waiting_passengers)

            if not waiting_passengers.empty:
                waiting_passengers['wait_time'] = tm - waiting_passengers['start_time']
                average_waiting_time = np.mean(waiting_passengers['wait_time'])

                waiting_passengers['wait_time_cate'] = pd.cut(
                    waiting_passengers['wait_time'],
                    bins=[0, 10, 20, 30, 40, 50, np.inf],
                    labels=[0, 10, 20, 30, 40, 50],
                    right=False
                )
                waiting_time_dictionary = round(
                    waiting_passengers['wait_time_cate'].value_counts(normalize=True) * 100, 2
                ).to_dict()
                current_waiting_time_dict = {str(k): v for k, v in waiting_time_dictionary.items()}
            else:
                average_waiting_time = 0
                current_waiting_time_dict = {}

        # append values
        driving_vehicle_num_lst.append(driving_vehicle_num)
        dispatched_vehicle_num_lst.append(dispatched_vehicle_num)
        occupied_vehicle_num_lst.append(occupied_vehicle_num)
        empty_vehicle_num_lst.append(empty_vehicle_num)
        fail_passenger_cumNum_lst.append(fail_passenger_cumNum)
        waiting_passenger_num_lst.append(waiting_passenger_num)
        average_waiting_time_lst.append(round(average_waiting_time, 1))
        current_waiting_time_dict_lst.append(current_waiting_time_dict)

    results = pd.DataFrame({
        'time': range(time_range[0], time_range[1]),
        'driving_vehicle_num': driving_vehicle_num_lst,
        'dispatched_vehicle_num': dispatched_vehicle_num_lst,
        'occupied_vehicle_num': occupied_vehicle_num_lst,
        'empty_vehicle_num': empty_vehicle_num_lst,
        'fail_passenger_cumNum': fail_passenger_cumNum_lst,
        'waiting_passenger_num': waiting_passenger_num_lst,
        'average_waiting_time': average_waiting_time_lst,
        'current_waiting_time_dict': current_waiting_time_dict_lst
    })

    return results



# MAIN - generate everthing about dashboard
def generate_dashboard_materials(dashboard_config, simulation_name=None):
    simulation_configuration_for_dashboard(dashboard_config['base_path'], dashboard_config['save_file_path'], simulation_name)

    generate_level_of_service_figures(dashboard_config['base_path'], dashboard_config['save_figure_path'],
                                dashboard_config['time_range'], simulation_name)
    generate_vehicle_operation_figures(dashboard_config['base_path'], dashboard_config['save_figure_path'],
                                        dashboard_config['time_range'], simulation_name)
    generate_spatial_distribution_figures(dashboard_config['base_path'], dashboard_config['save_figure_path'], dashboard_config['region_boundary_file_path'], 
                                    dashboard_config['time_range'],
                                    dashboard_config['target_region_name'], dashboard_config['mapboxKey'], simulation_name)



def generate_html_js_files(simulation_name):
    """HTML과 JS 파일을 시뮬레이션별로 생성 (stats.json 데이터 직접 임베드)"""
    
    stats_json_path = f'./visualization/dashboard/assets/data/{simulation_name}_data/stats.json'
    try:
        with open(stats_json_path, 'r') as f:
            stats_data = json.load(f)[0]  
            
        total_calls = stats_data['total_calls']
        failed_calls = stats_data['failed_calls']
        failure_rate = stats_data['failure_rate']
        vehicles_driven = stats_data['vehicles_driven']
                
    except Exception as e:
        print(f"stats.json 읽기 실패, 기본값 사용: {e}")
        total_calls = 0
        failed_calls = 0
        failure_rate = 0.0
        vehicles_driven = 0
    
    js_template = f"""// Stats Loader for {simulation_name}
                // stats.json 데이터를 직접 임베드하여 CORS 문제 회피

                (function() {{
                    // 데이터 직접 임베드 (CORS 없음)
                    const statsData = {{
                        total_calls: {total_calls},
                        failed_calls: {failed_calls},
                        failure_rate: {failure_rate},
                        vehicles_driven: {vehicles_driven}
                    }};
                    
                    // DOM 로드 시 데이터 표시
                    window.addEventListener('DOMContentLoaded', function() {{
                        console.log('통계 데이터 적용 중...', statsData);
                        
                        // 각 요소에 데이터 적용
                        const totalCallsEl = document.getElementById('total-calls');
                        const failedCallsEl = document.getElementById('total-failed-calls');
                        const failureRateEl = document.getElementById('failure-rate');
                        const vehiclesDrivenEl = document.getElementById('vehicles-driven');
                        
                        if (totalCallsEl) totalCallsEl.textContent = statsData.total_calls.toLocaleString();
                        if (failedCallsEl) failedCallsEl.textContent = statsData.failed_calls.toLocaleString();
                        if (failureRateEl) failureRateEl.textContent = statsData.failure_rate.toFixed(2);
                        if (vehiclesDrivenEl) vehiclesDrivenEl.textContent = statsData.vehicles_driven.toLocaleString();
                        
                        console.log('통계 데이터 적용 완료!');
                }});
            }})();
            """
    
    template_path = './visualization/dashboard/index_simulation_base.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    html_content = html_content.replace('simulation_base_figures', f'{simulation_name}_figures')

    html_content = html_content.replace(
        '<script src="./assets/js/stats-loader.js"></script>',
        f'<script src="../js/simulation_stats/stats-loader_{simulation_name}.js"></script>'
    )

    html_content = html_content.replace('./assets/css/', '../css/')
    html_content = html_content.replace('./assets/js/', '../js/')
    html_content = html_content.replace('./assets/figure/', '../figure/')

    import os
    os.makedirs('./visualization/dashboard/assets/js/simulation_stats/', exist_ok=True)
    
     
    js_path = f'./visualization/dashboard/assets/js/simulation_stats/stats-loader_{simulation_name}.js'
    html_path = f'./visualization/dashboard/assets/html/index_{simulation_name}.html'
    
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_template)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path, js_path



def sync_to_npm(simul_configs):
    """시뮬레이션 결과를 visualization/simulation/public/data로 복사 (덮어쓰기)"""
    
    source_dir = simul_configs['save_path']
    target_dir = './visualization/simulation/public/data'
    
    files_to_copy = [
        'passenger_marker.json',
        'vehicle_marker.json', 
        'trip.json',
        'record.csv',
        'result.json'
    ]
    
    os.makedirs(target_dir, exist_ok=True)
    
    for file_name in files_to_copy:
        source_file = os.path.join(source_dir, file_name)
        target_file = os.path.join(target_dir, file_name)
        
        if os.path.exists(source_file):
            shutil.copy2(source_file, target_file)
    