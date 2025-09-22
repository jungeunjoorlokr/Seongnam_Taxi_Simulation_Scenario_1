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



#####################
# Extract Passenger #
#####################
# - 특징은 승객 휠체어 이용 여부를 알 수 없기 때문에 비율 고려하여, 승객 타입 부여
# - columns : ['ID', 'ride_time', 'ride_geometry', 'alight_geometry', 'dispatch_time', 'type']
# def extract_passenger(operation_record, simulation_inf):
    
#     # 승객 수 변화 없음
#     if not('passenger_increase_ratio' in simulation_inf.keys()):
#         # taxi_operation_record로 승객 데이터 추출
#         passenger = operation_record[['ride_time', 'ride_lat', 'ride_lon', 'alight_lat', 'alight_lon']]

#         # 승객 ID 생성
#         passenger = passenger.reset_index(drop=False)
#         passenger = passenger.rename(columns={'index': 'ID'})

#         # 승객 dispatch_time 생성
#         passenger['dispatch_time'] = 0 # dispatch_time이란 taxi를 잡기 전 까지 걸리는 시간!

#         # # 고객 type 부여 (0 : 휠체어 미이용, 1 : 휠체어 이용)
#         # type_list = np.random.choice(2 ,size = len(passenger), p=[0.23, 0.77]) ## 0(휠체어X): 23%, 1(휠체어O) : 77%
#         # passenger["type"] = type_list
        
#         return passenger
#     # 승객 수 (증가 / 감소)
#     else:
#         passenger = operation_record[['ride_time', 'ride_lat', 'ride_lon', 'alight_lat', 'alight_lon']]
        
#         passenger_increase_ratio = simulation_inf['passenger_increase_ratio']
        
#         if  passenger_increase_ratio <= 1:        
#             passenger = passenger.sample(frac=passenger_increase_ratio).sort_values('ride_time').reset_index(drop=True).reset_index()
#             passenger = passenger.rename(columns={'index': 'ID'})
            
#             type_list = np.random.choice(2 ,size = len(passenger), p=[0.23, 0.77]) # 0(휠체어X): 23%, 1(휠체어O) : 77%
#             passenger["type"] = type_list
#         else:
#             add_passenger = passenger.sample(frac=passenger_increase_ratio-1).copy()
#             add_passenger = add_passenger.reset_index(drop=True)
            
#             # # 장소 기반 포인트 생성
#             # point_generator = point_generator_with_OSM()
#             # add_passenger_point = point_generator.point_generator_about_placeName(place=simulation_inf['target_region'], count=len(add_passenger) * 2)
            
#             ride_point = add_passenger_point[:len(add_passenger)].reset_index(drop=True)
#             alight_point = add_passenger_point[len(add_passenger):].reset_index(drop=True)
            
#             add_passenger[['ride_lat', 'ride_lon']] = ride_point[['lat', 'lon']] 
#             add_passenger[['alight_lat', 'alight_lon']] = alight_point[['lat', 'lon']]           
            
#             passenger = pd.concat([passenger, add_passenger]).sort_values('ride_time').reset_index(drop=True).reset_index()
#             passenger = passenger.rename(columns={'index': 'ID'})
            
#             type_list = np.random.choice(2 ,size = len(passenger), p=[0.23, 0.77]) # 0(휠체어X): 23%, 1(휠체어O) : 77%
#             passenger["type"] = type_list
        
#         # 승객 dispatch_time 생성
#         passenger['dispatch_time'] = 0 # dispatch_time이란 taxi를 잡기 전 까지 걸리는 시간!
        
#         '''여기부터 수정'''
#         # passenger column 순서 정렬
#         passenger = passenger[['ID', 'ride_time', 'ride_lat', 'ride_lon', 'alight_lat', 'alight_lon', 'dispatch_time']]
    
#         return passenger


# ################
# # Extract Taxi #
# ################
# # -'vehicle_id 별 최소 탑승 시간과 최대 하차 시간으로 taxi_schedule을 생성한다.
# # - 주간근무자 17시 이전 근무자 9시간 근무
# # - 야간근무자 17시 이후 근무자 12시간 근무 
# def extract_taxi(operation_record, simulation_inf):
    
#     if not('taxi_schedule' in simulation_inf.keys()):
        
#         taxi_schedule_dict = dict()

#         for id, row in operation_record.groupby('vehicle_id'):
#             taxi_schedule_dict[id] = [row['cartype'].iloc[0], row['ride_time'].min(), row['ride_time'].max()]

#         taxi_schedule = pd.DataFrame(taxi_schedule_dict).T.reset_index()
#         taxi_schedule.columns = ['vehicle_id', 'cartype', 'work_start', 'work_end']

#         taxi_schedule['temporary_stopTime'] = 0 

#         ## taxi 운행표 생성
#         bins = [i*60 for i in range(6,31)]
#         labels = [i for i in range(6,30)]

#         work_startTime = pd.cut(taxi_schedule['work_start'], bins=bins, labels=labels, right=False)
#         taxi_schedule['work_start'] = work_startTime.tolist()

#         ## 주간, 야간 근무자의 근무 시간이 다르기 때문에 근무 시간 아래와 같이 차별 부여 
#         # - A조(주간근무자) 17시 이전 근무자 9시간 근무 : 06:00~17:00시
#         # - B조(야간근무자) 17시 이후 근무자 12시간 근무 : 이외 시간
#         A_group_timeTable = list(range(6,17))

#         A_taxi_schedule = taxi_schedule.loc[(taxi_schedule['work_start'].isin(A_group_timeTable))]
#         B_taxi_schedule = taxi_schedule.loc[~(taxi_schedule['work_start'].isin(A_group_timeTable))]

#         A_taxi_schedule['work_end'] = A_taxi_schedule['work_start'] + 9
#         B_taxi_schedule['work_end'] = B_taxi_schedule['work_start'] + 12

#         taxi_schedule = pd.concat([A_taxi_schedule, B_taxi_schedule]).reset_index(drop=True)

#         ## 시뮬레이션 시간 상 6~30시이기 때문에 30시 이후 운행 차량 데이터 조정 
#         # - 예) 17시~31시 근무 차량 => 0~1시, 17~30시 근무로 변경
#         taxi_inMorning = taxi_schedule.loc[(taxi_schedule['work_end'] <= 30)]
#         taxi_inNight = taxi_schedule.loc[(taxi_schedule['work_end'] > 30)]

#         over_time = taxi_inNight['work_end'] - 30
#         taxi_inNight['work_end'] = 30

#         taxi_inNight_copy = copy.deepcopy(taxi_inNight)
#         taxi_inNight_copy['work_start'] = 0 
#         taxi_inNight_copy['work_end'] = over_time

#         taxi_inNight = pd.concat([taxi_inNight, taxi_inNight_copy])

#         taxi_schedule = pd.concat([taxi_inMorning, taxi_inNight]).sort_values('work_start').reset_index(drop=True)

#         taxi_schedule['work_start'] = taxi_schedule['work_start'] * 60
#         taxi_schedule['work_end'] = taxi_schedule['work_end'] * 60


#         point_generator = point_generator_with_OSM()
#         taxi_point = point_generator.point_generator_about_placeName(place=simulation_inf['target_region'], count=len(taxi_schedule))
#         taxi_schedule['lat'] = taxi_point['lat']
#         taxi_schedule['lon'] = taxi_point['lon']
        
#         return taxi_schedule
#     else:
#         ## 사용자가 생성한 시뮬레이션 데이터 사용
#         taxi_schedule = simulation_inf['taxi_schedule']
        
#         taxi_schedule['temporary_stopTime'] = 0

#         point_generator = point_generator_with_OSM()
#         taxi_point = point_generator.point_generator_about_placeName(place=simulation_inf['target_region'], count=len(taxi_schedule))
#         taxi_schedule['lat'] = taxi_point['lat']
#         taxi_schedule['lon'] = taxi_point['lon']        
        
#         ## 시뮬레이션 시간 상 6~30시이기 때문에 30시 이후 운행 차량 데이터 조정 
#         # - 예) 17시~31시 근무 차량 => 0~1시, 17~30시 근무로 변경
#         taxi_inMorning = taxi_schedule.loc[(taxi_schedule['work_end'] <= 30)]
#         taxi_inNight = taxi_schedule.loc[(taxi_schedule['work_end'] > 30)]

#         over_time = taxi_inNight['work_end'] - 30
#         taxi_inNight['work_end'] = 30

#         taxi_inNight_copy = copy.deepcopy(taxi_inNight)
#         taxi_inNight_copy['work_start'] = 0 
#         taxi_inNight_copy['work_end'] = over_time

#         taxi_inNight = pd.concat([taxi_inNight, taxi_inNight_copy])

#         taxi_schedule = pd.concat([taxi_inMorning, taxi_inNight]).sort_values('work_start').reset_index(drop=True)

#         taxi_schedule['work_start'] = taxi_schedule['work_start'] * 60
#         taxi_schedule['work_end'] = taxi_schedule['work_end'] * 60
    
#         return taxi_schedule