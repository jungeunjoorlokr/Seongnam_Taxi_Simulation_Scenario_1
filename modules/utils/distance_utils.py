import numpy as np
import geopandas as gpd
import osmnx as ox
from difflib import get_close_matches
from shapely.ops import unary_union


# Find similar words from candidate list
def select_similar_word(word_to_compare, candidates):
    n = 1  # Maximum number of matches
    cutoff = 0.6  # Similarity threshold
    
    close_matches = get_close_matches(word_to_compare, candidates, n, cutoff)
    return close_matches


# Calculate haversine distance between coordinates (returns km)
def calculate_straight_distance(lat1, lon1, lat2, lon2):
    km_constant = 3959 * 1.609344
    lat1, lon1, lat2, lon2 = map(np.deg2rad, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1 
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a)) 
    km = km_constant * c
    return km


# Calculate total distance for routes (returns km)
def calculate_route_distance(data):
    distance = []

    for tr in data: 
        route = np.hstack([np.array(tr)[:-1], np.array(tr)[1:]])
        dis = sum(calculate_straight_distance(route[:,0], route[:,1], route[:,2], route[:,3]))
        distance.append(dis)
    
    return distance 


# Convert meters to euclidean distance in lat/lon coordinates
def calculate_euclidean_distance(meter):
    # Calculate euclidean distance between point pairs
    dis_1 = ox.distance.euclidean_dist_vec(36.367658, 127.447499, 36.443928, 127.419678)
    # Calculate great circle distance
    dis_2 = ox.distance.great_circle_vec(36.367658, 127.447499, 36.443928, 127.419678)

    return dis_1/dis_2 * meter


# Filter vehicles outside region boundary
def filter_outside_region(vehicles, region_key):
    boundary_path = f"data/etc/{region_key}_boundary.geojson"
    region = gpd.read_file(boundary_path)
    union_poly = unary_union(region.geometry.values)

    gdf = gpd.GeoDataFrame(
        vehicles,
        geometry=gpd.points_from_xy(vehicles['lon'], vehicles['lat']),
        crs="EPSG:4326"
    )
    gdf = gdf[gdf.within(union_poly)]
    return gdf.drop(columns='geometry')