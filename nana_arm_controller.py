import os
import sys
import time
import math

import yaml
import json

import select
import random
import argparse

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

        self.nana_arm_handler = NanaArmWrapper(serial_port=self.port, baudrate=self.baudrate, dxl_models=self.dxl_models, mighty_models=self.mighty_models, dxl_ids=self.dxl_ids, mighty_ids=self.mighty_ids, dxl_params=self.dxl_params, mighty_params=self.mighty_params)

        print("[Info] NANA Arm with Hand initialized successfully.")

    def _encode_to_radian(self, encode):
        return (encode - 2048) * math.pi / 2048

    def _radian_to_degree(self, radian):
        return radian * 180.0 / math.pi

    def _degree_to_radian(self, degree):
        return degree * math.pi / 180.0

    def _radian_to_encode(self, radian):
        return int(radian * 2048 / math.pi + 2048)

    # Helper Functions to resolve config path
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

    # Helper function to print loaded configuration
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

    # Load configuration from YAML file and declare necessary variables
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
        
        # --- DXL 설정 로드 ---
        dxl_data = data.get('dxl', {})
        self.protocol_version = dxl_data.get('protocol_version', 2.0)
        self.number_of_dxl = int(dxl_data.get('number_of_dxl', 0))
        self.dxl_ids = dxl_data.get('dxl_ids', [])
        self.dxl_names = dxl_data.get('dxl_names', [])
        self.dxl_models = dxl_data.get('dxl_models', [])

        self.dxl_params = dxl_data.get('dxl_params', {})

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

        self.mighty_params = mighty_data.get('mighty_params', {})

        mighty_limits = mighty_data.get('limits', {})
        self.mighty_hard_position_max_limits = mighty_limits.get('hard', {}).get('position', {}).get('max', [])
        self.mighty_hard_position_min_limits = mighty_limits.get('hard', {}).get('position', {}).get('min', [])
        self.mighty_soft_position_max_limits = mighty_limits.get('soft', {}).get('position', {}).get('max', [])
        self.mighty_soft_position_min_limits = mighty_limits.get('soft', {}).get('position', {}).get('min', [])

        self._print_config_info(config_path)

    # Check if the given command is within the defined soft limits
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

    # Generate random position values within hard limits for given arm and hand sources, and execute the move command
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

    # Helper function to print recorded command
    def _print_recorded_command(self, command):
        """
            Helper function for printing recorded command
        """
        print("Recorded Command:")
        for item in command:
            print(item)

    # Helper function to save recorded command into json/motion/ as JSON, matching the format of `json/motion/pick_cup_motion.json`
    def _save_commands(self, command, arm_source=None, hand_source=None):
        """
            Helper function for saving recorded command into json/motion/ as JSON
            The saved format matches `json/motion/pick_cup_motion.json`:
        """
        # prepare output directory json/motion
        save_dir = os.path.join(CURRENT_DIR, "json", "motion")
        os.makedirs(save_dir, exist_ok=True)

        # filename with timestamp
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        filename = f"commands_{timestamp}.json"
        file_path = os.path.join(save_dir, filename)

        try:
            steps = []

            arm_len = len(arm_source) if arm_source is not None else 0
            
            for idx, recorded_step in enumerate(command):
                
                arm_entries = recorded_step[:arm_len]  # recorded_step expected like [(id, type, pos), ...]
                hand_entries = recorded_step[arm_len:]

                # convert tuples to lists to match JSON style
                arm_list = [list(x) for x in arm_entries]
                hand_list = [list(x) for x in hand_entries]

                steps.append({
                    "description": str(idx + 1),
                    "arm": arm_list,
                    "hand": hand_list,
                })

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(steps, f, ensure_ascii=False, indent=4)

            print(f"Successfully saved motion JSON to: {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

    # Helper functions to load motion and pose data from json/motion/ and json/pose/ respectively, given the file name (without .json extension)
    def _load_motion_data(self, file_name):
        file_path = os.path.join(CURRENT_DIR, "json", "motion", file_name + ".json")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    # Helper function to load pose data from json/pose/ given the file name (without .json extension)
    def _load_pose_data(self, file_name):
        
        file_path = os.path.join(CURRENT_DIR, "json", "pose", file_name + ".json")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    # Motion Service Functions
    def move_to_position(self, arm_command, hand_command):
        """
            주어진 관절 위치로 로봇을 이동시키는 함수
            * command 형식 : [(id, type, position),  (id, type, position), ...]
        """
        print(f"[Info] Moving to positions: Arm: {arm_command}, Hand: {hand_command}")

        commands = arm_command + hand_command # List Concatenate

        if not self._is_position_within_limits(commands):
            print("[Error] One or more commands are out of soft limits. Aborting move.")
            return

        self.nana_arm_handler.writePosition(commands)

    # Execute Motion Sequence
    def execute_motion(self, motion_data):

        for step in motion_data:

            description = step.get('description', 'No description provided.')
            arm_command = step.get('arm', [])
            hand_command = step.get('hand', [])
            
            print(f"\n\n[Info] Executing step: {description}")
            print(" ==========================================================================")
            self.move_to_position(arm_command, hand_command)

            

            # self.wait_until_reach_position(arm_command, hand_command)

            time.sleep(1.3)
            print(" ==========================================================================")

        print(f"[Info] Motion execution completed.")

    # Execute Pose
    def execute_pose(self, pose_data):

        description = pose_data.get('description', 'No description provided.')
        arm_command = pose_data.get('arm', [])
        hand_command = pose_data.get('hand', [])
        
        print(f"[Info] Executing pose: {description}")
        print(" ==========================================================================")
        self.move_to_position(arm_command, hand_command)
        self.wait_until_reach_position(arm_command, hand_command)
        print(" ==========================================================================")

        print(f"[Info] Pose execution completed.")

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
            
    # get current position
    def get_position(self, arm_source, hand_source):
        """
            현재 관절 위치를 읽어오는 함수
            * source 형식 : [(id, type), (id_type), ]
        """

        sources = arm_source + hand_source # List Concatenate

        return self.nana_arm_handler.readPosition(sources)

    # Check Menu for getting current position interactively (Press Enter to sample, 'q' to quit)
    def check_menu(self, arm_source, hand_source):

        print("[Info] Interactive check mode. Press Enter to read positions, or type 'q' then Enter to return to menu.")

        step = 0

        try:
            while True:
                try:
                    line = input("Press Enter to sample positions, or 'q' then Enter to quit: ")
                except EOFError:
                    print("[Info] EOF received. Exiting interactive check.")
                    break

                if line is None:
                    continue

                s = line.strip()
                if s in ('q', 'Q'):
                    print("[Info] Exiting interactive check.")
                    break

                # empty Enter -> perform check and print result
                positions = controller.get_position(arm_source, hand_source)
                controller._print_recorded_command(positions)
                step += 1
                print(f"Sample #{step} captured.")

        except KeyboardInterrupt:
            print("[Info] KeyboardInterrupt received. Returning to menu.")

    # Capture Motion with Torque Disable every 2.0 seconds, until user presses Enter or 'q'/'Q'
    def motion_capture(self, arm_source, hand_source, timeout=2.0):
        """
            Torque를 Disable한 상태로 관절을 직접 움직이며 Encoder 값을 기록하기 위한 함수
        """
        # NOTE: Deprecated periodic automatic capture. New behavior:
        # Capture a single frame when the user presses Enter. Type 'q' or 'Q' then Enter to stop.

        # 1. Disable Torque
        sources = arm_source + hand_source
        self.nana_arm_handler.disableTorque(sources)

        # 2. record commands when the user presses Enter
        recorded_commands = []

        step = 0
        print("[Info] Capturing current positions on Enter key press.")
        print("[Info] Press Enter (empty line) to capture one frame, or type 'q'/'Q' then Enter to stop capturing.")

        try:
            while True:
                try:
                    line = input("Press Enter to capture, or type 'q' then Enter to finish: ")
                except EOFError:
                    # e.g., user pressed Ctrl-D or input stream closed
                    print("[Info] EOF received. Stopping capture.")
                    break

                if line is None:
                    continue

                s = line.strip()
                # if user requested to stop
                if s in ('q', 'Q'):
                    print("[Info] Stop signal received. Stopping capture.")
                    break

                # otherwise capture current positions
                command = self.get_position(arm_source, hand_source)
                self._print_recorded_command(command)
                recorded_commands.append(command)
                step += 1
                print(f"Captured step {step}.")

        except KeyboardInterrupt:
            print("[Info] KeyboardInterrupt received. Stopping capture.")

        # 3. Enable Torque
        self.nana_arm_handler.enableTorque(sources)

        # 4. Save Commands into File
        self._save_commands(recorded_commands, arm_source=arm_source, hand_source=hand_source)

def debug_mode(controller, motion_file):
    motion_data = controller._load_motion_data(motion_file)

    if motion_data is None:
        print(f"[Error] {motion_file} 모션 데이터를 불러오는데 실패했습니다. 파일 이름과 경로를 확인해주세요.")
        print(f"path: {os.path.join(CURRENT_DIR, 'json', 'motion', motion_file + '.json')}")
        sys.exit(1)

    controller.execute_motion(motion_data)

    return True

if __name__ == "__main__":

    try:
        controller = NanaArmController()

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("motion_file", nargs="?", default="")
        args, _ = parser.parse_known_args()

        if args.motion_file:
            debug_option = debug_mode(controller, args.motion_file)

            if debug_option:
                sys.exit(0)

        while True:

                print("\n[Command Options]"
                        "\n=========================================================================="
                        "\n motion: Execute Motion Sequence from File"
                        "\n pose: Execute Pose from File"
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
                
                # Motion
                if cmd == 'motion':

                    file_name = input("실행할 모션 파일 이름을 입력하세요 (예시: pick_cup_motion) : ")

                    if not file_name:
                        print("[Error] 파일 이름이 입력되지 않았습니다. pick_cup_motion으로 대체합니다.")
                        file_name = "pick_cup_motion"

                    motion_data = controller._load_motion_data(file_name)

                    if(motion_data is None):
                        print("[Error] 모션 데이터를 불러오는데 실패했습니다. 파일 이름과 경로를 확인해주세요.")
                        print(f"file: {file_name}, path: {os.path.join(CURRENT_DIR, 'json', 'motion', file_name + '.json')}")
                        continue

                    controller.execute_motion(motion_data)
                    
                # Pose
                elif cmd == 'pose':
                    
                    file_name = input("실행할 포즈 파일 이름을 입력하세요 (예시: initial_pose) : ")

                    if not file_name:
                        print("[Error] 파일 이름이 입력되지 않았습니다. initial_pose로 대체합니다.")
                        file_name = "initial_pose"

                    pose_data = controller._load_pose_data(file_name)

                    if(pose_data is None):
                        print("[Error] 포즈 데이터를 불러오는데 실패했습니다. 파일 이름과 경로를 확인해주세요.")
                        print(f"file: {file_name}, path: {os.path.join(CURRENT_DIR, 'json', 'pose', file_name + '.json')}")
                        continue

                    controller.execute_pose(pose_data)

                # Check Current Position (interactive: Enter to sample, 'q' to quit)
                elif cmd == 'check':
                    controller.check_menu(
                        [
                            (1, 'dynamixel'),
                            (2, 'dynamixel'),
                            (3, 'dynamixel'),
                            (4, 'dynamixel'),
                            (5, 'dynamixel'),
                            (6, 'dynamixel'),
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
                    print("Maybe it is harmful if the robot moves to random position. Make sure to clear the area around the robot and be ready to stop the program if anything goes wrong.")
                    input("Press Enter to continue or Ctrl-C to abort...")

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
                    controller.motion_capture(
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
                        ],
                        timeout=2.0
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
                elif cmd == 'q' or cmd == 'quit' or cmd == 'exit' or cmd == 'end':
                    break

                # Invalid Command       
                else:
                    print("유효하지 않은 값입니다. 다시 입력해주세요!")

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"[Error] {e}")

    finally:
        pass
