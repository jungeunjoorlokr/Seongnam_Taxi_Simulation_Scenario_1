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