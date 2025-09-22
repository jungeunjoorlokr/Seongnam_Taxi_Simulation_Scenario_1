import pandas as pd
import numpy as np

from .io_manager import save_json_data


# Update passenger status (new requests, failures)
def update_passenger(requested_passenger, fail_passenger, passenger, simul_configs, time):
    fail_time = simul_configs['fail_time']
    save_path = simul_configs['save_path']
    
    # Extract passengers requesting at current time
    current_requested_passenger = passenger[passenger['ride_time'] == time]
    passenger = passenger[passenger['ride_time'] != time].reset_index(drop=True)
    
    if len(requested_passenger) > 0:
        # Increment dispatch waiting time
        requested_passenger['dispatch_time'] = requested_passenger['dispatch_time'] + 1
        
        # Move passengers exceeding fail time to failed status
        current_fail_passenger = requested_passenger[requested_passenger['dispatch_time'] >= fail_time]
        fail_passenger = pd.concat([fail_passenger, current_fail_passenger])
        fail_passenger = fail_passenger.reset_index(drop=True)
        
        if len(current_fail_passenger) > 0:
            # Keep only passengers under fail time threshold
            requested_passenger = requested_passenger[requested_passenger['dispatch_time'] < fail_time]
            
            # Save failed passenger markers
            current_fail_passenger = [
                {
                    'passenger_id': row['ID'], 
                    'status': 0,
                    'location': [row['ride_lon'], row['ride_lat']], 
                    'timestamp': [row['ride_time'], row['ride_time'] + row['dispatch_time']]
                }
                for _, row in current_fail_passenger.iterrows()
            ]
            
            save_json_data(current_fail_passenger, save_path, file_name='passenger_marker')
            del current_fail_passenger
    
    # Add new requests to active passenger pool
    requested_passenger = pd.concat([requested_passenger, current_requested_passenger])
    requested_passenger = requested_passenger.reset_index(drop=True)
    
    return requested_passenger, fail_passenger, passenger


# Update vehicle status (work start, passenger drop-off, work end)
def update_vehicle(active_vehicle, empty_vehicle, vehicle, simul_configs, time):
    save_path = simul_configs['save_path']
    
    # Process vehicles starting work
    current_start_vehicle = vehicle[vehicle['work_start'] == time]
    
    if len(current_start_vehicle) > 0:
        # Select columns based on available data
        if 'cartype' in current_start_vehicle.columns:
            current_start_vehicle = current_start_vehicle[[
                'vehicle_id', 'cartype', 'work_end', 'temporary_stopTime', 'lat', 'lon'
            ]]
        else:
            current_start_vehicle = current_start_vehicle[[
                'vehicle_id', 'work_end', 'temporary_stopTime', 'lat', 'lon'
            ]]
        
        # Initialize passenger fields for empty vehicles
        current_start_vehicle['temporary_stopTime'] = time
        current_start_vehicle['P_ID'] = np.nan
        current_start_vehicle['P_ride_lat'] = np.nan
        current_start_vehicle['P_ride_lon'] = np.nan
        current_start_vehicle['P_alight_lat'] = np.nan
        current_start_vehicle['P_alight_lon'] = np.nan
        current_start_vehicle['P_request_time'] = np.nan
        current_start_vehicle['P_disembark_time'] = np.nan
        
        empty_vehicle = pd.concat([empty_vehicle, current_start_vehicle])
        empty_vehicle = empty_vehicle.reset_index(drop=True)
        
        # Remove started vehicles from pending pool
        vehicle = vehicle[vehicle['work_start'] != time].reset_index(drop=True)
        
    # Process passenger drop-offs
    if len(active_vehicle) > 0:
        current_empty_vehicle = active_vehicle[active_vehicle['P_disembark_time'] <= time].copy()
        
        if len(current_empty_vehicle) > 0:
            # Update vehicle location to drop-off point
            current_empty_vehicle['lat'] = current_empty_vehicle['P_alight_lat']
            current_empty_vehicle['lon'] = current_empty_vehicle['P_alight_lon']
            current_empty_vehicle['temporary_stopTime'] = current_empty_vehicle['P_disembark_time']
            
            # Clear passenger fields
            current_empty_vehicle['P_ID'] = np.nan
            current_empty_vehicle['P_ride_lat'] = np.nan
            current_empty_vehicle['P_ride_lon'] = np.nan
            current_empty_vehicle['P_alight_lat'] = np.nan
            current_empty_vehicle['P_alight_lon'] = np.nan
            current_empty_vehicle['P_disembark_time'] = np.nan
        
            empty_vehicle = pd.concat([empty_vehicle, current_empty_vehicle])
            empty_vehicle = empty_vehicle.reset_index(drop=True)
            
            # Keep only vehicles still in transit
            active_vehicle = active_vehicle[active_vehicle['P_disembark_time'] > time]
            active_vehicle = active_vehicle.reset_index(drop=True)
            
    # Process vehicles ending work
    if len(empty_vehicle) > 0:
        # Find vehicles approaching work end (within 5 minutes)
        end_vehicle = empty_vehicle[empty_vehicle['work_end'] < time + 5]
        end_vehicle = end_vehicle[end_vehicle['temporary_stopTime'] != time]
    
        empty_vehicle = empty_vehicle[empty_vehicle['work_end'] >= time + 5]
        empty_vehicle = empty_vehicle.reset_index(drop=True)
        
        if len(end_vehicle) > 0:
            # Save vehicle markers (excluding NaN stopTime cases)
            if 'cartype' in current_start_vehicle.columns:
                end_vehicle = [
                    {
                        'vehicle_id': row['vehicle_id'], 
                        'cartype': row['cartype'],
                        'location': [row['lon'], row['lat']], 
                        'timestamp': [row['temporary_stopTime'], time]
                    }
                    for _, row in end_vehicle.iterrows() 
                    if not np.isnan(row['temporary_stopTime'])
                ]
            else:
                end_vehicle = [
                    {
                        'vehicle_id': row['vehicle_id'],
                        'location': [row['lon'], row['lat']], 
                        'timestamp': [row['temporary_stopTime'], time]
                    }
                    for _, row in end_vehicle.iterrows() 
                    if not np.isnan(row['temporary_stopTime'])
                ]
            
            save_json_data(end_vehicle, save_path, file_name='vehicle_marker')
            del end_vehicle
    
    return active_vehicle, empty_vehicle, vehicle