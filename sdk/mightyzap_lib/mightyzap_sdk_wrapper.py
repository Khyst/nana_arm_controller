import time
from .mightyzap_sdk import MightyZapSDK  # relative import within package


class MightyZapSDKWrapper:
    """
        최종 packet, port 통신을 통해 Hardware에 직접 제어하는 부분에 대한 Wrapper
    """
    
    def __init__(self, serial_handler, mighty_models, mighty_ids, mighty_params):
        """Initialize wrapper with a serial handler and create SDK instance."""
        
        self.serial_handler = serial_handler
        self.mighty_models = mighty_models
        self.mighty_ids = mighty_ids
        self.mighty_params = mighty_params

        self.mightyzap_sdk = MightyZapSDK(serial_handler)

        self._initial_setup()

        print(f"[Info] Initialized MightyZapSDK with provided serial handler")

    def _initial_setup(self):
        """
            MightyZap SDK 초기 설정을 수행하는 함수
        """
        print(f"[Info] Performing initial setup for MightyZap SDK")
        for id in self.mighty_ids:
            idx = self.mighty_ids.index(id)
            print(f"[Info] Initializing MightyZap ID {id} (Model: {self.mighty_models[idx]})")

            # Torque Enable
            self.enableTorque(id)
            
    def writePosition(self, id, position):
        """Write goal position to actuator 'id'.

        Delegates to underlying MightyZapSDK.GoalPosition.
        """
        print(f"[Info] Writing position to MightyZap ID {id}: {position}")
        self.mightyzap_sdk.GoalPosition(id, position)

    def readPosition(self, id):
        """Read present position from actuator 'id'. Returns integer position or -1 on error."""
        position = self.mightyzap_sdk.PresentPosition(id)

        print(f"[Info] Reading position from MightyZap ID {id} is {position}")
        
        return position
    
    """ Helper Function """

    def enableTorque(self, id):
        self.mightyzap_sdk.ForceEnable(id, True)

    def disableTorque(self, id):
        self.mightyzap_sdk.ForceEnable(id, False)

    def isMoving(self, id, position):
        current_position = self.readPosition(id)
        return abs(current_position - position) > 10  # Threshold for considering it still moving
        
    def reset_serial_handler(self, new_serial_handler):
        self.serial_handler = new_serial_handler
        self.mightyzap_sdk.ser = new_serial_handler
        print(f"[MightyZapSDKWrapper] Serial handler reset successfully")

    def setSafeTorqueOn(self, id):
        print(f"[Info] Initializing Safe Recovery for MightyZap ID {id}")
        
        # 1. 토크가 꺼진 상태를 확실히 보장 (이미 꺼져있어도 안전함)
        self.mightyzap_sdk.ForceEnable(id, 0)
        time.sleep(0.1)

        # 2. 현재 처진 위치를 정확히 읽어오기 (Retry 로직 유지)
        current_position = -1
        for attempt in range(5):
            current_position = self.readPosition(id)
            if current_position != -1:
                break
            print(f"[Warning] Waiting for MightyZap ID {id} sensor stable... ({attempt+1}/5)")
            time.sleep(0.2)

        if current_position == -1:
            print(f"[Critical] MightyZap ID {id} position read failed.")
            return

        # 4. 현재 위치로 이동 명령 전송 (이 명령으로 인해 자동으로 Force On 됨) [cite: 74]
        print(f"[Info] Synchronizing position to {current_position}. Force will be auto-enabled.")
        self.writePosition(id, current_position)
