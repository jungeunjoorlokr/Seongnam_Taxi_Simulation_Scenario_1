from modules.preprocess.data_preprocessor import extract_main
from modules.dispatch.dispatch_flow import dispatch_main


# Base configuration template with default values
base_configs = {
    'target_region': None,                # Target simulation region (e.g., '성남 대한민국')
    'problem': 'default',                # Problem type identifier
    'relocation_region': None,           # Relocation region key (e.g., 'seongnam')
    'path': None,                        # Result save path (within simul_result)
    'additional_path': None,             # Scenario-specific additional path
    'time_range': [0, 1440],            # Simulation time range in minutes (0~1440)
    'fail_time': 10,                     # Passenger failure timeout in minutes
    'add_board_time': 0.2,              # Boarding additional time in minutes
    'add_disembark_time': 0.2,          # Alighting additional time in minutes
    'matrix_mode': 'street_distance',    # Distance calculation method
    'dispatch_mode': 'in_order',         # Dispatch algorithm mode
    'eta_model': None,                   # ETA prediction model (None if unavailable)
    'corp_priv_split': (0.55, 0.45),    # Corporate:Private taxi ratio
    'filter_out_of_region': False,       # Filter out-of-region data
    'view_operation_graph': True         # Display operation graph
}


# Select data extraction function based on service type
def extract_selector(service_type):
    return extract_main


# Select dispatch function based on service type  
def dispatch_selector(service_type):
    return dispatch_main