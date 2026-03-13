from .mightyzap_sdk import MightyZapSDK  # relative import within package


class MightyZapSDKWrapper:
    """
        최종 packet, port 통신을 통해 Hardware에 직접 제어하는 부분에 대한 Wrapper
    """
    
    def __init__(self, serial_handler, mighty_models, mighty_ids):
        """Initialize wrapper with a serial handler and create SDK instance."""
        
        self.serial_handler = serial_handler
        self.mighty_models = mighty_models
        self.mighty_ids = mighty_ids

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
        
