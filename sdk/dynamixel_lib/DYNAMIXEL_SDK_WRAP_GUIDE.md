# DynamixelSDK & DynamixelSDKWrapper 사용 가이드

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

## 2. DynamixelSDK 직접 사용

### 초기화

```python
import serial
from sdk.dynamixel_lib.dynamixel_sdk import DynamixelSDK

ser = serial.Serial('/dev/ttyUSB0', baudrate=57600, timeout=0)
sdk = DynamixelSDK(ser, protocol_version=2.0)   # 1.0 또는 2.0
```

> `serial.Serial` 인스턴스를 외부에서 생성해 주입합니다.  
> `protocol_version` 기본값은 `2.0` 입니다.

---

### Ping

```python
model_number, result, error = sdk.ping(dxl_id=1)

if result == 0:  # COMM_SUCCESS
    print(f"모델 번호: {model_number}")
else:
    print(sdk.getTxRxResult(result))
    print(sdk.getRxPacketError(error))
```

---

### 읽기 (Read)

| 메서드 | 반환 타입 | 설명 |
|---|---|---|
| `read1ByteTxRx(id, addr)` | `(int, result, error)` | 1바이트 읽기 |
| `read2ByteTxRx(id, addr)` | `(int, result, error)` | 2바이트 읽기 |
| `read4ByteTxRx(id, addr)` | `(int, result, error)` | 4바이트 읽기 |
| `readTxRx(id, addr, length)` | `(list, result, error)` | 임의 길이 읽기 |

```python
# Present Position 읽기 (주소 132, 4바이트 — XM 시리즈 기준)
position, result, error = sdk.read4ByteTxRx(dxl_id=1, address=132)

if result == 0:
    print(f"현재 위치: {position}")
```

---

### 쓰기 (Write)

| 메서드 | 반환 타입 | 설명 |
|---|---|---|
| `write1ByteTxRx(id, addr, data)` | `(result, error)` | 1바이트, 응답 수신 |
| `write2ByteTxRx(id, addr, data)` | `(result, error)` | 2바이트, 응답 수신 |
| `write4ByteTxRx(id, addr, data)` | `(result, error)` | 4바이트, 응답 수신 |
| `write1ByteTxOnly(id, addr, data)` | `result` | 1바이트, 응답 무시 |
| `write2ByteTxOnly(id, addr, data)` | `result` | 2바이트, 응답 무시 |
| `write4ByteTxOnly(id, addr, data)` | `result` | 4바이트, 응답 무시 |

```python
# Torque Enable (주소 64, 1바이트)
result, error = sdk.write1ByteTxRx(dxl_id=1, address=64, data=1)

# Goal Position (주소 116, 4바이트)
result, error = sdk.write4ByteTxRx(dxl_id=1, address=116, data=2048)
```

---

### Sync Write (여러 모터 동시 쓰기)

```python
# {dxl_id: [byte0, byte1, ...]} 형식으로 전달
from sdk.dynamixel_lib.dynamixel_sdk import DXL_LOBYTE, DXL_HIBYTE, DXL_LOWORD, DXL_HIWORD

def position_to_bytes(pos: int):
    lo_word = pos & 0xFFFF
    hi_word = (pos >> 16) & 0xFFFF
    return [DXL_LOBYTE(lo_word), DXL_HIBYTE(lo_word),
            DXL_LOBYTE(hi_word), DXL_HIBYTE(hi_word)]

data_dict = {
    1: position_to_bytes(1000),
    2: position_to_bytes(2000),
    3: position_to_bytes(3000),
}

result = sdk.syncWrite(
    start_address=116,   # Goal Position 주소
    data_length=4,       # 4바이트
    data_dict=data_dict
)
```

---

### Sync Read (여러 모터 동시 읽기, Protocol 2.0 전용)

```python
data_dict, result = sdk.syncRead(
    start_address=132,          # Present Position 주소
    data_length=4,
    dxl_ids=[1, 2, 3]
)

for dxl_id, raw_bytes in data_dict.items():
    pos = raw_bytes[0] | (raw_bytes[1] << 8) | (raw_bytes[2] << 16) | (raw_bytes[3] << 24)
    print(f"ID {dxl_id} 위치: {pos}")
```

---

### Bulk Read (모터별 다른 주소 읽기, Protocol 2.0 전용)

```python
# {dxl_id: (start_address, data_length)} 형식
requests = {
    1: (132, 4),   # ID 1: Present Position (4 bytes)
    2: (146, 2),   # ID 2: Present Velocity (2 bytes)
}

data_dict, result = sdk.bulkRead(requests)
```

---

### Bulk Write (모터별 다른 주소 쓰기, Protocol 2.0 전용)

```python
# {dxl_id: (start_address, data_length, [bytes])} 형식
requests = {
    1: (116, 4, position_to_bytes(1500)),
    2: (116, 4, position_to_bytes(2500)),
}

result = sdk.bulkWrite(requests)
```

---

### 기타 명령

```python
# Reboot (Protocol 2.0 전용)
result, error = sdk.reboot(dxl_id=1)

# Factory Reset
result, error = sdk.factoryReset(dxl_id=1, option=0xFF)

# Action (REG_WRITE 후 동시 실행)
result = sdk.action(dxl_id=1)
```

---

### 결과 코드 확인

```python
result, error = sdk.write4ByteTxRx(dxl_id=1, address=116, data=2048)

if result != 0:
    print(sdk.getTxRxResult(result))   # 통신 오류 메시지

if error != 0:
    print(sdk.getRxPacketError(error)) # 장치 오류 메시지
```

| 상수 | 값 | 의미 |
|---|---|---|
| `COMM_SUCCESS` | 0 | 정상 |
| `COMM_PORT_BUSY` | -1000 | 포트 사용 중 |
| `COMM_TX_FAIL` | -1001 | 송신 실패 |
| `COMM_RX_FAIL` | -1002 | 수신 실패 |
| `COMM_RX_TIMEOUT` | -3001 | 응답 타임아웃 |
| `COMM_RX_CORRUPT` | -3002 | 패킷 손상 |
| `COMM_NOT_AVAILABLE` | -9000 | 지원하지 않는 기능 |

---

## 3. DynamixelSDKWrapper 사용 (권장)

`DynamixelSDKWrapper`는 모델 이름을 기반으로 제어 테이블을 자동 로드하여,  
주소 번호를 직접 입력하지 않고 `Goal_Position` 같은 이름으로 접근합니다.

### 초기화

```python
import serial
from sdk.dynamixel_lib.dynamixel_sdk_wrapper import DynamixelSDKWrapper

ser = serial.Serial('/dev/ttyUSB0', baudrate=57600, timeout=0)

# 사용하는 모터 모델 목록 (ID 순서와 무관, 모델 이름 목록)
dxl_models = ['xm430_w350', 'xm540_w270']

wrapper = DynamixelSDKWrapper(ser, dxl_models)
```

> `dxl_models` 에 지정한 모델의 `.model` 파일이  
> `control_tables/` 또는 `src/control_tables/` 디렉토리에 있어야 합니다.

---

### 위치 쓰기 / 읽기

```python
# 목표 위치 쓰기
wrapper.writePosition(id=1, position=2048)

# 현재 위치 읽기 → (value, result, error) 반환
value, result, error = wrapper.readPosition(id=1)
print(f"현재 위치: {value}")
```

> 내부적으로 `dynamixel_control_tables[model].address['Goal_Position']` 를 조회하여  
> `DynamixelSDK.write4ByteTxRx` / `read4ByteTxRx` 를 호출합니다.

---

### 저수준 SDK 직접 접근

`DynamixelSDKWrapper`가 제공하지 않는 기능은 내부 `dynamixel_sdk` 인스턴스로 직접 접근합니다.

```python
# Sync Write 예시
data_dict = {
    1: position_to_bytes(1000),
    2: position_to_bytes(2000),
}
addr = wrapper.dynamixel_control_tables['xm430_w350'].address['Goal_Position']
wrapper.dynamixel_sdk.syncWrite(addr, 4, data_dict)

# Ping 예시
model_number, result, error = wrapper.dynamixel_sdk.ping(dxl_id=1)
```

---

## 4. 프로토콜 버전별 지원 기능 요약

| 기능 | Protocol 1.0 | Protocol 2.0 |
|---|:---:|:---:|
| ping | ✅ | ✅ |
| read / write | ✅ | ✅ |
| syncWrite | ✅ | ✅ |
| syncRead | ❌ | ✅ |
| bulkRead | ❌ | ✅ |
| bulkWrite | ❌ | ✅ |
| reboot | ❌ | ✅ |
| factoryReset | ✅ | ✅ |

---

## 5. 주의 사항

- `serial.Serial`의 `timeout=0` (Non-blocking) 으로 설정해야 SDK 내부 타임아웃 로직이 정상 동작합니다.
- `syncRead` / `bulkRead` / `bulkWrite` 는 **Protocol 2.0 전용**입니다. Protocol 1.0에서 호출하면 `COMM_NOT_AVAILABLE(-9000)` 을 반환합니다.
- `writeTxOnly` 계열은 장치의 Status Packet 수신을 건너뜁니다. 응답 확인이 필요하면 `writeTxRx` 계열을 사용하세요.
- 동일한 `serial.Serial` 인스턴스를 여러 SDK 객체에서 공유하면 패킷 충돌이 발생할 수 있습니다. 포트당 하나의 SDK 인스턴스를 사용하세요.
