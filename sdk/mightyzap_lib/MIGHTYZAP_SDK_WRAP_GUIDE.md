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

작성중...