import os
import serial

from sdk.dynamixel_lib.dynamixel_sdk_wrapper import *  # Uses Dynamixel SDK library
from sdk.mightyzap_lib.mightyzap_sdk_wrapper import *  # Uses Mightyzap SDK library

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정

class NanaArmWrapper:
    
    def __init__(self, serial_port, baudrate, dxl_models, mighty_models):
        
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = 0.1
        
        self.dxl_models = dxl_models
        self.mighty_models = mighty_models

        self.serial_handler = None

        try:
            self.serial_handler = serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1)
            print(f"[Info] Serial connection established on {self.serial_port} at {self.baudrate} baud.")
        
        except serial.SerialException as e:
            print(f"[Error] Failed to establish serial connection: {e}")
            raise e
        
        self.mightyzap_sdk_handler = MightyZapSDKWrapper(self.serial_handler, self.mighty_models)
        self.dynamixel_sdk_handler = DynamixelSDKWrapper(self.serial_handler, self.dxl_models)

    def __close__(self):
        
        if self.serial_handler and self.serial_handler.is_open:
            self.serial_handler.close()
            print(f"[Info] Serial connection on {self.serial_port} closed.")

    def writePosition(self, type, id, position):
        
        if type == 'mighty':
            self.mightyzap_sdk_handler.writePosition(id, position)

            # read current position for verification
            current_position = self.mightyzap_sdk_handler.readPosition(id)
            print(f"[Info] Verified MightyZap ID {id} position: {current_position}")

        elif type == 'dynamixel':
            self.dynamixel_sdk_handler.writePosition(id, position)

    def readPosition(self, type, id):
                        
        if type == 'mighty':
            current_position = self.mightyzap_sdk_handler.readPosition(id)
            print(f"[Info] Verified MightyZap ID {id} position: {current_position}")

        elif type == 'dynamixel':
            current_position = self.dynamixel_sdk_handler.readPosition(id)
            print(f"[Info] Verified Dynamixel ID {id} position: {current_position}")

if __name__ == "__main__":
    pass