# This file contains shared configuration constants for the application.

MOTOR_IP = "169.254.0.1"
FREQUENCY_MV_IMPORTANT = 0.3
FREQUENCY_MV_NOT_IMPORTANT = 0.8
ORANGE_PI_URL = 'http://192.168.179.180:8000'

SENSOR_READ_DELAY = 0.5  # Delay in seconds for sensor reading


# This list defines the "public API" of the module.
# It controls what is imported when a user does 'from constants import *'.
__all__ = [
    "MOTOR_IP",
    "FREQUENCY_MV_IMPORTANT",
    "FREQUENCY_MV_NOT_IMPORTANT",
    "ORANGE_PI_URL"
]


 # Base parts of the protocol
base_protocol = "44424450000001000"
read_only = "10000000"
read_write = "30000000"

# Memory type areas
read_only_int32 = "3000000"
read_only_uint32 = "3000000"
read_write_uint8 = "4000000"
read_write_int32 = "7000000"
read_write_uint16 = "5000000"
        
        
        
# Command dictionary
COMMAND_DICT= command_dict = {
            'velocity_mode':  ["44424450000001000-30000000-7000000-4200-01-00000000","44424450000001000-30000000-4000000-4003-01-04", "44424450000001000-30000000-4000000-4000-01-01","44424450000001000-30000000-4000000-4004-01-01",
                                 "44424450000001000-30000000-4000000-6048-01-0BB8","44424450000001000-30000000-4000000-6048-02-0BB8","44424450000001000-30000000-4000000-6048-03-0BB8","44424450000001000-30000000-4000000-6048-04-0BB8",
                             ],
           
            'current_mode':   ["44424450000001000-30000000-4000000-4003-01-02", "44424450000001000-30000000-4000000-4000-01-01",   #special current mode, clear error, enable motor
                               "44424450000001000-30000000-4000000-4004-01-01", "44424450000001000-30000000-7000000-4200-01-0000"], 
                              
            
            'x':              ["44424450000001000-30000000-4000000-4004-01-00"],
            'f':              ["44424450000001000-30000000-7000000-4300-01-00000539"],
            'r':              ["44424450000001000-30000000-7000000-4300-01-FFFFF63C"],
            'init_packet':    ["48494e49000003e80000000113f3bf8a0000006000000000a9fe3f0f0000e5250000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],
            "quick_start":    ["44424450000001000-30000000-4000000-4000-02-0115"],
            "set_position_0":    ["44424450000001000-30000000-7000000-4762-01-00000000"],

            
        }       
        
        
        
    
        
        
        
        
        
        
        
        
        
        