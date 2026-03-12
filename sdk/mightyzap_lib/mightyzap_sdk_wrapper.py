from .mightyzap_sdk import MightyZapSDK  # relative import within package


class MightyZapSDKWrapper:
    """
        최종 packet, port 통신을 통해 Hardware에 직접 제어하는 부분에 대한 Wrapper
    """
    
    def __init__(self, serial_handler, mighty_models):
        """Initialize wrapper with a serial handler and create SDK instance."""
        
        self.serial_handler = serial_handler
        self.mighty_models = mighty_models

        self.mightyzap_sdk = MightyZapSDK(serial_handler)

        print(f"[Info] Initialized MightyZapSDK with provided serial handler")

    def writePosition(self, id, position):
        """Write goal position to actuator 'id'.

        Delegates to underlying MightyZapSDK.GoalPosition.
        """
        print(f"[Info] Writing position to MightyZap ID {id}: {position}")
        self.mightyzap_sdk.GoalPosition(id, position)

    def readPosition(self, id):
        """Read present position from actuator 'id'. Returns integer position or -1 on error."""
        print(f"[Info] Reading position from MightyZap ID {id}")
        
        return self.mightyzap_sdk.PresentPosition(id)

        """ torque off for all MightyZap motors on close """
        
        for model in self.mighty_models:
            for id in range(1, 4): # Assuming IDs 1-3 for hand joints
                self.mightyzap_sdk.TorqueOff(id)
                print(f"[Info] Torque off for MightyZap ID {id} (Model: {model})")