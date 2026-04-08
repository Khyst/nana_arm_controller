import os
import time
import serial

from sdk.dynamixel_lib.dynamixel_sdk_wrapper import *  # Uses Dynamixel SDK library
from sdk.mightyzap_lib.mightyzap_sdk_wrapper import *  # Uses Mightyzap SDK library

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정

class NanaArmWrapper:
    
    def __init__(self, serial_port, baudrate, dxl_models, mighty_models, dxl_ids, mighty_ids, dxl_profiles, mighty_profiles):
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
        self.dxl_profiles = dxl_profiles
        self.mighty_profiles = mighty_profiles

        self.serial_handler = None

        try:
            self.serial_handler = serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1)
            print(f"[Info] Serial connection established on {self.serial_port} at {self.baudrate} baud.")
        
        except serial.SerialException as e:
            print(f"[Error] Failed to establish serial connection: {e}")
            raise e
        
        self.dynamixel_sdk_handler = DynamixelSDKWrapper(self.serial_handler, self.dxl_models, self.dxl_ids, self.dxl_profiles)
        self.mightyzap_sdk_handler = MightyZapSDKWrapper(self.serial_handler, self.mighty_models, self.mighty_ids, self.mighty_profiles)
        
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
    
    def reconnect_serial(self):
        
        print("[Info] Re-establishing serial connection for recovery...")
    
        # 1. 기존 포트 닫기
        if self.serial_handler and self.serial_handler.is_open:
            self.serial_handler.close()
        
        time.sleep(0.5)

        # 2. 포트 새로 열기
        try:
            self.serial_handler = serial.Serial(port=self.serial_port, baudrate=self.baudrate, timeout=1)
            
            # 각 SDK 핸들러에 새로운 시리얼 핸들러 할당
            # Prefer calling each wrapper's reset method so internal SDK objects also update their serial reference
            try:
                # update wrapper attributes
                self.dynamixel_sdk_handler.reset_serial_handler(self.serial_handler)
            except Exception:
                # fallback to direct assignment if reset method not available
                self.dynamixel_sdk_handler.serial_handler = self.serial_handler
                try:
                    self.dynamixel_sdk_handler.dynamixel_sdk.ser = self.serial_handler
                except Exception:
                    pass

            try:
                self.mightyzap_sdk_handler.reset_serial_handler(self.serial_handler)
            except Exception:
                self.mightyzap_sdk_handler.serial_handler = self.serial_handler
                try:
                    self.mightyzap_sdk_handler.mightyzap_sdk.ser = self.serial_handler
                except Exception:
                    pass

            print("[Info] Serial connection reset successful.")

        except Exception as e:
            print(f"[Error] Failed to reconnect serial: {e}")

    def safe_torque_on(self, sources):

        self.reconnect_serial()

        # self.serial_handler.reset_input_buffer()
        # self.serial_handler.reset_output_buffer()
        
        for source in sources:
            id, type = source

            if type == 'dynamixel':
                self.dynamixel_sdk_handler.setSafeTorqueOn(id)

            elif type == 'mighty':
                self.mightyzap_sdk_handler.setSafeTorqueOn(id)

if __name__ == "__main__":
    pass