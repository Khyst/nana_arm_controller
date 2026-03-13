import os
import sys
import time
import yaml
import argparse
import random

from datetime import datetime
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

        self.nana_arm_handler = NanaArmWrapper(serial_port=self.port, baudrate=self.baudrate, dxl_models=self.dxl_models, mighty_models=self.mighty_models, dxl_ids=self.dxl_ids, mighty_ids=self.mighty_ids)

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

    def _is_position_within_limits(self, command):
        """
            주어진 명령이 설정된 소프트 리밋 내에 있는지 확인하는 함수
            * command 형식 : [(id, type, position),  (id, type, position), ...]
        """

        for cmd in command:
            id, type, position = cmd
            
            if type == 'dynamixel':
                idx = self.dxl_ids.index(id)
                v_min = min(self.dxl_soft_position_min_limits[idx], self.dxl_soft_position_max_limits[idx])
                v_max = max(self.dxl_soft_position_min_limits[idx], self.dxl_soft_position_max_limits[idx])

                if not (v_min <= position <= v_max):
                    print(f"[Warning] Out of limits...")
                    return False
            
            elif type == 'mighty':
                idx = self.mighty_ids.index(id)
                v_min = min(self.mighty_soft_position_min_limits[idx], self.mighty_soft_position_max_limits[idx])
                v_max = max(self.mighty_soft_position_min_limits[idx], self.mighty_soft_position_max_limits[idx])

                if not (v_min <= position <= v_max):
                    print(f"[Warning] Out of limits...")
                    return False
        
        return True

    def _make_random_values_under_hard_limits(self, arm_source, hand_source):
        """
            팔과 손에 있어서 가동 범위내 임의의 position을 포함헌 command를 생성해주는 함수
        """

        print("[Info] Generating random positions within hard limits for given sources...")

        # make random arm_command from arm_source
        arm_command = []
        for source in arm_source:
            id, type = source
            if type == 'dynamixel':
                idx = self.dxl_ids.index(id)
                # min과 max 중 진짜 작은 값을 앞에, 큰 값을 뒤에 배치
                v1 = self.dxl_hard_position_min_limits[idx]
                v2 = self.dxl_hard_position_max_limits[idx]
                random_position = random.randint(min(v1, v2), max(v1, v2))
                print(f"[Info] Random position for Dynamixel ID {id}: {random_position} (Limits: {v1} - {v2})")
                
            if type == 'mighty':
                idx = self.mighty_ids.index(id)
                v1 = self.mighty_hard_position_min_limits[idx]
                v2 = self.mighty_hard_position_max_limits[idx]
                random_position = random.randint(min(v1, v2), max(v1, v2))
                print(f"[Info] Random position for MightyZap ID {id}: {random_position} (Limits: {v1} - {v2})")

            arm_command.append((id, type, random_position))
        
        # make random hand_command from hand_soruce
        hand_command = []
        for source in hand_source:
            id, type = source
            if type == 'dynamixel':
                idx = self.dxl_ids.index(id)
                v1 = self.dxl_hard_position_min_limits[idx]
                v2 = self.dxl_hard_position_max_limits[idx]
                random_position = random.randint(min(v1, v2), max(v1, v2))
                print(f"[Info] Random position for Dynamixel ID {id}: {random_position} (Limits: {v1} - {v2})")
            if type == 'mighty':
                idx = self.mighty_ids.index(id)
                v1 = self.mighty_hard_position_min_limits[idx]
                v2 = self.mighty_hard_position_max_limits[idx]
                random_position = random.randint(min(v1, v2), max(v1, v2))
                print(f"[Info] Random position for MightyZap ID {id}: {random_position} (Limits: {v1} - {v2})")

            hand_command.append((id, type, random_position))

        print(f"[Info] Generated Hand Command: {hand_command}")

        self.move_to_position(arm_command, hand_command)

    def _print_recorded_command(self, command):
        """
            Helper function for printing recorded command
        """
        print("Recorded Command:")
        for item in command:
            print(item)

    def _save_commands(self, command):
        """
            Helper function for saving recorded command into file in commands/
        """
        # 1. Define and create the 'command' directory
        save_dir = os.path.join(CURRENT_DIR, "command")
        os.makedirs(save_dir, exist_ok=True)

        # 2. Define and create filename with timestamp
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        filename = f"commands_{timestamp}.txt"
        
        #3. Define the full file path
        file_path = os.path.join(save_dir, filename)
        
        # 4. Write the data to the file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for item in command:
                    f.write(f"{item}\n")
            print(f"Successfully saved to: {file_path}")
        except Exception as e:
            print(f"Error saving file: {e}")

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
        self.number_of_dxl = int(dxl_data.get('number_of_dxl', 0))
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

        commands = arm_command + hand_command # List Concatenate

        # if not self._is_position_within_limits(commands):
        #     print("[Error] One or more commands are out of soft limits. Aborting move.")
        #     return

        self.nana_arm_handler.writePosition(commands)

    # Wait Until Reach Position
    def wait_until_reach_position(self, arm_command, hand_command, timeout=10.0):
        """
            Dynamixel 및 MightyZap이 Moving Status가 False임을 반환할 때 까지 대기하는 함수
        """

        commands = arm_command + hand_command # List Concatenate
        
        while True:
            
            if self.nana_arm_handler.isMoving(commands) == False:
                break

            time.sleep(0.01)
            
    # Check current position
    def check_current_position(self, arm_source, hand_source):
        """
            현재 관절 위치를 읽어오는 함수
            * source 형식 : [(id, type), (id_type), ]
        """

        sources = arm_source + hand_source # List Concatenate

        return self.nana_arm_handler.readPosition(sources)

    # Capture Motion with Torque Disable
    def capture_motion(self, arm_source, hand_source):
        """
            Torque를 Disable한 상태로 관절을 직접 움직이며 Encoder 값을 기록하기 위한 함수
        """

        # 1. Disable Toruqe
        sources = arm_source + hand_source
        self.nana_arm_handler.disableTorque(sources)


        # 2. record commands repeately
        recorded_commands = []

        step = 0
        while True:
            user_input = input(f"{step}번째 모션 캡처? (Y: 캡처,  X: 종료)")
            print("==========================================================================")

            if(user_input == 'X' or user_input =='x'):
                break

            # 2.1 get the current positions from dxl and mighty zap
            command = self.check_current_position(arm_source, hand_source)
            self._print_recorded_command(command)
            recorded_commands.append(command)
            step = step + 1

        # 3. Enable Torque
        self.nana_arm_handler.enableTorque(sources)

        # 4. Save Commands into File
        self._save_commands(recorded_commands)

if __name__ == "__main__":

    try:
        controller = NanaArmController()

        while True:

                print("\n[Command Options]"
                        "\n=========================================================================="
                        "\n a: Motion A (물체 파지)"
                        "\n b: Motion B (물체 파지 + 초기자세로 돌아오기)"
                        "\n c: Motion C (팔 벌리기 + 물체 파지)"
                        "\n i: Pose I (Initial Pose)"
                        "\n s: Pose S (Stretch Pose)"
                        "\n check: Check Current Position"
                        "\n random: Make Random Position within Hard Limits and Move"
                        "\n motion_capture: Capture Motion with Torque Off"
                        "\n torque_off: Turn Torque Off"
                        "\n torque_on: Turn Torque On"
                        "\n debug: Debug Mode for Moving to Custom Position"

                        "\n q: Quit"
                        "\n=========================================================================="
                )

                cmd = input("명령 입력 : ").lower()
                
                # Move Option A (가장 유력)
                if cmd == 'a':

                    # 팔벌리기
                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 2000), 
                            (2, 'dynamixel', 2000), 
                            (3, 'dynamixel', 2000), 
                            (4, 'dynamixel', 3000), 
                            (5, 'dynamixel', 2100), 
                            (6, 'dynamixel', 2100)
                        ],
                        [
                            (21,'dynamixel', 1020), 
                            (1, 'mighty', 1048), 
                            (2, 'mighty', 920), 
                            (3, 'mighty', 920)
                        ]
                    )

                    controller.wait_until_reach_position(
                        [
                            (1, 'dynamixel', 2000), 
                            (2, 'dynamixel', 2000), 
                            (3, 'dynamixel', 2000), 
                            (4, 'dynamixel', 3000), 
                            (5, 'dynamixel', 2100), 
                            (6, 'dynamixel', 2100)
                        ],
                        [
                            (21,'dynamixel', 1020), 
                            (1, 'mighty', 1048), 
                            (2, 'mighty', 920), 
                            (3, 'mighty', 920)
                        ]
                    )

                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 1868), 
                            (2, 'dynamixel', 1316), 
                            (3, 'dynamixel', 1289), 
                            (4, 'dynamixel', 3544), 
                            (5, 'dynamixel', 1932), 
                            (6, 'dynamixel', 1435)
                        ],
                        [
                            (21, 'dynamixel', 1021), 
                            (1, 'mighty', 1024), 
                            (2, 'mighty', 917), 
                            (3, 'mighty', 924)
                        ]
                    )

                    controller.wait_until_reach_position(
                        [
                            (1, 'dynamixel', 1868), 
                            (2, 'dynamixel', 1316), 
                            (3, 'dynamixel', 1289), 
                            (4, 'dynamixel', 3544), 
                            (5, 'dynamixel', 1932), 
                            (6, 'dynamixel', 1435)
                        ],
                        [
                            (21, 'dynamixel', 1021), 
                            (1, 'mighty', 1024), 
                            (2, 'mighty', 917), 
                            (3, 'mighty', 924)
                        ]
                    )

                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 1752),
                            (2, 'dynamixel', 1356), 
                            (3, 'dynamixel', 1799), 
                            (4, 'dynamixel', 3871), 
                            (5, 'dynamixel', 1512), 
                            (6, 'dynamixel', 1059)
                        ],
                        [
                            (21, 'dynamixel', 2048), 
                            (1, 'mighty', 1024), 
                            (2, 'mighty', 917), 
                            (3, 'mighty', 925)
                        ]
                    )

                    controller.wait_until_reach_position(
                        [
                            (1, 'dynamixel', 1752),
                            (2, 'dynamixel', 1356), 
                            (3, 'dynamixel', 1799), 
                            (4, 'dynamixel', 3871), 
                            (5, 'dynamixel', 1512), 
                            (6, 'dynamixel', 1059)
                        ],
                        [
                            (21, 'dynamixel', 2048), 
                            (1, 'mighty', 1024), 
                            (2, 'mighty', 917), 
                            (3, 'mighty', 925)
                        ]
                    )

                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 1752),
                            (2, 'dynamixel', 1356), 
                            (3, 'dynamixel', 1799), 
                            (4, 'dynamixel', 3871), 
                            (5, 'dynamixel', 1512), 
                            (6, 'dynamixel', 1059)
                        ],
                        [
                            (21, 'dynamixel', 2048), 
                            (1, 'mighty', 460), 
                            (2, 'mighty', 260), 
                            (3, 'mighty', 260)
                        ]
                    )
                
                # Check Current Position
                elif cmd == 'check':
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
                
                # Make feasible random position and execute
                elif cmd == 'random':
                    controller._make_random_values_under_hard_limits(
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
                
                # Motion Capture
                elif cmd == 'motion_capture':
                    # capture motion with torque off.
                    controller.capture_motion(
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
                
                # Torque Off 
                elif cmd == 'torque_off':
                    controller.nana_arm_handler.disableTorque(
                         [
                            (1, 'dynamixel'), 
                            (2, 'dynamixel'), 
                            (3, 'dynamixel'), 
                            (4, 'dynamixel'), 
                            (5, 'dynamixel'), 
                            (6, 'dynamixel')
                        ]+
                        [
                            (21, 'dynamixel'),
                            (1, 'mighty'),
                            (2, 'mighty'),
                            (3, 'mighty')
                        ]
                    )

                # Torque On
                elif cmd == 'torque_on':
                    controller.nana_arm_handler.enableTorque(
                         [
                            (1, 'dynamixel'), 
                            (2, 'dynamixel'), 
                            (3, 'dynamixel'), 
                            (4, 'dynamixel'), 
                            (5, 'dynamixel'), 
                            (6, 'dynamixel')
                        ]+
                        [
                            (21, 'dynamixel'),
                            (1, 'mighty'),
                            (2, 'mighty'),
                            (3, 'mighty')
                        ]
                    )

                # Initial Pose
                elif cmd == 'i':
                    # initial pose
                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 2001), 
                            (2, 'dynamixel', 1970), 
                            (3, 'dynamixel', 2017), 
                            (4, 'dynamixel', 2935), 
                            (5, 'dynamixel', 1340), 
                            (6, 'dynamixel', 1928)
                        ],
                        [
                            (21, 'dynamixel', 1020), 
                            (1, 'mighty', 1028), 
                            (2, 'mighty', 920), 
                            (3, 'mighty', 920)
                        ]
                    )

                    # initial pose
                    # controller.move_to_position(
                    #     [
                    #         (1, 'dynamixel', 1993), 
                    #         (2, 'dynamixel', 2134), 
                    #         (3, 'dynamixel', 2034), 
                    #         (4, 'dynamixel', 2905), 
                    #         (5, 'dynamixel', 1319), 
                    #         (6, 'dynamixel', 2067)
                    #     ],
                    #     [
                    #         (21, 'dynamixel', 1298), 
                    #         (1, 'mighty', 1028), 
                    #         (2, 'mighty', 920), 
                    #         (3, 'mighty', 920)
                    #     ]
                    # )
                    print(f"initial pose is executed")
                
                # Stretch Pose
                elif cmd == 's':
                    # Stretch

                    # 팔벌리기
                    controller.move_to_position(
                        [
                            (1, 'dynamixel', 2000), 
                            (2, 'dynamixel', 2000), 
                            (3, 'dynamixel', 2000), 
                            (4, 'dynamixel', 3000), 
                            (5, 'dynamixel', 2100), 
                            (6, 'dynamixel', 2100)
                        ],
                        [
                            (21,'dynamixel', 1020), 
                            (1, 'mighty', 1048), 
                            (2, 'mighty', 920), 
                            (3, 'mighty', 920)
                        ]
                    )

                # Debug
                elif cmd == 'debug':
                    print("\n[Debug Mode] 포지션 값을 순서대로 입력하세요.")
                    print("형식: Arm(1~6) Hand(21, M1~3) 순서로 10개의 숫자 입력")
                    print("예시: 1774 1967 1234 2848 1381 1952 2000 1048 920 920")
                    
                    line = input(">> ").replace(',', ' ') # 콤마가 있어도 공백으로 변환
                    values = line.split()

                    if len(values) == 10:
                        try:
                            # 입력받은 문자열을 숫자로 변환
                            v = [int(x) for x in values]
                            
                            # 데이터 할당 및 실행
                            controller.move_to_position(
                                [
                                    (1, 'dynamixel', v[0]), (2, 'dynamixel', v[1]), 
                                    (3, 'dynamixel', v[2]), (4, 'dynamixel', v[3]), 
                                    (5, 'dynamixel', v[4]), (6, 'dynamixel', v[5])
                                ],
                                [
                                    (21, 'dynamixel', v[6]), (1, 'mighty', v[7]), 
                                    (2, 'mighty', v[8]), (3, 'mighty', v[9])
                                ]
                            )
                            print("[Success] 명령이 전송되었습니다.")
                        except ValueError:
                            print("[Error] 숫자만 입력 가능합니다.")
                    else:
                        print(f"[Error] 10개의 값이 필요합니다. (현재 {len(values)}개 입력됨)")
                
                # Quit
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
