import os
import sys
import time
import yaml
import json
import select
import random
import argparse

from datetime import datetime
from typing import Any, Dict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # 라이브러리 경로 설정
CONFIG_FILE_NAME = 'nana_arm_controller_config.yaml'

from nana_arm_controller import NanaArmController

if __name__ == "__main__":
    
    controller = NanaArmController()

    # pick_cup과 release_cup을 반복적으로 실행
    REPEAT_COUNT = 1000
    
    for _ in range(REPEAT_COUNT):
        print(f"\n\n[Experiment] Starting pick_cup motion...")
        pick_cup_motion_data = controller._load_motion_data("pick_cup")
        if pick_cup_motion_data is None:
            print("[Error] Failed to load pick_cup_motion data.")
            sys.exit(1)
        controller.execute_motion(pick_cup_motion_data)

        time.sleep(1.0)

        print(f"\n\n[Experiment] Starting release_cup motion...")
        release_cup_motion_data = controller._load_motion_data("release_cup")
        if release_cup_motion_data is None:
            print("[Error] Failed to load release_cup_motion data.")
            sys.exit(1)
        controller.execute_motion(release_cup_motion_data)

        time.sleep(1.0)