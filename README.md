# Robot Arm with Hand Controller
---
Dynamixel과 MightyZap Actuator로 이루어진 Robot Arm의 제어를 하는 High-level to Low-level Control 패키지

## Features
---
- 하나의 serial 포트에 대한 통신으로 여러 종류의 액추에이터 하드웨어 인터페이스를 사용하도록 하는 통일된 인터페이스 역할
- High-Level (인간 친화적인) 명령을 통해 Low-Level (하드웨어 제어 친화적인) 명령까지 전달하는 플로우로 구성

## Prerequisites
---
pyserial
pyyaml

## Installation
---
git clone https://github.com/khyst/nana_arm_controller.git

### Script 파일별 설명
```Python
    python3 nana_arm_controller.py # High Level 단에서 팔의 제어를 하도록 하는 Application 실행

    # nana_arm_wrapper.py # 실제 로봇 팔에 연결된 여러 하드웨어를 통일된 인터페이스로 관리하기 위한 Wrapper Application
    # dynamixel
    # - dynamixel_lib/dynamixel_wrapper.py # Dynamixel 프로토콜을 통한 저수준 제어를, 특정 기능 단위로 묶기 위한 Wrapper
    # - dynamixel_lib/dynamixel_sdk.py # Dynamixel 프로토콜을 통한 저수준 제어 SDK
    # - dxl_model_parser.py # Dynamixel 액추에이터 별 상이한 Control Table 로드 (Address, Instrunction Byte 등등)

    # mightyzap
    # - mightyzap_lib/mightyzap_wrapper.py # MightyZap 프로토콜을 통한 저수준 제어를, 특정 기능 단위로 묶기 위한 Wrapper
    # - mightyzap_lib/mightyzap_sdk.py # MightyZap 프로토콜을 통한 주수준 제어 SDK

```

### config
- 로봇 암 및 그리퍼 하드웨어의 전반적인 통신 설정과 액추에이터 사양을 정의하는 메인 설정 파일
  - Common Settings
    - port : 장치 연결 경로 (ex: /dev/ttyUSB0)
    - baudrate: 통신 속도 (Default: 115200)

  - DXL (Dynamixel) Configuration
    - number_of_dxl : 연결된 Dynamixel 액추에이터 총 갯수 (현재 7개)
    - dxl_ids / dxl_names : 각 조인트별 ID와 매핑된 이름(joint 1~6, hand_joint)
    - dxl_models : 각 ID에 해당하는 Dynamixel 액추에이터 모델명 (XM540_W270 등)
    - limits : 각 조인트의 하드웨어/소프트웨어 위치 제한 값(max, min) 설정

  = Mighty (MightyZap) Configuration
    - number_of_mighty : 연결된 MightyZap 액추에이터 총 갯수 (현재 3개)
    - mighty_ids / mighty_names : 그리퍼 조인트 ID 및 이름 (gripper_joint1~3)
    - mighty_models : 사용 중인 MightyZap 액추에이터 모델 명 (D12-12F-3)
    - limits : 각 액추에이터의 스트로크 제한을 위한 하드웨어 및 소프트웨어 위치 제한 값 설정

### json
- motion/
    - 로봇 팔이 수행해야 할 모션에 대한 Pose sequence(ex.pick_cup_motion.json)를 정의하는 폴더. 추후, 이를 통해 실제 로봇의 실시간 제어가 이루어짐.

- <motion>.json 정의 방법
    ```json
        [
            {
                "description": "팔 벌리기", // 각 포즈에 대한 설명
                "arm": [...], // 각 포즈에 대해 팔에 포함되는 액추에이터 값들 정의 [ [Id, Actuator type, Goal position ], ... ]
                "hand": [...] // 각 포즈에 대해 핸드에 포함되는 액추에이터 값들 정의 [ [Id, Actuator type, Goal position ], ... ]
            },
            ... // 반복
        ]
    ```


- pose/
    - 로봇 팔이 움직여야 할 포즈에 대한 Pose(ex.initial_pose.json, stretch_pose.json)를 정의하는 폴더, 추후 이 포즈로 로봇의 실시간 제어가 이루어짐
    ```json
        {
            "description": "팔 벌리기", // 각 포즈에 대한 설명
            "arm": [...], // 각 포즈에 대해 팔에 포함되는 액추에이터 값들 정의 [ [Id, Actuator type, Goal position ], ... ]
            "hand": [...] // 각 포즈에 대해 핸드에 포함되는 액추에이터 값들 정의 [ [Id, Actuator type, Goal position ], ... ]
        },
    ```

### control_tables
- 각 액추에이터 별 상이한 Control Table 정보를 포함하는 파일을 로드 (ex. control_tables/dynamixel/xm540_w270.model)


### E.T.C. 
- command/ (Deprecated, 현재 사용 안함)