import os
import sys
import time
import yaml
import argparse

from typing import Any, Dict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정
CONFIG_FILE_NAME = 'nana_arm_controller_config.yaml'

# NANA Actuator 동작을 위한 Hardware Control Wrapper 클래스 임포트
from nana_arm_wrapper import NanaArmWrapper

class NanaArmController:
    """
        NANA Arm과 Hand를 움직이는 서비스를 위한 Controller 클래스 (High-Level Interface)        
    """

    def __init__(self):
        """
            파라미터 로드 및 초기화, NANA Arm과 Hand Low-Level 제어를 위한 Handler 객체 생성
        """

        self.load_and_declare_config()

        self.nana_arm_handler = NanaArmWrapper(serial_port=self.port, baudrate=self.baudrate, dxl_models=self.dxl_models, mighty_models=self.mighty_models)

        print("[Info] NANA Arm with Hand initialized successfully.")

    # Helper Functions
    def _resolve_config_path(self, file_name):
        """
            설정 파일의 경로를 찾는 Helper 함수
        """

        candidates = [
            os.path.join(CURRENT_DIR, 'config', file_name),
            os.path.join(CURRENT_DIR, 'src', 'config', file_name),
        ]

        for path in candidates:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError(f'{CONFIG_FILE_NAME} 파일을 찾을 수 없습니다.')

    def _print_config_info(self, config_path):
        """ 로드된 설정을 출력하는 헬퍼 함수 """
        print(f"[Info] Configuration loaded from {config_path}")
        print(f"       Port: {self.port}, Baudrate: {self.baudrate}")
        print(f"       --- DXL ({self.number_of_dxl} units) ---")
        print(f"       IDs: {self.dxl_ids}")
        print(f"       Models: {self.dxl_models}")
        print(f"       Soft Limits (Max/Min): {self.dxl_soft_position_max_limits} / {self.dxl_soft_position_min_limits}")
        print(f"       --- Mighty ({self.number_of_mighty} units) ---")
        print(f"       IDs: {self.mighty_ids}")
        print(f"       Models: {self.mighty_models}")
        print(f"       Soft Limits (Max/Min): {self.mighty_soft_position_max_limits} / {self.mighty_soft_position_min_limits}")

    def load_and_declare_config(self):
        """
            설정 파일을 로드하고, 필요한 변수들을 선언하는 함수
        """
        
        config_path = self._resolve_config_path(CONFIG_FILE_NAME)

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # 공통 설정 로드
        self.port = data.get('port', '/dev/ttyUSB0')
        self.baudrate = data.get('baud_rate', 115200) # YAML의 baud_rate와 일치시킴
        self.protocol_version = data.get('protocol_version', 2.0)

        # --- DXL 설정 로드 ---
        dxl_data = data.get('dxl', {})
        self.number_of_dxl = dxl_data.get('number_of_dxl', 0)
        self.dxl_ids = dxl_data.get('dxl_ids', [])
        self.dxl_names = dxl_data.get('dxl_names', [])
        self.dxl_models = dxl_data.get('dxl_models', [])

        dxl_limits = dxl_data.get('limits', {})
        self.dxl_hard_position_max_limits = dxl_limits.get('hard', {}).get('position', {}).get('max', [])
        self.dxl_hard_position_min_limits = dxl_limits.get('hard', {}).get('position', {}).get('min', [])
        self.dxl_soft_position_max_limits = dxl_limits.get('soft', {}).get('position', {}).get('max', [])
        self.dxl_soft_position_min_limits = dxl_limits.get('soft', {}).get('position', {}).get('min', [])

        # --- Mighty 설정 로드 ---
        mighty_data = data.get('mighty', {})
        self.number_of_mighty = mighty_data.get('number_of_mighty', 0)
        self.mighty_ids = mighty_data.get('mighty_ids', [])
        self.mighty_names = mighty_data.get('mighty_names', [])
        self.mighty_models = mighty_data.get('mighty_models', [])

        mighty_limits = mighty_data.get('limits', {})
        self.mighty_hard_position_max_limits = mighty_limits.get('hard', {}).get('position', {}).get('max', [])
        self.mighty_hard_position_min_limits = mighty_limits.get('hard', {}).get('position', {}).get('min', [])
        self.mighty_soft_position_max_limits = mighty_limits.get('soft', {}).get('position', {}).get('max', [])
        self.mighty_soft_position_min_limits = mighty_limits.get('soft', {}).get('position', {}).get('min', [])

        self._print_config_info(config_path)

    # Motion Service Functions
    def move_to_position(self, arm_command, hand_command):
        """
            주어진 관절 위치로 로봇을 이동시키는 함수
            * command 형식 : [(id, type, position),  (id, type, position), ...]
        """
        print(f"[Info] Moving to positions: Arm: {arm_command}, Hand: {hand_command}")

        commands = arm_command + hand_command

        self.nana_arm_handler.writePosition(commands)

    # Check current position
    def check_current_position(self, arm_source, hand_source):
        """
            현재 관절 위치를 읽어오는 함수
            * source 형식 : [(id, type), (id_type), ]
        """

        sources = arm_source + hand_source

        self.nana_arm_handler.readPosition(sources)
            
if __name__ == "__main__":
    
    """
        Do some sequence for grasp water bottle, for example:

        # 1. 기본 자세
            - [A1, A1, A1, A1, A1, A1] & [H1, H1, H1, H1]
        # 2. 팔꿈치를 굽히며 팔을 잡는 자세
            - [A2, A2, A2, A2, A2, A2] & [H2, H2, H2, H2]
        # 3. 핸드 열기
            - [A3, A3, A3, A3, A3, A3] & [H3, H3, H3, H3]
        # 4. 컵에 다가가기
            - [A4, A4, A4, A4, A4, A4] & [H4, H4, H4, H4]
        # 5. 핸드 닫기 (컵 잡기)
            - [A5, A5, A5, A5, A5, A5] & [H5, H5, H5, H6]
        # 6. 컵 릴리즈 하기
            - [A6, A6, A6, A6, A6, A6] & [H6, H6, H6, H6]
    """

    try:
        controller = NanaArmController()

        while True:

                cmd = input("명령 입력 (a: 첫번 째 모션, b: 현 위치 확인, q: 종료): ").lower()
                
                if cmd == 'a':
                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 2000), 
                            (2, 'dynamixel', 1200), 
                            (3, 'dynamixel', 1500), 
                            (4, 'dynamixel', 1500), 
                            (5, 'dynamixel', 1500), 
                            (6, 'dynamixel', 2000)
                        ],
                        [
                            (21,'dynamixel', 2000), 
                            (1, 'mighty', 460), 
                            (2, 'mighty', 260), 
                            (3, 'mighty', 260)
                        ]
                    )
                
                elif cmd == 'b':
                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 2000), 
                            (2, 'dynamixel', 1200), 
                            (3, 'dynamixel', 1500), 
                            (4, 'dynamixel', 1500), 
                            (5, 'dynamixel', 1500), 
                            (6, 'dynamixel', 2000)
                        ],
                        [
                            (21,'dynamixel', 2000), 
                            (1, 'mighty', 600), 
                            (2, 'mighty', 600), 
                            (3, 'mighty', 600)
                        ]
                    )
                    
                elif cmd == 'c':
                    controller.check_current_position(
                        [
                            (1, 'dynamixel'), 
                            (2, 'dynamixel'), 
                            (3, 'dynamixel'), 
                            (4, 'dynamixel'), 
                            (5, 'dynamixel'), 
                            (6, 'dynamixel')
                        ],
                        [
                            (21, 'dynamixel'),
                            (1, 'mighty'),
                            (2, 'mighty'),
                            (3, 'mighty')
                        ]
                    )
                
                elif cmd == 'q':
                    break
                else:
                    print("유효하지 않은 값입니다. 다시 입력해주세요!")

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"[Error] {e}")

    finally:
        pass
