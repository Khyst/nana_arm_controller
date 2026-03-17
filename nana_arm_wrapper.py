import os
import serial

from sdk.dynamixel_lib.dynamixel_sdk_wrapper import *  # Uses Dynamixel SDK library
from sdk.mightyzap_lib.mightyzap_sdk_wrapper import *  # Uses Mightyzap SDK library

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정

class NanaArmWrapper:
    
    def __init__(self, serial_port, baudrate, dxl_models, mighty_models, dxl_ids, mighty_ids, dxl_params={}, mighty_params={}):
        """
            NANA Arm과 Hand의 Low-Level 제어를 담당하는 Wrapper 클래스 (Low-level Interface)
            - serial_handler를 통해 실제 액추에이터와 통신을 함으로써 Arm과 Hand를 제어하는 역할을 수행.
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = 0.0
        
        self.dxl_models = dxl_models
        self.mighty_models = mighty_models
        self.dxl_ids = dxl_ids
        self.mighty_ids = mighty_ids
        self.dxl_params = dxl_params
        self.mighty_params = mighty_params

        self.serial_handler = None

        try:
            self.serial_handler = serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1)
            print(f"[Info] Serial connection established on {self.serial_port} at {self.baudrate} baud.")
        
        except serial.SerialException as e:
            print(f"[Error] Failed to establish serial connection: {e}")
            raise e
        
        self.dynamixel_sdk_handler = DynamixelSDKWrapper(self.serial_handler, self.dxl_models, self.dxl_ids, self.dxl_params)
        self.mightyzap_sdk_handler = MightyZapSDKWrapper(self.serial_handler, self.mighty_models, self.mighty_ids, self.mighty_params)
        
    def __close__(self):
        if self.serial_handler and self.serial_handler.is_open:
            self.serial_handler.close()
            print(f"[Info] Serial connection on {self.serial_port} closed.")

    def enableTorque(self, sources):
        for source in sources:
            id, type = source

            if type == 'dynamixel':
                self.dynamixel_sdk_handler.enableTorque(id)

            elif type == 'mighty':
                self.mightyzap_sdk_handler.enableTorque(id)

    def disableTorque(self, sources):
        for source in sources:
            id, type = source
            if type == 'dynamixel':
                self.dynamixel_sdk_handler.disableTorque(id)

            elif type == 'mighty':
                self.mightyzap_sdk_handler.disableTorque(id)

    def writePosition(self, commands):
        
        for cmd in commands:   
            id, type, position = cmd
            
            if type == 'mighty':
                self.mightyzap_sdk_handler.writePosition(id, position)
            
            elif type == 'dynamixel':
                self.dynamixel_sdk_handler.writePosition(id, position)

    def readPosition(self, sources):
        
        position = []

        for src in sources:
            id, type = src
            
            if type == 'mighty':
                current_position = self.mightyzap_sdk_handler.readPosition(id)
                print(f"[Info] Verified MightyZap ID {id} position: {current_position}")
            
            elif type == 'dynamixel':
                current_position = self.dynamixel_sdk_handler.readPosition(id)
                print(f"[Info] Verified Dynamixel ID {id} position: {current_position}")

            position.append((id, type, current_position))
        
        return position
    
    def isMoving(self, commands):
        """
            Check if any of the actuators are currently moving.
        """
        for cmd in commands:
            id, type, position = cmd
            if type == 'dynamixel':
                if self.dynamixel_sdk_handler.isMoving(id):
                    return True
            elif type == 'mighty':
                if self.mightyzap_sdk_handler.isMoving(id, position):
                    return True
        return False
    
if __name__ == "__main__":
    pass