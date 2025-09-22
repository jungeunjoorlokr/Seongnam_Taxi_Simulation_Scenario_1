import numpy as np
import pandas as pd 
from multiprocess import Pool

from modules.routing.osrm_client import osrm_routing_machine
from modules.utils.distance_utils import calculate_straight_distance


# Prepare passenger and vehicle data for cost matrix calculation
def cost_matrix_data_prepare(passenger, vehicle, simul_configs):
    if simul_configs['matrix_mode'] == 'ETA':
        # ETA mode uses full dataframes
        pass
    else:
        # Extract coordinates for distance calculations
        passenger = passenger[['ride_lat', 'ride_lon']].values.tolist()
        vehicle = vehicle[['lat', 'lon']].values.tolist()
    return passenger, vehicle


# Calculate ETA-based cost matrix
def eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs):
    YMD = simul_configs['YMD']
    eta_model = simul_configs['eta_model']
    
    # Extract time features
    target_minute = time % 60
    target_hour = time // 60
    target_weekday = YMD.weekday()
    target_holiday = 1 if target_weekday >= 5 else 0

    # Extract coordinates
    ride_lon = empty_vehicle['lon'].tolist()
    ride_lat = empty_vehicle['lat'].tolist()
    alight_lon = active_passenger['ride_lon'].tolist()
    alight_lat = active_passenger['ride_lat'].tolist()

    # Expand coordinates to match dimensions
    if len(active_passenger) >= len(empty_vehicle):
        alight_lon = np.repeat(alight_lon, len(empty_vehicle)).tolist()
        alight_lat = np.repeat(alight_lat, len(empty_vehicle)).tolist()
        ride_lon = ride_lon * len(active_passenger)
        ride_lat = ride_lat * len(active_passenger)
    else: 
        ride_lon = np.repeat(ride_lon, len(active_passenger)).tolist()
        ride_lat = np.repeat(ride_lat, len(active_passenger)).tolist()
        alight_lon = alight_lon * len(empty_vehicle)
        alight_lat = alight_lat * len(empty_vehicle)

    # Create ETA input dataframe
    eta_inputData_for_cost_matrix = pd.DataFrame({
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
    for target_col in ['minute', 'hour', 'weekday', 'holiday']:
        eta_inputData_for_cost_matrix[target_col] = eta_inputData_for_cost_matrix[target_col].astype('category')
    
    # Calculate distances
    eta_inputData_for_cost_matrix['straight_distance'] = calculate_straight_distance(
        eta_inputData_for_cost_matrix['ride_lat'].values, 
        eta_inputData_for_cost_matrix['ride_lon'].values,
        eta_inputData_for_cost_matrix['alight_lat'].values,
        eta_inputData_for_cost_matrix['alight_lon'].values
    )
    
    # Get OSRM distances
    osrm_rs = [
        osrm_routing_machine([row['ride_lat'], row['ride_lon'], 
                            row['alight_lat'], row['alight_lon']])
        for _, row in eta_inputData_for_cost_matrix.iterrows()
    ]
    
    eta_inputData_for_cost_matrix['osrm_distance'] = [
        rs['distance'] / 1000 if rs is not None else 0.5 
        for rs in osrm_rs
    ]
    
    # Select features for prediction
    eta_inputData_for_cost_matrix = eta_inputData_for_cost_matrix[[
        'weekday', 'holiday', 'hour', 'minute', 'straight_distance', 'osrm_distance'
    ]]

    # Predict and reshape cost matrix
    eta_model_cost_matrix = eta_model.predict(eta_inputData_for_cost_matrix)
    shape_list = [len(empty_vehicle), len(active_passenger)]
    eta_model_cost_matrix = eta_model_cost_matrix.reshape(max(shape_list), min(shape_list))

    return eta_model_cost_matrix


# Calculate dispatch cost matrix based on configuration
def dispatch_cost_matrix(active_passenger, empty_vehicle, time, simul_configs):
    
    # Helper function for haversine distance matrix
    def haversine_distance_cost_matrix(A, B):
        costs = []
        for a in A:
            cost = list(map(lambda data: calculate_straight_distance(
                data[0], data[1], a[0], a[1]
            ).tolist(), B))
            costs.append(cost)
        return np.array(costs)
        
    matrix_mode = simul_configs['matrix_mode']
    dispatch_mode = simul_configs['dispatch_mode']
    
    # Prepare data
    active_passenger, empty_vehicle = cost_matrix_data_prepare(
        active_passenger, empty_vehicle, simul_configs
    )

    # Optimization mode - handles multiple passengers and vehicles
    if dispatch_mode == 'optimization':
        
        if matrix_mode == 'haversine_distance':
            # Larger set goes first for optimization
            if len(active_passenger) >= len(empty_vehicle):
                cost_matrix = haversine_distance_cost_matrix(active_passenger, empty_vehicle)
            else:
                cost_matrix = haversine_distance_cost_matrix(empty_vehicle, active_passenger)
        
        elif matrix_mode == 'street_distance':
            # Create all possible combinations
            if len(active_passenger) >= len(empty_vehicle):
                costs = np.array([[a + b for b in empty_vehicle] for a in active_passenger])
            else:
                costs = np.array([[a + b for b in active_passenger] for a in empty_vehicle])
            
            costs_shape = costs.shape
            costs = costs.reshape(costs_shape[0] * costs_shape[1], costs_shape[2])
            
            # Sequential processing (Pool removed)
            cost_matrix = [osrm_routing_machine(cost)['distance'] for cost in costs]
            
            cost_matrix = np.array(cost_matrix).reshape(costs_shape[0], costs_shape[1])
            cost_matrix = cost_matrix / 1000  # Convert to km
            
        elif matrix_mode == 'ETA':
            cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
            
        else:
            raise ValueError('matrix_mode is not defined')
        
    # In-order mode - handles one passenger at a time
    elif dispatch_mode == 'in_order':
        
        if matrix_mode == 'haversine_distance':
            active_passenger = active_passenger[0]
            costs = np.array([active_passenger + vehicle for vehicle in empty_vehicle])
            cost_matrix = calculate_straight_distance(
                costs[:, 0], costs[:, 1], costs[:, 2], costs[:, 3]
            )
            
        elif matrix_mode == 'street_distance':
            active_passenger = active_passenger[0]
            costs = [active_passenger + vehicle for vehicle in empty_vehicle]
            
            # Sequential processing (Pool removed)
            cost_matrix = [osrm_routing_machine(cost)['distance'] for cost in costs]
            cost_matrix = np.array(cost_matrix) / 1000  # Convert to km
            
        elif matrix_mode == 'ETA':
            cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
            cost_matrix = cost_matrix.reshape(-1)
            
    return cost_matrix