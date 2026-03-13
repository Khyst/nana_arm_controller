# DynamixelSDK & DynamixelSDKWrapper 사용 가이드
- 참고 : https://emanual.robotis.com/docs/en/dxl/protocol2/

## 파일 구조

```
sdk/dynamixel_lib/
├── dynamixel_sdk.py          # 저수준 프로토콜 드라이버 (DynamixelSDK 클래스)
├── dynamixel_sdk_wrapper.py  # 고수준 래퍼 (DynamixelSDKWrapper 클래스)
└── DYNAMIXEL_SDK_WRAP_GUIDE.md
```

---

## 1. 계층 구조

```
serial.Serial  →  DynamixelSDK  →  DynamixelSDKWrapper
   (pyserial)      (저수준 패킷)      (제어 테이블 기반 API)
```

- **`DynamixelSDK`** : 프로토콜 1.0 / 2.0 패킷을 직접 조립·송수신하는 저수준 드라이버
- **`DynamixelSDKWrapper`** : 모델별 제어 테이블을 로드하여 `Goal_Position` 등의 이름으로 접근하는 고수준 API

---

## 2. Dynamixel SDK Protocol 개요

### 2.1 프로토콜 비교 (1.0 vs 2.0)

- Protocol 1.0
   - 헤더: 0xFF 0xFF
   - 체크섬: 단순 합산 기반의 체크섬 (1바이트)
   - 길이 필드: ID, Length, Instruction, Parameters, Checksum 구조
   - 일부 고급 명령(예: Bulk Read 등)을 사용할 때 제약이 있으며, 기본적인 Read/Write/SyncWrite/Action은 지원

- Protocol 2.0
   - 헤더: 0xFF 0xFF 0xFD 0x00 (확장된 프레임)
   - CRC: CRC-16-IBM (2바이트) — 신뢰성이 향상됨
   - 확장된 길이 및 파라미터 지원, Bulk Read, Sync Read 등 더 많은 기능 제공
   - 대부분 최신 Dynamixel 모델(예: XM, XH, XL-430 등)에서 Protocol 2.0 사용 권장

### 2.2 공통 패킷 구조

- Protocol 1.0 (요약)
   - [0] 0xFF
   - [1] 0xFF
   - [2] ID
   - [3] Length (Instruction + Parameters + Checksum 포함 길이)
   - [4] Instruction
   - [5..N] Parameters
   - [N+1] Checksum (1 byte)

- Protocol 2.0 (요약)
   - [0] 0xFF
   - [1] 0xFF
   - [2] 0xFD
   - [3] 0x00
   - [4] ID
   - [5..6] Length (little-endian, Parameter 길이 + Instruction 등 포함)
   - [7] Instruction
   - [8..N] Parameters
   - [N+1..N+2] CRC (2 bytes, little-endian)

### 2.3 주요 Instruction (예)

- PING: 장치 연결 확인
- READ: 특정 주소에서 데이터 읽기
- WRITE: 특정 주소에 데이터 쓰기
- REG_WRITE: 등록된 레지스터에 값을 예약(홍보) — ACTION 명령으로 동시 실행
- ACTION: 예약된 REG_WRITE 명령 실행
- REBOOT / FACTORY_RESET: 장치 재부팅/리셋
- SYNC_WRITE (1.0/2.0 모두 지원): 여러 ID에 대해 동시에 쓰기
- BULK_READ / SYNC_READ (주로 2.0): 여러 ID에서 동시에 읽기(효율적)

### 2.4 체크섬 / CRC

- Protocol 1.0: 체크섬 = ~(ID + Length + Instruction + Parameters 합) & 0xFF
- Protocol 2.0: CRC-16-IBM을 사용. 프레임의 일부(헤더 제외) 바이트들에 대해 16비트 CRC 계산을 수행

### 2.5 바이트 오더 및 데이터 크기

- Dynamixel은 대부분의 다중바이트 값(예: 2바이트, 4바이트)을 little-endian 형식으로 전송/저장