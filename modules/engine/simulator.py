import pandas as pd 
from tqdm import tqdm

from .config_manager import extract_selector, dispatch_selector, base_configs
from .state_updater import update_passenger, update_vehicle
from .io_manager import generate_path_to_save, save_json_data, checking_progress
from ..preprocess.data_preprocessor import crop_data_by_timerange, get_preprocessed_data


# Initialize simulation base dataframes
def base_data():
    active_vehicle = pd.DataFrame()
    empty_vehicle = pd.DataFrame()
    requested_passenger = pd.DataFrame()
    fail_passenger = pd.DataFrame()
    
    simulation_record = pd.DataFrame(
                                columns=[
                                    'time',
                                    'waiting_passenger_cnt',
                                    'fail_passenger_cnt', 
                                    'empty_vehicle_cnt',
                                    'driving_vehicle_cnt', 
                                    'iter_time(second)'
                                ]
                            )
    
    return active_vehicle, empty_vehicle, requested_passenger, fail_passenger, simulation_record


class Simulator:
    
    def __init__(self, raw_data=None, passengers=None, vehicles=None, configs=None):
        # Validate configuration
        self.configs = configs    
        if self.configs is None:
            raise ValueError("Please input the configs data")

        # Set problem-specific handlers
        self.extract_main = extract_selector(self.configs["problem"])
        self.dispatch_main = dispatch_selector(self.configs["problem"])

        # Generate save path
        path_to_save_data = generate_path_to_save(
            self.configs['path'], 
            self.configs['additional_path']
        )
        self.configs['save_path'] = path_to_save_data

        # Store input data
        self.raw_data = raw_data
        self.passengers = passengers
        self.vehicles = vehicles

        # Process raw data if provided, otherwise use default timestamp
        if self.raw_data is not None:            
            self.passengers, self.vehicles, YMD = self.extract_main(self.raw_data, self.configs)
            self.configs['YMD'] = YMD
        else:
            self.configs['YMD'] = pd.Timestamp('2019-04-09 00:00:00')
        
        # Crop data to simulation time range
        self.passengers, self.vehicles = crop_data_by_timerange(
            self.passengers, self.vehicles, self.configs
        )
            
        # Initialize simulation state variables
        (self.active_vehicle, self.empty_vehicle, self.requested_passenger, 
         self.fail_passenger, self.simulation_record) = base_data()
    
    # Main simulation execution
    def run(self):
        start_time, end_time = self.configs['time_range'][0], self.configs['time_range'][1]
        print(f"[Data]  passengers={len(self.passengers)} load completed")
        
        with tqdm(total=end_time-start_time, 
                  desc="시뮬레이션", 
                  unit="분",
                  ncols=80) as pbar:

            for time in range(start_time, end_time):
                # Update passenger status (new requests, failures)
                self.requested_passenger, self.fail_passenger, self.passengers = update_passenger(
                    self.requested_passenger, 
                    self.fail_passenger,  
                    self.passengers, 
                    self.configs,
                    time
                )
                
                # Update vehicle status (active to empty transitions)
                self.active_vehicle, self.empty_vehicle, self.vehicles = update_vehicle(
                    self.active_vehicle,
                    self.empty_vehicle, 
                    self.vehicles,
                    self.configs,
                    time
                )
                
                # Execute dispatch when both requests and vehicles available
                if (len(self.requested_passenger) > 0) and (len(self.empty_vehicle) > 0):
                    self.requested_passenger, self.active_vehicle, self.empty_vehicle = self.dispatch_main(
                        self.requested_passenger, 
                        self.active_vehicle, 
                        self.empty_vehicle, 
                        self.configs, 
                        time
                    )

                # Record current simulation state
                self.simulation_record = checking_progress(
                    self.simulation_record, time, self.requested_passenger, 
                    self.fail_passenger, self.empty_vehicle, self.active_vehicle, 
                    self.configs
                )

                pbar.update(1)