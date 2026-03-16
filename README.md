# Robot Arm with Hand Controller

Dynamixel과 MightyZap 액추에이터로 구성된 로봇 팔을 제어하기 위한 High-Level to Low-Level 제어 패키지입니다.

## Features

- 하나의 시리얼 포트 통신으로 여러 종류의 액추에이터 하드웨어 인터페이스를 통합
- High-Level(사람 친화적) 명령을 Low-Level(하드웨어 제어 친화적) 명령으로 전달하는 제어 플로우 제공

## Prerequisites

- pyserial
- pyyaml

## Installation

```bash
git clone https://github.com/khyst/nana_arm_controller.git
cd nana_arm_controller
```

## Quick Start

```bash
python3 nana_arm_controller.py
```

## Scripts

- nana_arm_controller.py
    - High-Level에서 로봇 팔 제어를 수행하는 메인 애플리케이션
- nana_arm_wrapper.py
    - 로봇 팔에 연결된 다양한 하드웨어를 통합 인터페이스로 관리하는 Wrapper
- dxl_model_parser.py
    - Dynamixel 액추에이터별 Control Table(주소, Instruction Byte 등) 로드
- sdk/dynamixel_lib/dynamixel_wrapper.py
    - Dynamixel 저수준 제어 기능을 단위 기능별로 묶은 Wrapper
- sdk/dynamixel_lib/dynamixel_sdk.py
    - Dynamixel 프로토콜 기반 저수준 제어 SDK
- sdk/mightyzap_lib/mightyzap_wrapper.py
    - MightyZap 저수준 제어 기능을 단위 기능별로 묶은 Wrapper
- sdk/mightyzap_lib/mightyzap_sdk.py
    - MightyZap 프로토콜 기반 저수준 제어 SDK

## Configuration

config/nana_arm_controller_config.yaml 파일을 통해 파라미터를 수정할 수 있습니다. 

### Common

- port: 장치 연결 경로 (예: /dev/ttyUSB0)
- baudrate: 통신 속도 (기본값: 115200)

### DXL (Dynamixel)

- number_of_dxl: 연결된 Dynamixel 액추에이터 수 (현재 7개)
- dxl_ids / dxl_names: 조인트 ID와 이름 매핑 (joint1~6, hand_joint)
- dxl_models: 각 ID에 해당하는 Dynamixel 모델명 (예: XM540_W270)
- limits: 각 조인트의 하드웨어/소프트웨어 위치 제한(max, min)

### Mighty (MightyZap)

- number_of_mighty: 연결된 MightyZap 액추에이터 수 (현재 3개)
- mighty_ids / mighty_names: 그리퍼 조인트 ID와 이름 (gripper_joint1~3)
- mighty_models: 사용 중인 MightyZap 모델명 (예: D12-12F-3)
- limits: 각 액추에이터의 스트로크 하드웨어/소프트웨어 제한값

## JSON Data Format

### motion/

모션 시퀀스(예: pick_cup.json)를 정의합니다.

```json
[
    {
        "description": "Step 1: 초기 위치 및 중심 잡기",
        "arm": [[1,"dynamixel",2050],[2,"dynamixel",2047],[3,"dynamixel",2044],[4,"dynamixel",2049],[5,"dynamixel",1202],[6,"dynamixel",2080]],
        "hand": [[21,"dynamixel",1027],[1,"mighty",2000],[2,"mighty",920],[3,"mighty",920]]
    },
    {
        "description": "Step 2: 책상 높이로 이동",
        "arm": [[1,"dynamixel",1915],[2,"dynamixel",1882],[3,"dynamixel",796],[4,"dynamixel",2900],[5,"dynamixel",1328],[6,"dynamixel",2392]],
        "hand": [[21,"dynamixel",1052],[1,"mighty",2000],[2,"mighty",920],[3,"mighty",920]]
    },
    {
        "description": "Step 3: 물체를 향해 뻗기",
        "arm": [[1,"dynamixel",1915],[2,"dynamixel",1882],[3,"dynamixel",1200],[4,"dynamixel",3300],[5,"dynamixel",1328],[6,"dynamixel",1800]],
        "hand": [[21,"dynamixel",2300],[1,"mighty",2000],[2,"mighty",920],[3,"mighty",920]]
    },
    {
        "description": "Step 4: 물체를 잡기",
        "arm": [[1,"dynamixel",1915],[2,"dynamixel",1882],[3,"dynamixel",1200],[4,"dynamixel",3300],[5,"dynamixel",1328],[6,"dynamixel",1800]],
        "hand": [[21,"dynamixel",2300],[1,"mighty",500],[2,"mighty",260],[3,"mighty",260]]
    }
]
```

- description: 포즈 설명
- arm: 팔 액추에이터 명령 목록 [ID, actuator_type, goal_position]
- hand: 핸드 액추에이터 명령 목록 [ID, actuator_type, goal_position]

### pose/

단일 포즈(예: initial_pose.json, stretch_pose.json)를 정의합니다.

```json
{
    "description": "팔 벌리기",
    "arm": [[1, "dynamixel", 2048]],
    "hand": [[1, "mightyzap", 1200]]
}
```

## Control Tables

액추에이터별 Control Table 정보를 담은 모델 파일을 사용합니다.

- 예: control_tables/dynamixel/xm540_w270.model

## 기타

Challenges
- 적재 및 팔을 완전히 스트레치 했을 때 어꺠 축 모터(ID 5, 6)의 Over-Load 문제 존재
- 데카르트 좌표계에서 pose간 이동(motion)에 있어서 자유도 제약조건 존재