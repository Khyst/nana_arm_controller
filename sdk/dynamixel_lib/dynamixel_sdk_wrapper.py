import os
from typing import Dict, Any

from .dynamixel_sdk import DynamixelSDK  # unified SDK class

# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정
CURRENT_DIR = "/home/ras/nana_arm_operation_ws/src/nana_arm_controller"

class DynamixelSDKWrapper:
    
    def __init__(self, serial_handler, dxl_models):
        
        self.serial_handler = serial_handler
        self.dxl_models = dxl_models
        
        self.dynamixel_control_tables = self.load_control_table(self.dxl_models)

        self.dynamixel_sdk = DynamixelSDK(serial_handler, protocol_version=2.0)

        print(f"[Info] Initialized DynamixelSDKWrapper with provided serial handler and model information")

    def _resolve_control_table_path(self, model_name):
        """
            모델 이름에 따른 Control Table 파일 경로를 찾는 Helper 함수
        """

        candidates = [
            os.path.join(CURRENT_DIR, 'control_tables', f"{model_name}.model"),
            os.path.join(CURRENT_DIR, 'src', 'control_tables', f"{model_name}.model"),
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
    
    def load_control_table(self, dxl_models):

        dynamixel_control_tables = {}
        
        for model in dxl_models:
            control_table_path = self._resolve_control_table_path(model)
            control_table = self._parse_dynamixel_model_control_table_info(control_table_path)
            
            if control_table:
                dynamixel_control_tables[model] = control_table
            else:
                print(f"[Warning] Control Table 정보를 로드하지 못했습니다: {model}")
        
        return dynamixel_control_tables
    
    def writePosition(self, id, position):
        print(f"[DynamixelSDKWrapper] Writing position {position} to ID {id}")
        self.dynamixel_sdk.write4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[id]].get('Goal Position').get('address'), position)
        
    def readPosition(self, id):
        print(f"[DynamixelSDKWrapper] Reading position from Dynamixel ID {id}")
        return self.dynamixel_sdk.read4ByteTxRx(id, self.dynamixel_control_tables[self.dxl_models[id]].get('Present Position').get('address'))