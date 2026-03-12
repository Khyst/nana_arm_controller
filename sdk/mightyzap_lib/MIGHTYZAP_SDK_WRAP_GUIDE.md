# MightyZapSDK & MightyZapSDKWrapper 사용 가이드

## 파일 구조

```
sdk/mightyzap_lib/
├── mightyzap_sdk.py          # 저수준 프로토콜 드라이버 (MightyZapSDK 클래스)
├── mightyzap_sdk_wrapper.py  # 고수준 래퍼 (MightyZapSDKWrapper 클래스)
└── MIGHTYZAP_SDK_WRAP_GUIDE.md
```

---

## 1. 계층 구조

```
serial.Serial  →  MightyZapSDK  →  MightyZapSDKWrapper
   (pyserial)     (저수준 패킷)      (간편 위치 제어 API)
```

- **`MightyZapSDK`** : MightyZap 커스텀 프로토콜 패킷을 직접 조립·송수신하는 저수준 드라이버
- **`MightyZapSDKWrapper`** : 위치 읽기/쓰기를 간단하게 제공하는 고수준 API

---

## 2. MightyZap 프로토콜 개요

```
TX 패킷: 0xFF 0xFF 0xFF  [ID]  [LENGTH]  [INSTRUCTION]  [PARAMS...]  [CHECKSUM]
RX 패킷: 0xFF 0xFF 0xFF  [ID]  [LENGTH]  [ERROR]        [PARAMS...]  [CHECKSUM]
```

- **CHECKSUM** : `(ID + LENGTH + INSTRUCTION + PARAMS 합산) & 0xFF ^ 0xFF` (1의 보수)
- **버퍼 크기** : TX / RX 각 50 바이트

| 인스트럭션 상수 | 값 | 설명 |
|---|---|---|
| `MIGHTYZAP_PING` | `0xF1` | Ping |
| `MIGHTYZAP_READ_DATA` | `0xF2` | 읽기 |
| `MIGHTYZAP_WRITE_DATA` | `0xF3` | 쓰기 |
| `MIGHTYZAP_REG_WRITE` | `0xF4` | 레지스터 쓰기 (Action 대기) |
| `MIGHTYZAP_ACTION` | `0xF5` | REG_WRITE 실행 |
| `MIGHTYZAP_RESET` | `0xF6` | 리셋 |
| `MIGHTYZAP_RESTART` | `0xF8` | 재시작 |
| `MIGHTYZAP_FACTORY_RESET` | `0xF9` | 공장 초기화 |
| `MIGHTYZAP_SYNC_WRITE` | `0x73` | 동기 쓰기 (브로드캐스트) |

---

## 3. MightyZapSDK 직접 사용

### 초기화

```python
import serial
from sdk.mightyzap_lib.mightyzap_sdk import MightyZapSDK

ser = serial.Serial('/dev/ttyUSB0', baudrate=57600, timeout=0.1)
sdk = MightyZapSDK(ser)
```

> `serial.Serial` 인스턴스를 외부에서 생성해 주입합니다.

---

### 위치 제어 (가장 자주 사용)

```python
# 목표 위치 쓰기 (0 ~ 10000 범위, 내부 주소 0x86)
sdk.GoalPosition(bID=1, position=5000)

# 현재 위치 읽기 (내부 주소 0x8C) → 정수 또는 실패 시 -1
pos = sdk.PresentPosition(bID=1)
if pos != -1:
    print(f"현재 위치: {pos}")
```

---

### 오류 확인

```python
# Ping 후 Error 바이트 반환 → 0이면 정상, -1이면 타임아웃
error = sdk.ReadError(bID=1)
```

---

### 저수준 읽기 / 쓰기

```python
# 1바이트 쓰기
sdk.Write_Addr(bID=1, addr=0x80, size=1, data=1)   # Force Enable ON

# 2바이트 쓰기
sdk.Write_Addr(bID=1, addr=0x86, size=2, data=3000) # Goal Position

# 1바이트 읽기 → 값 또는 -1(타임아웃)
val = sdk.Read_Addr(bID=1, addr=0x80, size=1)

# 2바이트 읽기 → 값 또는 -1(타임아웃)
val = sdk.Read_Addr(bID=1, addr=0x8C, size=2)
```

---

### Force Enable / 스트로크 제한

```python
# Force Enable (0: OFF, 1: ON)
sdk.ForceEnable(bID=1, enable=1)

# 짧은 방향 스트로크 한계 설정
sdk.ShortStrokeLimit(bID=1, SStroke=100)

# 긴 방향 스트로크 한계 설정
sdk.LongStrokeLimit(bID=1, LStroke=9900)
```

---

### 가속 / 감속

```python
sdk.Acceleration(bID=1, acc=50)   # 가속도 설정
sdk.Deceleration(bID=1, acc=50)   # 감속도 설정
```

---

### Shutdown / Error Indicator

```python
# Shutdown Enable 설정 / 읽기
sdk.SetShutDownEnable(bID=1, flag=1)
flag = sdk.GetShutDownEnable(bID=1)

# Error Indicator Enable 설정 / 읽기
sdk.SetErrorIndicatorEnable(bID=1, flag=1)
flag = sdk.GetErrorIndicatorEnable(bID=1)
```

---

### REG_WRITE + ACTION (동시 실행)

```python
# 여러 액추에이터에 위치를 등록만 하고 (즉시 동작 안 함)
sdk.reg_write(ID=1, addr=0x86, datz=[0x88, 0x13], size=2)
sdk.reg_write(ID=2, addr=0x86, datz=[0x10, 0x27], size=2)

# 동시에 실행
sdk.action(ID=1)
sdk.action(ID=2)
```

---

### Sync Write (브로드캐스트 동시 쓰기)

```python
# 모든 연결된 액추에이터에 동일한 데이터 전송
sdk.Sync_write_data(addr=0x86, data=[0x88, 0x13], size=2)
```

---

### ID 변경 / 재시작 / 공장 초기화

```python
sdk.changeID(bID=1, data=2)             # ID 1 → 2 로 변경
sdk.Restart(ID=1)                        # 재시작
sdk.reset_write(ID=1, option=0)          # 리셋
sdk.factory_reset_write(ID=1, option=0)  # 공장 초기화
```

---

### 직렬 포트 타임아웃 변경

```python
sdk.serialtimeout(0.5)  # 500ms
```

---

## 4. MightyZapSDKWrapper 사용 (권장)

`MightyZapSDKWrapper`는 위치 읽기/쓰기를 간단한 인터페이스로 제공합니다.

### 초기화

```python
import serial
from sdk.mightyzap_lib.mightyzap_sdk_wrapper import MightyZapSDKWrapper

ser = serial.Serial('/dev/ttyUSB0', baudrate=57600, timeout=0.1)
mighty_models = ['L12-20F-4']   # 사용 모터 모델 목록 (현재 참조용)

wrapper = MightyZapSDKWrapper(ser, mighty_models)
```

---

### 위치 쓰기 / 읽기

```python
# 목표 위치 쓰기 (내부적으로 GoalPosition 호출)
wrapper.writePosition(id=1, position=5000)

# 현재 위치 읽기 → 정수 또는 -1(타임아웃)
pos = wrapper.readPosition(id=1)
if pos != -1:
    print(f"현재 위치: {pos}")
```

---

### 저수준 SDK 직접 접근

`MightyZapSDKWrapper`가 제공하지 않는 기능은 내부 `mightyzap_sdk` 인스턴스로 직접 접근합니다.

```python
# Force Enable
wrapper.mightyzap_sdk.ForceEnable(bID=1, enable=1)

# 오류 읽기
error = wrapper.mightyzap_sdk.ReadError(bID=1)

# Sync Write
wrapper.mightyzap_sdk.Sync_write_data(addr=0x86, data=[0x88, 0x13], size=2)
```

---

## 5. 주요 제어 테이블 주소 (참고)

| 주소 | 이름 | 크기 | 접근 |
|---|---|---|---|
| `0x03` | ID | 1 byte | R/W |
| `0x06` | Short Stroke Limit | 2 byte | R/W |
| `0x08` | Long Stroke Limit | 2 byte | R/W |
| `0x11` | Error Indicator Enable | 1 byte | R/W |
| `0x12` | Shutdown Enable | 1 byte | R/W |
| `0x21` | Acceleration | 1 byte | R/W |
| `0x22` | Deceleration | 1 byte | R/W |
| `0x80` | Force Enable | 1 byte | R/W |
| `0x86` | Goal Position | 2 byte | R/W |
| `0x8C` | Present Position | 2 byte | R |

---

## 6. 주의 사항

- `serial.Serial`의 `timeout`을 반드시 설정하세요. `None`(무한 대기)으로 설정하면 `ReceivePacket` 내부 루프가 블로킹됩니다. 권장값: `0.1` 초.
- `ReceivePacket`은 최대 100회 루프 후 타임아웃을 반환합니다. 반환값이 `-1`이면 통신 실패입니다.
- `Read_Addr` / `PresentPosition` 등 읽기 메서드의 반환값이 `-1`이면 타임아웃으로 수신 실패입니다.
- 동일한 `serial.Serial` 인스턴스를 여러 SDK 객체에서 공유하면 패킷 충돌이 발생합니다. 포트당 하나의 SDK 인스턴스를 사용하세요.
- `Write_Addr`는 `size=1` 또는 `size=2` 만 지원합니다. 3바이트 이상은 `write_data`를 직접 사용하세요.
