import numpy as np
import pandas as pd
import itertools
from itertools import repeat
from ortools.linear_solver import pywraplp

from .cost_matrix import dispatch_cost_matrix


# Optimization-based dispatch using OR-Tools
def ortools_dispatch(active_passenger, empty_vehicle, cost_matrix):
    
    # Assign larger set as A, smaller as B for optimization
    if len(active_passenger) >= len(empty_vehicle):
        A = active_passenger
        B = empty_vehicle
    else: 
        A = empty_vehicle
        B = active_passenger

    A_cnt = len(A)
    B_cnt = len(B)
    
    # Create MIP solver with SCIP backend
    solver = pywraplp.Solver.CreateSolver('SCIP')

    # Generate index arrays for optimization variables
    A_idx = sorted(list(itertools.chain(*list(repeat(list(range(A_cnt)), B_cnt)))))
    B_idx = list(itertools.chain(*list(repeat(list(range(B_cnt)), A_cnt))))

    # Create binary decision variables x[i, j]
    x = {}
    for t, p in zip(A_idx, B_idx):
        x[t, p] = solver.IntVar(0, 1, '')

    # Constraint: Each worker assigned to at most 1 task
    for i in range(A_cnt):
        solver.Add(solver.Sum([x[i, j] for j in range(B_cnt)]) <= 1)

    # Constraint: Each task assigned to exactly one worker
    for j in range(B_cnt):
        solver.Add(solver.Sum([x[i, j] for i in range(A_cnt)]) == 1)
    
    # Create objective function (minimize total cost)
    objective_terms = []
    for i in range(A_cnt):
        for j in range(B_cnt):
            objective_terms.append(cost_matrix[i][j] * x[i, j])

    solver.Minimize(solver.Sum(objective_terms))
    
    # Solve optimization problem
    status = solver.Solve()
    
    # Extract solution
    A_iloc = []
    B_iloc = []

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        for i in range(A_cnt):
            for j in range(B_cnt):
                if x[i, j].solution_value() > 0.5:
                    A_iloc.append(i) 
                    B_iloc.append(j)
    
    # Calculate matched distances
    iloc_distance = [cost_matrix[iloc_1, iloc_2] for iloc_1, iloc_2 in zip(A_iloc, B_iloc)]
    
    # Return results in correct order
    if len(active_passenger) >= len(empty_vehicle):
        dispatch_inf = {'vehicle': B_iloc, 'passenger': A_iloc, 'distance': iloc_distance}
    else:
        dispatch_inf = {'vehicle': A_iloc, 'passenger': B_iloc, 'distance': iloc_distance}    
    
    return dispatch_inf


# Sequential first-come-first-served dispatch
def in_order_dispatch(active_ps, empty_vh, time, simul_configs):
    
    active_passengers = active_ps.copy()
    empty_vehicles = empty_vh.copy()

    vehicle_iloc = []
    passenger_iloc = []
    iloc_distance = []

    # Process passengers in order
    for idx, row in active_passengers.iterrows():
        if len(empty_vehicles) != 0:
            # Prepare single passenger data
            P_geo = pd.DataFrame(row).T.reset_index(drop=True)
            V_geo = empty_vehicles
            
            # Calculate cost matrix for current passenger
            cost_matrix = dispatch_cost_matrix(P_geo, V_geo, time, simul_configs)
            
            # Find closest vehicle
            cost_min_idx = np.argmin(cost_matrix)
            vehicle_idx = empty_vehicles.iloc[[cost_min_idx]].index[0]
            
            match_distance = cost_matrix[cost_min_idx]

            # Remove matched vehicle from available pool
            empty_vehicles = empty_vehicles.loc[(empty_vehicles.index != vehicle_idx)]
            
            # Record match
            vehicle_iloc.append(vehicle_idx)
            passenger_iloc.append(idx)
            iloc_distance.append(match_distance) 
        else:
            break
        
    dispatch_inf = {'vehicle': vehicle_iloc, 'passenger': passenger_iloc, 'distance': iloc_distance} 
    
    return dispatch_inf