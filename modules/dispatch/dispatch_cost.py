from modules.routing.osrm_routing import osrm_routing_machine
from modules.utils.utils import calculate_straight_distance
import numpy as np
import pandas as pd 

########
# TAXI #
########
def cost_matrix_data_prepare(passenger, vehicle, simul_configs):
    """비용 행렬 계산을 위한 입력 데이터 전처리.

    - ETA 모드가 아닌 경우에만, 필요한 좌표 컬럼만 추출하여 리스트로 변환한다.
    - 반환 형식은 downstream 로직과 동일하게 유지한다.
    """
    if simul_configs['matrix_mode'] == 'ETA':
        # ETA 모드에서는 원본 DataFrame 형태를 유지한다
        pass
    else:
        passenger = passenger[['ride_lat', 'ride_lon']].values.tolist()
        vehicle = vehicle[['lat', 'lon']].values.tolist()

    return passenger, vehicle

### metro일때랑 seuol일때랑 eta 모델의 input data가 다름
def eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs):
    """ETA 모델을 이용해 비용 행렬(예상 소요시간/거리 등)을 계산한다.

    입력 데이터는 승객-차량 모든 조합에 대해 구성되며, 필요한 파생 변수
    (직선거리, OSRM 기반 도로거리)까지 포함하여 모델 입력 프레임을 생성한다.
    반환 형태는 (max(|V|, |P|), min(|V|, |P|))의 2차원 배열로 유지한다.
    """
    # if simul_configs['dispatch_mode'] == 'in_order':
    #     active_passenger = pd.DataFrame(active_passenger).T

    YMD = simul_configs['YMD']
    eta_model = simul_configs['eta_model']

    # 숫자형 시간 변수 생성
    target_minute = time % 60
    target_hour = time // 60
    target_weekday = YMD.weekday()
    target_holiday = 1 if target_weekday >= 5 else 0

    # 좌표 추출 (DataFrame → list)
    ride_lon = empty_vehicle['lon'].tolist()
    ride_lat = empty_vehicle['lat'].tolist()
    alight_lon = active_passenger['ride_lon'].tolist()
    alight_lat = active_passenger['ride_lat'].tolist()

    # 모든 조합을 만들기 위한 길이 보정
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

    # 모델 입력 프레임 생성
    eta_inputData_for_cost_matrix = pd.DataFrame({
        'minute': target_minute,
        'hour': target_hour,
        'weekday': target_weekday,
        'holiday': target_holiday,
        'ride_lat': ride_lat,
        'ride_lon': ride_lon,
        'alight_lat': alight_lat,
        'alight_lon': alight_lon,
    })

    # 범주형 캐스팅
    for target_col in ['minute', 'hour', 'weekday', 'holiday']:
        eta_inputData_for_cost_matrix[target_col] = eta_inputData_for_cost_matrix[target_col].astype('category')

    # 파생 변수: 직선거리, OSRM 도로거리(km)
    eta_inputData_for_cost_matrix['straight_distance'] = \
        calculate_straight_distance(
            eta_inputData_for_cost_matrix['ride_lat'].values,
            eta_inputData_for_cost_matrix['ride_lon'].values,
            eta_inputData_for_cost_matrix['alight_lat'].values,
            eta_inputData_for_cost_matrix['alight_lon'].values,
        )
    osrm_rs = [
        osrm_routing_machine([row['ride_lat'], row['ride_lon'], row['alight_lat'], row['alight_lon']])
        for _, row in eta_inputData_for_cost_matrix.iterrows()
    ]
    eta_inputData_for_cost_matrix['osrm_distance'] = [
        rs['distance'] / 1000 if rs != None else 0.5 for rs in osrm_rs
    ]
    eta_inputData_for_cost_matrix = eta_inputData_for_cost_matrix[
        ['weekday', 'holiday', 'hour', 'minute', 'straight_distance', 'osrm_distance']
    ]

    # 예측 수행 → 비용 행렬
    eta_model_cost_matrix = eta_model.predict(eta_inputData_for_cost_matrix)

    shape_list = [len(empty_vehicle), len(active_passenger)]
    eta_model_cost_matrix = eta_model_cost_matrix.reshape(max(shape_list), min(shape_list))

    return eta_model_cost_matrix


# def dispatch_cost_matrix(active_passenger, empty_vehicle, time, simul_configs):
    
#     def haversine_distance_cost_matrix(A, B):
#         costs = []
        
#         for a in A:
#             cost = list(map(lambda data: calculate_straight_distance(data[0], data[1], a[0], a[1]).tolist(), B))
#             costs.append(cost)
            
#         return np.array(costs)
        
#     matrix_mode = simul_configs['matrix_mode']
#     dispatch_mode = simul_configs['dispatch_mode']
    
    
#     active_passenger, empty_vehicle = cost_matrix_data_prepare(active_passenger, empty_vehicle, simul_configs)

#     # (optimization은 수가 큰 것을 항상 처음에 넣어 준다)
#     if dispatch_mode == 'optimization':
#         # 직선 길이
#         if matrix_mode == 'haversine_distance':    
#             if len(active_passenger) >= len(empty_vehicle):
#                 cost_matrix = haversine_distance_cost_matrix(active_passenger, empty_vehicle)
#             else:
#                 cost_matrix = haversine_distance_cost_matrix(empty_vehicle, active_passenger)
        
#         # 도로 길이
#         elif matrix_mode == 'street_distance':
#             if len(active_passenger) >= len(empty_vehicle):
#                 costs = np.array([[a + b for b in  empty_vehicle] for a in active_passenger])
#             else:
#                 costs = np.array([[a + b for b in  active_passenger] for a in empty_vehicle])
            
#             costs_shape = costs.shape
#             costs = costs.reshape(costs_shape[0] * costs_shape[1], costs_shape[2])
#             if len(costs) >= 60:
#                 p = Pool(processes=5)
#                 result = p.map(osrm_routing_machine, costs)
#                 cost_matrix = [i['distance'] if i is not None and 'distance' in i else 5000 for i in result]  # fallback: 5km
#                 del p
#             else:
#                 cost_matrix = []
#                 for cost in costs:
#                     result = osrm_routing_machine(cost)
#                     if result is not None and 'distance' in result:
#                         cost_matrix.append(result['distance'])
#                     else:
#                         cost_matrix.append(5000)  # fallback: 5km
            
#             cost_matrix = np.array(cost_matrix).reshape(costs_shape[0], costs_shape[1])
#             cost_matrix = np.array(cost_matrix)/1000
#         elif matrix_mode == 'ETA':
#             cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
#         else:
#             assert False, 'matrix_mode is not defined'
        
#     ### 데이터 순서대로
#     elif dispatch_mode == 'in_order':
#         # 직선 길이
#         if matrix_mode == 'haversine_distance': 
#             active_passenger = active_passenger[0] 
#             costs = np.array([active_passenger +  vehicle for vehicle in empty_vehicle])
#             cost_matrix = calculate_straight_distance(costs[:,0], costs[:,1], costs[:,2], costs[:,3])
            
#         # 도로 길이
#         elif matrix_mode == 'street_distance': 
#             active_passenger = active_passenger[0] 
#             costs = [active_passenger + vehicle for vehicle in empty_vehicle]
#             if len(costs) >= 60:
#                 p = Pool(processes=5)
#                 cost_matrix = p.map(osrm_routing_machine, costs)
#                 cost_matrix = [i['distance'] for i in cost_matrix]
                
#                 del p
#             else:
#                 cost_matrix = [osrm_routing_machine(cost)['distance'] for cost in costs]
                
#             cost_matrix = np.array(cost_matrix)/1000
#         elif matrix_mode == 'ETA':
#             cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
#             cost_matrix = cost_matrix.reshape(-1)
            
#     return cost_matrix

def dispatch_cost_matrix(active_passenger, empty_vehicle, time, simul_configs):
    """디스패치 비용 행렬 생성.

    - matrix_mode: 'haversine_distance' | 'street_distance' | 'ETA'
    - dispatch_mode: 'optimization' | 'in_order'
    - 반환: numpy.ndarray 또는 1차원 numpy.ndarray (in_order + haversine/street)
    """

    def haversine_distance_cost_matrix(A, B):
        """좌표 리스트 A, B에 대해 해버사인(직선) 거리 행렬을 계산한다.

        A, B: [[lat, lon], ...] 형식
        반환: (len(A), len(B))의 numpy.ndarray
        """
        costs = []
        for a in A:
            cost = list(map(lambda data: calculate_straight_distance(data[0], data[1], a[0], a[1]).tolist(), B))
            costs.append(cost)
        return np.array(costs)

    def _compute_osrm_distances_m(costs):
        """OSRM으로부터 거리(m)를 리스트로 받아온다. 각 cost는 [lat1, lon1, lat2, lon2]."""
        return [osrm_routing_machine(cost)['distance'] for cost in costs]
        
    matrix_mode = simul_configs['matrix_mode']
    dispatch_mode = simul_configs['dispatch_mode']
    
    active_passenger, empty_vehicle = cost_matrix_data_prepare(active_passenger, empty_vehicle, simul_configs)

    # (optimization은 수가 큰 것을 항상 처음에 넣어 준다)
    if dispatch_mode == 'optimization':
        # 직선 길이
        if matrix_mode == 'haversine_distance':    
            if len(active_passenger) >= len(empty_vehicle):
                cost_matrix = haversine_distance_cost_matrix(active_passenger, empty_vehicle)
            else:
                cost_matrix = haversine_distance_cost_matrix(empty_vehicle, active_passenger)
        
        # 도로 길이
        elif matrix_mode == 'street_distance':
            if len(active_passenger) >= len(empty_vehicle):
                costs = np.array([[a + b for b in empty_vehicle] for a in active_passenger])
            else:
                costs = np.array([[a + b for b in active_passenger] for a in empty_vehicle])
            
            costs_shape = costs.shape
            costs = costs.reshape(costs_shape[0] * costs_shape[1], costs_shape[2])

            # OSRM 거리(m) 계산 → 원래 shape 복원 후 km 변환
            cost_matrix = _compute_osrm_distances_m(costs)
            cost_matrix = np.array(cost_matrix).reshape(costs_shape[0], costs_shape[1])
            cost_matrix = np.array(cost_matrix)/1000
            
        elif matrix_mode == 'ETA':
            cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
        else:
            assert False, 'matrix_mode is not defined'
        
    ### 데이터 순서대로
    elif dispatch_mode == 'in_order':
        # 직선 길이
        if matrix_mode == 'haversine_distance': 
            active_passenger = active_passenger[0] 
            costs = np.array([active_passenger + vehicle for vehicle in empty_vehicle])
            cost_matrix = calculate_straight_distance(costs[:,0], costs[:,1], costs[:,2], costs[:,3])
            
        # 도로 길이
        elif matrix_mode == 'street_distance': 
            active_passenger = active_passenger[0] 
            costs = [active_passenger + vehicle for vehicle in empty_vehicle]
            # OSRM 거리(m) 계산 후 km 변환
            cost_matrix = _compute_osrm_distances_m(costs)
            cost_matrix = np.array(cost_matrix)/1000
            
        elif matrix_mode == 'ETA':
            cost_matrix = eta_cost_matrix(active_passenger, empty_vehicle, time, simul_configs)
            cost_matrix = cost_matrix.reshape(-1)
            
    return cost_matrix