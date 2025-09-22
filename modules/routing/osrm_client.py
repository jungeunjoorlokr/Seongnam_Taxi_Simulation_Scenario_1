import numpy as np
import itertools
import requests
import polyline
import warnings 
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from modules.utils.distance_utils import calculate_straight_distance

warnings.filterwarnings('ignore')

# Main OSRM routing function
def osrm_routing_machine(OD_coords):
    osrm_base, status = get_res(OD_coords)
    
    if status == 'defined':
        duration, distance = extract_duration_distance(osrm_base)
        route = extract_route(osrm_base)
        timestamp = extract_timestamp(route, duration)
        
        result = {'route': route, 'timestamp': timestamp, 'duration': duration, 'distance': distance}
        
        # Handle edge case with NaN timestamp
        if np.isnan(result['timestamp'][-1]):
            result['timestamp'][-1] = 0.01
            result['duration'] = 0.01
            
        return result
    else: 
        return None

        
# Get routing response from OSRM server
def get_res(point):
    status = 'defined'

    # Setup session with retry strategy
    session = requests.Session()
    retry = Retry(connect=10, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Build OSRM request URL
    overview = '?overview=full'
    loc = f"{point[1]},{point[0]};{point[3]},{point[2]}"  # lon,lat;lon,lat format
    url = "http://127.0.0.1:8000/route/v1/driving/"
    
    r = session.get(url + loc + overview) 
    
    # Handle failed requests with fallback calculation
    if r.status_code != 200:
        status = 'undefined'
        
        # Calculate straight-line distance as fallback
        distance = calculate_straight_distance(point[0], point[1], point[2], point[3]) * 1000
        
        # Create simple route with origin and destination
        route = [[point[1], point[0]], [point[3], point[2]]]

        # Estimate duration based on average speed
        speed_km = 30  # km/h for general taxi
        speed = (speed_km * 1000 / 60)  # m/min      
        duration = distance / speed
        
        timestamp = [0, duration]
        result = {'route': route, 'timestamp': timestamp, 'duration': duration, 'distance': distance}
        
        return result, status
    
    res = r.json()   
    return res, status


# Extract duration and distance from OSRM response
def extract_duration_distance(res):
    duration = res['routes'][0]['duration'] / 60  # Convert to minutes
    distance = res['routes'][0]['distance']
    return duration, distance


# Extract route coordinates from OSRM response
def extract_route(res):
    route = polyline.decode(res['routes'][0]['geometry'])
    route = list(map(lambda data: [data[1], data[0]], route))  # Convert to [lon, lat] format
    return route


# Calculate timestamp for each route point based on distance
def extract_timestamp(route, duration):
    rt = np.array(route)
    rt = np.hstack([rt[:-1, :], rt[1:, :]])

    # Calculate distance proportions between consecutive points
    per = calculate_straight_distance(rt[:, 1], rt[:, 0], rt[:, 3], rt[:, 2])
    per = per / np.sum(per)

    # Distribute total duration proportionally
    timestamp = per * duration
    timestamp = np.hstack([np.array([0]), timestamp])
    timestamp = list(itertools.accumulate(timestamp)) 
    
    return timestamp
 

