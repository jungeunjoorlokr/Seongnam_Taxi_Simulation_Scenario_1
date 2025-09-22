import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import clear_output


# Generate directory path for saving simulation results
def generate_path_to_save(result_folder_name=None, additional_path=None):
    # Create base directory
    base_path = os.path.join(os.getcwd(), "simul_result") 
    if not os.path.isdir(base_path):
        os.mkdir(base_path)
        
    # Add additional path if specified
    if additional_path is not None:
        base_path = os.path.join(base_path, additional_path)
        if not os.path.isdir(base_path):
            os.mkdir(base_path)
    
    # Create result folder with unique name
    if result_folder_name is not None:
        if result_folder_name not in os.listdir(base_path):
            base_path = os.path.join(base_path, result_folder_name)
            os.mkdir(base_path)
        else:
            # Generate unique folder name if exists
            result_folder_name = f"simulation_{len(os.listdir(base_path)) + 1}"
            base_path = os.path.join(base_path, result_folder_name)
            os.mkdir(base_path)
    else:
        # Auto-generate folder name
        result_folder_name = f"simulation_{len(os.listdir(base_path)) + 1}"
        base_path = os.path.join(base_path, result_folder_name)
        os.mkdir(base_path)
        
    return base_path


# Save data to JSON file (append if exists)
def save_json_data(current_data, save_path, file_name):
    file_path = f'{save_path}/{file_name}.json'
    
    if os.path.isfile(file_path): 
        # Append to existing file
        with open(file_path, 'r') as f:
            prior_data = json.load(f)
        
        prior_data.extend(current_data)
        
        with open(file_path, 'w') as f:
            json.dump(prior_data, f)
    else:
        # Create new file
        with open(file_path, 'w') as f:
            json.dump(current_data, f)    


# Track and visualize simulation progress
def checking_progress(simulation_record, current_time, requested_passenger, 
                     fail_passenger, empty_vehicle, active_vehicle, inform):
    
    time_range = inform['time_range']
    save_path = inform['save_path']

    # Record current simulation state
    current_record = pd.DataFrame({
        'time': [current_time],
        'waiting_passenger_cnt': [len(requested_passenger)],
        'fail_passenger_cnt': [len(fail_passenger)],
        'empty_vehicle_cnt': [len(empty_vehicle)],
        'driving_vehicle_cnt': [len(active_vehicle)]
    })

    simulation_record = pd.concat([simulation_record, current_record]).reset_index(drop=True)

    # Display operation graph
    if inform.get('view_operation_graph', True):
        clear_output(True)
        plt.figure(figsize=(18, 10))
        plt.rcParams['axes.grid'] = True 
        
        plt.plot(simulation_record['time'].values, 
                simulation_record['waiting_passenger_cnt'].values, 
                label=f"Waiting passengers ({len(requested_passenger)})", 
                color='royalblue')
        
        plt.plot(simulation_record['time'].values, 
                simulation_record['empty_vehicle_cnt'].values, 
                label=f"Idle vehicles ({len(empty_vehicle)})", 
                color='darkorange')
        
        plt.plot(simulation_record['time'].values, 
                simulation_record['driving_vehicle_cnt'].values, 
                label=f"In-service vehicles ({len(active_vehicle)})", 
                color='limegreen')
        
        plt.legend()

    # Save final simulation record
    if current_time == (time_range[-1] - 1):
        simulation_record.to_csv(f'{save_path}/record.csv', index=False)
    
    return simulation_record