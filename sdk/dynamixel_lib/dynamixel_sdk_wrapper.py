import os
import time
from typing import Dict, Any

from .dynamixel_sdk import DynamixelSDK  # unified SDK class

# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정
CURRENT_DIR = "/home/ras/nana_arm_operation_ws/src/nana_arm_controller"

class DynamixelSDKWrapper:
    """
        최종 packet, port 통신을 통해 Hardware에 직접 제어하는 부분에 대한 Wrapper
    """
    
    def __init__(self, serial_handler, dxl_models, dxl_ids, dxl_params):
        
        self.serial_handler = serial_handler
        self.dxl_models = dxl_models
        self.dxl_ids = dxl_ids
        self.dxl_params = dxl_params
        
        self.dynamixel_control_tables = self._load_control_table(self.dxl_models)
        self.dynamixel_sdk = DynamixelSDK(serial_handler, protocol_version=2.0)

        self._initial_setup(dxl_params=self.dxl_params)

        print(f"[Info] Initialized DynamixelSDKWrapper with provided serial handler and model information")

    def _resolve_control_table_path(self, model_name):
        """
            모델 이름에 따른 Control Table 파일 경로를 찾는 Helper 함수
        """

        candidates = [
            os.path.join(CURRENT_DIR, 'control_tables', 'dynamixel', f"{model_name}.model"),
            os.path.join(CURRENT_DIR, 'src', 'control_tables', 'dynamixel', f"{model_name}.model"),
        ]

        for path in candidates:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError(f'{model_name} 모델의 Control Table 파일을 찾을 수 없습니다.')
        
    def _parse_dynamixel_model_control_table_info(self, control_table_path: str) -> Dict[str, Any]:
        """
            주어진 모델 이름에 대한 Control Table 정보를 반환하는 함수
        """

        from dxl_model_parser import DynamixelModelParser # Import Dynamixel Model Parser

        dxl_parser = DynamixelModelParser(path=control_table_path)

        # 제어 테이블 객체 반환받기
        control_table_obj = dxl_parser.parse_file()

        return control_table_obj
    
    def _load_control_table(self, dxl_models):

        dynamixel_control_tables = {}
        
        for model in dxl_models:
            control_table_path = self._resolve_control_table_path(model)
            control_table = self._parse_dynamixel_model_control_table_info(control_table_path)
            
            if control_table:
                dynamixel_control_tables[model] = control_table
            else:
                print(f"[Warning] Control Table 정보를 로드하지 못했습니다: {model}")
        
        return dynamixel_control_tables
    
    def _initial_setup(self, dxl_params):
        """
            Dynamixel SDK 초기 설정을 수행하는 함수
        """
        print(f"[Info] Performing initial setup for Dynamixel SDK")

        for id in self.dxl_ids:
            idx = self.dxl_ids.index(id)
            print(f"[Info] Initializing Dynamixel ID {id} (Model: {self.dxl_models[idx]})")

            # Torque Enable
            self.enableTorque(id)
            print(f"[Info] Enabled torque for Dynamixel ID {id} (Model: {self.dxl_models[idx]})")

            if dxl_params:
                 # If parameters are provided, use them
                profile_velocity = dxl_params.get('profile_velocity', 2000)
                profile_acceleration = dxl_params.get('profile_acceleration', 3000)
                self.setProfileVelocity(id, profile_velocity[idx])
                self.setProfileAcceleration(id, profile_acceleration[idx])
                print(f"[Info] Set Profile Velocity to {profile_velocity[idx]} and Acceleration to {profile_acceleration[idx]} for Dynamixel ID {id} (Model: {self.dxl_models[idx]})")
            else:
                print(f"[Info] No custom parameters provided for Dynamixel ID {id} (Model: {self.dxl_models[idx]}), using default Profile Velocity: 2000 and Acceleration: 3000")
                self.setProfileVelocity(id, 2000)
                self.setProfileAcceleration(id, 3000)
                print(f"[Info] Set Profile Velocity to 2000 and Acceleration to 3000 for Dynamixel ID {id} (Model: {self.dxl_models[idx]})")

    def writePosition(self, id, position):
        print(f"[DynamixelSDKWrapper] Writing position {position} to ID {id}")
        self.setGoalPosition(id, position)
           
    def readPosition(self, id):

        position = self.getCurrentPosition(id)[0]

        print(f"[DynamixelSDKWrapper] Reading position from Dynamixel ID {id} is {position}")

        return position

    """ Helper Function """
    def enableTorque(self, id):
        idx = self.dxl_ids.index(id)
        self.dynamixel_sdk.write1ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Torque Enable').get('address'), 1)

    def disableTorque(self, id):
        idx = self.dxl_ids.index(id)
        self.dynamixel_sdk.write1ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Torque Enable').get('address'), 0)
    
    def setProfileVelocity(self, id, value):
        idx = self.dxl_ids.index(id)
        self.dynamixel_sdk.write4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Profile Velocity').get('address'), value)
        
    def setProfileAcceleration(self, id, value):
        idx = self.dxl_ids.index(id)
        self.dynamixel_sdk.write4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Profile Acceleration').get('address'), value)

    def setGoalPosition(self, id, value):
        idx = self.dxl_ids.index(id)
        self.dynamixel_sdk.write4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Goal Position').get('address'), value)

    def getCurrentPosition(self, id):
        idx = self.dxl_ids.index(id)
        return self.dynamixel_sdk.read4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Present Position').get('address'))
    
    def isMoving(self, id):
        idx = self.dxl_ids.index(id)
        return self.dynamixel_sdk.read1ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[idx]].get('Moving').get('address')) == 1

    def reset_serial_handler(self, new_serial_handler):
        self.serial_handler = new_serial_handler
        self.dynamixel_sdk.ser = new_serial_handler
        # _SerialPortAdapter도 새로운 serial 참조로 갱신해야 실제 통신에 사용됨
        self.dynamixel_sdk._port.ser = new_serial_handler
        print(f"[DynamixelSDKWrapper] Serial handler reset successfully")

    def setSafeTorqueOn(self, id):
        
        # 하드웨어 reboot
        print(f"[DynamixelSDKWrapper] Rebooting ID {id} to ensure safe torque on")
        self.dynamixel_sdk.reboot(id)
        time.sleep(0.5)  # Reboot 후 잠시 대기

        # 현재 위치 동기화
        current_position = self.getCurrentPosition(id)[0]
        print(f"[DynamixelSDKWrapper] Setting safe torque on for ID {id} by first moving to current position {current_position}")
        self.setGoalPosition(id, current_position)

        # 프로파일 재설정
        self.setProfileVelocity(id, 1000)  # Set a reasonable velocity for the move
        self.setProfileAcceleration(id, 2000)  # Set a reasonable acceleration for the move

        # 최종적으로 토크 인가
        self.enableTorque(id)
    