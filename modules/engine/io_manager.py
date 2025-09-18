### extract, dispatch function selector
# - extract_selector
    
### Generate path to save 
import os
def generate_path_to_save(result_folder_name = None, additional_path=None):
    # base path
    base_path = os.path.join(os.getcwd(), "simul_result") 
    if not(os.path.isdir(base_path)):
        os.mkdir(base_path)
        
    # base path + additional_path
    if additional_path != None:
        base_path = os.path.join(base_path, additional_path)
        if not(os.path.isdir(base_path)):
            os.mkdir(base_path)
    
    # folder to save simulation result  
    if result_folder_name != None:
        if not(result_folder_name in os.listdir(base_path)):
            base_path = os.path.join(base_path, result_folder_name)
            os.mkdir(base_path)
        else:
            result_folder_name = f"simulation_{len(os.listdir(base_path)) + 1}"
            base_path = os.path.join(base_path, result_folder_name)
            os.mkdir(base_path)
    else:
        result_folder_name = f"simulation_{len(os.listdir(base_path)) + 1}"
        base_path = os.path.join(base_path, result_folder_name)
        os.mkdir(base_path)
        
    return base_path

### Save json data 
import json
def save_json_data(current_data, save_path, file_name):
    import json, os, traceback
    if os.path.isfile(f'{save_path}/{file_name}.json'): 
        with open(f'{save_path}/{file_name}.json', 'r') as f:
            prior_data = json.load(f)
        
        prior_data.extend(current_data)
        
        with open(f'{save_path}/{file_name}.json', 'w') as f:
            json.dump(prior_data, f)
    else:
        with open(f'{save_path}/{file_name}.json', 'w') as f:
            json.dump(current_data, f)    
    


### Simulation progress check function
import pandas as pd 
import matplotlib.pyplot as plt
from IPython.display import clear_output

def checking_progress(simulation_record, current_time, requested_passenger, fail_passenger, empty_vehicle, active_vehicle, inform):

    time_range = inform['time_range']
    save_path = inform['save_path']

    current_record = pd.DataFrame({
        'time' : [current_time],
        'waiting_passenger_cnt' : [len(requested_passenger)],
        'fail_passenger_cnt' : [len(fail_passenger)],
        'empty_vehicle_cnt' : [len(empty_vehicle)],
        'driving_vehicle_cnt' : [len(active_vehicle)]
        })

    simulation_record = pd.concat([simulation_record, current_record]).reset_index(drop=True)

    # simulation operation graph
    clear_output(True)
    plt.figure(figsize=(18, 10))
    plt.rcParams['axes.grid'] = True 
    plt.plot(simulation_record['time'].values, simulation_record['waiting_passenger_cnt'].values, label = f"waiting passengers ({len(requested_passenger)})", color='royalblue')
    plt.plot(simulation_record['time'].values, simulation_record['empty_vehicle_cnt'].values, label = f"Idle vehicles ({len(empty_vehicle)})", color= 'darkorange')
    plt.plot(simulation_record['time'].values, simulation_record['driving_vehicle_cnt'].values, label = f"In-service vehicles ({len(active_vehicle)})", color= 'limegreen')
    plt.legend()
    #plt.show()

    # save simulation record 
    if current_time == (time_range[-1]-1):
        simulation_record.to_csv(f'{save_path}/record.csv', index=False)
    
    return simulation_record
        

### base configs
base_configs = {'target_region': '성남 대한민국',
                  'problem': 'default',
                  'relocation_region': 'seongnam',
                  'path': None, # simul_result에 원하는 path 그 자리에 생김
                  'additional_path':None, # simul_result에 이 자리위에 생김
                  'time_range':[0, 1440],
                  'fail_time': 10,
                  'add_board_time': 0.2, # 일반 택시 시뮬이라 필요 없음-> 한 10초정도로
                  'add_disembark_time': 0.2,
                  'matrix_mode': 'street_distance', # ['street_distance', 'ETA', 'haversine_distance']
                  'dispatch_mode': 'in_order', # ['optimization', 'in_order']
                  'eta_model': None,
                  'view_operation_graph':True}



### simulation "result.json" 만드는 코드
import os
import pandas as pd
import numpy as np


