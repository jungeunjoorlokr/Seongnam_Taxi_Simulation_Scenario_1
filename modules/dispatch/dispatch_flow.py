import sys
import os
import pandas as pd
import numpy as np 
from multiprocess import Pool

from modules.routing.osrm_client import osrm_routing_machine
from modules.utils.distance_utils import calculate_straight_distance
from modules.engine.io_manager import save_json_data
from modules.dispatch.cost_matrix import dispatch_cost_matrix
from modules.dispatch.dispatch_algorithms import in_order_dispatch, ortools_dispatch


# Convert travel time to ETA result using prediction model
def change_travel_time_to_eta_result(data, time, simul_configs):
    YMD = simul_configs['YMD']
    eta_model = simul_configs['eta_model']

    # Extract time features
    target_minute = time % 60
    target_hour = time // 60

    target_weekday = YMD.weekday()
    target_holiday = 1 if target_weekday >= 5 else 0
    
    # Extract location coordinates
    ride_lat = data[:, 0]
    ride_lon = data[:, 1]
    
    alight_lat = data[:, 2]
    alight_lon = data[:, 3]
    
    # Create input dataframe for ETA model
    eta_inputData = pd.DataFrame({
                                    "minute": target_minute, 
                                    'hour': target_hour, 
                                    'weekday': target_weekday, 
                                    'holiday': target_holiday, 
                                    "ride_lat": ride_lat, 
                                    "ride_lon": ride_lon, 
                                    'alight_lat': alight_lat, 
                                    'alight_lon': alight_lon
    })
    
    # Convert to categorical types
    for col in ['minute', 'hour', 'weekday', 'holiday']:
        eta_inputData[col] = eta_inputData[col].astype('category')

    # Add distance features for metro region
    if simul_configs['relocation_region'] == 'metro':
        eta_inputData['straight_distance'] = calculate_straight_distance(
        eta_inputData['ride_lat'].values, 
        eta_inputData['ride_lon'].values,
        eta_inputData['alight_lat'].values,
        eta_inputData['alight_lon'].values
    )
        
        osrm_rs = [
            osrm_routing_machine([row['ride_lat'], row['ride_lon'], 
                                 row['alight_lat'], row['alight_lon']])
            for _, row in eta_inputData.iterrows()
        ]
        
        eta_inputData['osrm_distance'] = [
            rs['distance'] / 1000 if rs is not None else 0.5 
            for rs in osrm_rs
        ]
        
        eta_inputData = eta_inputData[['weekday', 'holiday', 'hour', 
                                       'minute', 'straight_distance', 'osrm_distance']]   

    # Predict travel time
    eta_result = eta_model.predict(eta_inputData)
    return eta_result


# Process active vehicles and save trip/marker information
def address_current_active_vehicle(current_active_vehicle, time, save_path, simul_configs):
    # Extract origin and destination coordinates
    O = current_active_vehicle[['lat', 'lon', 'P_ride_lat', 'P_ride_lon']].values
    D = current_active_vehicle[['P_ride_lat', 'P_ride_lon', 'P_alight_lat', 'P_alight_lon']].values
    
    # Get OSRM routing results (sequential processing)
    routing_result_O = [osrm_routing_machine(o) for o in O]
    routing_result_D = [osrm_routing_machine(d) for d in D]

    # Apply ETA model if available
    if simul_configs['eta_model'] is not None: 
        eta_result_O = change_travel_time_to_eta_result(O, time, simul_configs)
        eta_result_D = change_travel_time_to_eta_result(D, time, simul_configs)
        
        for idx in range(len(current_active_vehicle)):
            # Adjust origin timestamps
            target_timestamp_O = np.array(routing_result_O[idx]['timestamp'])
            revision_timestamp_O = ((target_timestamp_O / max(target_timestamp_O)) * eta_result_O[idx]).tolist()
            routing_result_O[idx]['timestamp'] = revision_timestamp_O

            # Adjust destination timestamps
            target_timestamp_D = np.array(routing_result_D[idx]['timestamp'])
            revision_timestamp_D = ((target_timestamp_D / max(target_timestamp_D)) * eta_result_D[idx]).tolist()
            routing_result_D[idx]['timestamp'] = revision_timestamp_D

    # Add boarding time
    for idx in range(len(routing_result_D)):
        routing_result_D[idx]['timestamp'] = (
            np.array(routing_result_D[idx]['timestamp']) + simul_configs['add_board_time']
        ).tolist()
    
    # Update disembark time
    current_active_vehicle['P_disembark_time'] = [
        time + o['timestamp'][-1] + d['timestamp'][-1] 
        for o, d in zip(routing_result_O, routing_result_D)
    ]
    current_active_vehicle['P_disembark_time'] += simul_configs['add_disembark_time']
    
    # Save vehicle marker data
    vehicle_marker_inf = current_active_vehicle[
        current_active_vehicle['temporary_stopTime'] != time
    ]
    vehicle_marker_inf = vehicle_marker_inf[
        ~vehicle_marker_inf['temporary_stopTime'].isna()
    ].reset_index(drop=True)
    
    if len(vehicle_marker_inf) >= 1:
        vehicle_marker_inf = [
            {
                'vehicle_id': row['vehicle_id'], 
                'cartype': row['cartype'],
                'location': [row['lon'], row['lat']], 
                'timestamp': [row['temporary_stopTime'], time]
            }
            for _, row in vehicle_marker_inf.iterrows()
        ]
        save_json_data(vehicle_marker_inf, save_path=save_path, file_name='vehicle_marker')
    del vehicle_marker_inf

    # Save passenger marker data
    passenger_marker_inf = current_active_vehicle[['P_ID', 'P_ride_lat', 'P_ride_lon', 'P_request_time']]
    passenger_marker_inf['P_ride_time'] = [o['timestamp'][-1] + time for o in routing_result_O]
    
    if len(passenger_marker_inf) >= 1:
        passenger_marker_inf = [
            {
                'passenger_id': row['P_ID'], 
                'status': 1,
                'location': [row['P_ride_lon'], row['P_ride_lat']],
                'timestamp': [row['P_request_time'], row['P_ride_time']]
            }
            for _, row in passenger_marker_inf.iterrows()
        ]
        save_json_data(passenger_marker_inf, save_path=save_path, file_name='passenger_marker')
    del passenger_marker_inf

    # Save trip data
    O_route = [o['route'] for o in routing_result_O]
    D_route = [d['route'] for d in routing_result_D]
    O_timestamp = [list(np.array(o['timestamp']) + time) for o in routing_result_O]
    D_timestamp = [
        list(np.array(d['timestamp']) + o_timestamp[-1]) 
        for d, o_timestamp in zip(routing_result_D, O_timestamp)
    ]

    trip_inf = current_active_vehicle[['vehicle_id', 'P_ID', 'cartype']]
    trip_inf['O_route'] = O_route
    trip_inf['D_route'] = D_route
    trip_inf['O_timestamp'] = O_timestamp
    trip_inf['D_timestamp'] = D_timestamp

    # Create separate trip records for origin and destination
    trip_inf_O = [
        {
            'vehicle_id': row['vehicle_id'], 
            'cartype': row['cartype'], 
            'passenger_id': row['P_ID'], 
            'board': 0,
            'trip': row['O_route'], 
            'timestamp': row['O_timestamp']
        }
        for _, row in trip_inf.iterrows()
    ]
    
    trip_inf_D = [
        {
            'vehicle_id': row['vehicle_id'], 
            'cartype': row['cartype'],
            'passenger_id': row['P_ID'], 
            'board': 1,
            'trip': row['D_route'], 
            'timestamp': row['D_timestamp']
        }
        for _, row in trip_inf.iterrows()
    ]

    trip_inf = []
    trip_inf.extend(trip_inf_O)
    trip_inf.extend(trip_inf_D)

    save_json_data(trip_inf, save_path=save_path, file_name='trip')
    del trip_inf, trip_inf_O, trip_inf_D
    
    return current_active_vehicle


# Select dispatch method and match passengers with vehicles
def select_dispatch_method(requested_passenger, empty_vehicle, simul_configs, time):
    # Use optimization or in-order dispatch based on configuration
    if simul_configs['dispatch_mode'] == 'optimization':
        cost_matrix = dispatch_cost_matrix(
            requested_passenger, 
            empty_vehicle, 
            time,
            simul_configs
        )
        dispatch_result = ortools_dispatch(requested_passenger, empty_vehicle, cost_matrix)
        del cost_matrix
        
    elif simul_configs['dispatch_mode'] == 'in_order':
        dispatch_result = in_order_dispatch(
            requested_passenger, 
            empty_vehicle,
            time,
            simul_configs
        )

    # Extract matched vehicles and passengers
    dispatch_result_vehicle = empty_vehicle.iloc[dispatch_result['vehicle']][
        ['vehicle_id', 'cartype', 'work_end', 'temporary_stopTime', 'lat', 'lon']
    ].reset_index(drop=True)
    
    dispatch_result_passenger = requested_passenger.iloc[dispatch_result['passenger']][
        ['ID', 'ride_lat', 'ride_lon', 'alight_lat', 'alight_lon', 'ride_time', 'dispatch_time']
    ].reset_index(drop=True)

    # Merge matched data
    current_active_vehicle = pd.concat([dispatch_result_vehicle, dispatch_result_passenger], axis=1)
    current_active_vehicle = current_active_vehicle.rename(columns={
        'ID': 'P_ID', 
        'ride_lat': 'P_ride_lat',
        'ride_lon': 'P_ride_lon',
        'alight_lat': 'P_alight_lat', 
        'alight_lon': 'P_alight_lon', 
        'ride_time': 'P_request_time'
    })
    current_active_vehicle['P_disembark_time'] = 0

    # Update remaining unmatched vehicles and passengers
    empty_vehicle = empty_vehicle.iloc[
        list(set(empty_vehicle.index) - set(dispatch_result['vehicle']))
    ].reset_index(drop=True)
    
    requested_passenger = requested_passenger.iloc[
        list(set(requested_passenger.index) - set(dispatch_result['passenger']))
    ].reset_index(drop=True)

    return requested_passenger, empty_vehicle, current_active_vehicle        


# Main dispatch coordination function
def dispatch_main(requested_passenger, active_vehicle, empty_vehicle, simul_configs, time):
    save_path = simul_configs['save_path']
    
    # Reset indices for clean processing
    requested_passenger = requested_passenger.reset_index(drop=True)
    empty_vehicle = empty_vehicle.reset_index(drop=True)

    # Perform dispatch when both passengers and vehicles are available
    if (len(requested_passenger) > 0) and (len(empty_vehicle) > 0):
        requested_passenger, empty_vehicle, current_active_vehicle = select_dispatch_method(
            requested_passenger, empty_vehicle, simul_configs, time
        )

        # Process matched vehicles and save trip data
        if len(current_active_vehicle) >= 1:
            current_active_vehicle = address_current_active_vehicle(
                current_active_vehicle, time, save_path, simul_configs
            )
            active_vehicle = pd.concat([active_vehicle, current_active_vehicle])
        
    active_vehicle = active_vehicle.reset_index(drop=True)
    return requested_passenger, active_vehicle, empty_vehicle