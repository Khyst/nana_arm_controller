import serial

# Protocol constants
PROTOCOL_TX_BUF_SIZE = 50
PROTOCOL_RX_BUF_SIZE = 50
MIGHTYZAP_PING = 0xF1
MIGHTYZAP_READ_DATA = 0xF2
MIGHTYZAP_WRITE_DATA = 0xF3
MIGHTYZAP_REG_WRITE = 0xF4
MIGHTYZAP_ACTION = 0xF5
MIGHTYZAP_RESET = 0xF6
MIGHTYZAP_RESTART = 0xF8
MIGHTYZAP_FACTORY_RESET = 0xF9
MIGHTYZAP_SYNC_WRITE = 0x73


class MightyZapSDK:
    """
        A small wrapper for MightyZap protocol using a provided serial handler.
    """

    def __init__(self, serial_handler):
        
        # external serial instance (pyserial Serial or compatible)
        self.ser = serial_handler

        # protocol buffers / state (instance attributes instead of globals)
        self.tx_buffer = [0] * PROTOCOL_TX_BUF_SIZE
        self.tx_buffer_index = 0
        self.rx_buffer = [0] * PROTOCOL_RX_BUF_SIZE
        self.rx_buffer_size = 0

        self.erollservice = 0
        self.erollservice_instruction = 0
        self.erollservice_id = 0x00
        self.erollservice_addr = 0x00
        self.erollservice_size = 0x00
        self.erollservice_modelnum = 0x0000

        self.actuator_id = 0
        self.checksum = 0

    # ------------------------ Low level serial protocol functions --------------------
    def setID(self, ID):
        """Set the current actuator ID for building packets."""
        self.actuator_id = int(ID) & 0xFF

    def getID(self):
        """Get the current actuator ID."""
        return self.actuator_id

    def ping(self, ID):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_PING)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def SetProtocalHeader(self):
        self.tx_buffer_index = 0
        self.tx_buffer[self.tx_buffer_index] = 0xFF
        self.tx_buffer_index += 1
        self.tx_buffer[self.tx_buffer_index] = 0xFF
        self.tx_buffer_index += 1
        self.tx_buffer[self.tx_buffer_index] = 0xFF
        self.tx_buffer_index += 1
        self.tx_buffer[self.tx_buffer_index] = self.actuator_id
        self.tx_buffer_index += 1

    def SetProtocolInstruction(self, ins):
        # preserve original behaviour: instruction starts at index 5
        self.tx_buffer_index = 5
        self.erollservice_instruction = ins
        self.tx_buffer[self.tx_buffer_index] = ins
        self.tx_buffer_index += 1

    def SetProtocollength_checksum(self):
        self.checksum = 0
        # length byte at index 4: number of parameters + instruction + checksum
        self.tx_buffer[4] = (self.tx_buffer_index - 4) & 0xFF
        start_i = 3
        for i in range(start_i, self.tx_buffer_index):
            self.checksum += int(self.tx_buffer[i])
        # checksum is one's complement of sum
        self.tx_buffer[self.tx_buffer_index] = (self.checksum & 0xFF) ^ 0xFF
        self.tx_buffer_index += 1

    def AddProtocolFactor(self, para):
        self.tx_buffer[self.tx_buffer_index] = int(para) & 0xFF
        self.tx_buffer_index += 1

    def SendPacket(self):
        # Send all bytes in one write (more efficient and correct for pyserial)
        if self.tx_buffer_index <= 0:
            return
        data = bytearray(self.tx_buffer[: self.tx_buffer_index])
        self.ser.write(data)

    def ReceivePacket(self, ID, size):
        # Wait for three 0xFF header bytes, then read remaining (size -3) bytes.
        timeout = 0
        head_count = 0

        # read header (simple loop limited by attempts)
        while head_count < 3:
            timeout += 1
            if timeout > 100:  # make timeout tolerant but finite
                # mark some bytes as zero like original behavior
                if len(self.rx_buffer) > 7:
                    self.rx_buffer[6] = 0
                    self.rx_buffer[7] = 0
                return -1

            temp = self.ser.read(1)
            if not temp:
                continue
            if temp == b"\xff":
                self.rx_buffer[head_count] = 0xFF
                head_count += 1
            else:
                self.rx_buffer[0] = 0
                head_count = 0

        # read remaining bytes (size includes header)
        to_read = size - 3
        idx = 3
        while to_read > 0:
            chunk = self.ser.read(1)
            if not chunk:
                # if serial timeout, continue until attempts exhausted
                timeout += 1
                if timeout > 100:
                    return -1
                continue
            self.rx_buffer[idx] = chunk[0]
            idx += 1
            to_read -= 1

        return 1

    def write_data(self, ID, addr, data, size):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_WRITE_DATA)
        self.AddProtocolFactor(addr)
        for i in range(0, size):
            self.AddProtocolFactor(data[i])
        self.SetProtocollength_checksum()
        self.SendPacket()

    def read_data(self, ID, addr, size):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_READ_DATA)
        self.AddProtocolFactor(addr)
        self.AddProtocolFactor(size)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def Write_Addr(self, bID,  addr,  size,  data):
        if size == 2:
            pByte=[0]*2 
            pByte[0]=(data&0x00ff)
            pByte[1]=(data//256)
            self.write_data(bID,addr,pByte,2)				
        else:
            pByte=[0]*1
            pByte[0] = data
            self.write_data(bID,addr,pByte,1)					

    def Read_Addr(self, bID, addr, size):
        if size==2 :
            self.read_data(bID,addr,2)		
            timeout = self.ReceivePacket(bID,9)
            if timeout == 1:
                return (self.rx_buffer[7] *256) + self.rx_buffer[6]
            else :
                return -1
        else :
            self.read_data(bID,addr,1)        
            timeout = self.ReceivePacket(bID,8)
            if timeout == 1:
                return self.rx_buffer[6]
            else :
                return -1

    def Write_Addr(self, bID,  addr,  size,  data):
        if size == 2:
            pByte=[0]*2 
            pByte[0]=(data&0x00ff)
            pByte[1]=(data//256)
            self.write_data(bID,addr,pByte,2)				
        else:
            pByte=[0]*1
            pByte[0] = data
            self.write_data(bID,addr,pByte,1)					

    def WritePacket(self, buff, size):
        """Write raw bytes from buff to serial (size bytes)."""
        # Use a single write call for efficiency
        self.ser.write(bytearray(buff[:size]))

    def serialtimeout(self, timeout_sec):
        """Set the serial timeout (seconds) on the underlying handler."""
        self.ser.timeout = timeout_sec

    # ------------------------ higher-level helpers ---------------------
    def ReadError(self, bID):
        self.ping(bID)
        timeout = self.ReceivePacket(bID, 7)
        if timeout == 1:
            return self.rx_buffer[5]
        else:
            return -1

    def GoalPosition(self, bID, position):
        pByte = [0] * 2
        pByte[0] = position & 0x00FF
        pByte[1] = (position >> 8) & 0xFF
        self.write_data(bID, 0x86, pByte, 2)

    def PresentPosition(self, bID):
        self.read_data(bID, 0x8C, 2)
        timeout = self.ReceivePacket(bID, 9)
        if timeout == 1:
            return (self.rx_buffer[7] * 256) + (self.rx_buffer[6])
        else:
            return -1

    def read_data_model_num(self, ID):
        """Read 2-byte model number from actuator ID."""
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_READ_DATA)
        # ask for two bytes at address 0
        self.AddProtocolFactor(0)
        self.erollservice_addr = 0
        self.AddProtocolFactor(2)
        self.erollservice_size = 2
        self.SetProtocollength_checksum()
        self.SendPacket()

    def Sync_write_data(self, addr, data, size):
        """Send a sync-write (broadcast) packet to write `size` bytes per device."""
        self.setID(0xFE)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_SYNC_WRITE)
        self.AddProtocolFactor(addr)
        for i in range(0, size):
            self.AddProtocolFactor(data[i])
        self.SetProtocollength_checksum()
        self.SendPacket()

    def reg_write(self, ID, addr, datz, size):
        """Register write (doesn't take effect until action)."""
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_REG_WRITE)
        self.AddProtocolFactor(addr)
        for i in range(0, size):
            self.AddProtocolFactor(datz[i])
        self.SetProtocollength_checksum()
        self.SendPacket()

    def action(self, ID):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_ACTION)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def reset_write(self, ID, option):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_RESET)
        self.AddProtocolFactor(option)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def Restart(self, ID):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_RESTART)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def factory_reset_write(self, ID, option):
        self.setID(ID)
        self.SetProtocalHeader()
        self.SetProtocolInstruction(MIGHTYZAP_FACTORY_RESET)
        self.AddProtocolFactor(option)
        self.SetProtocollength_checksum()
        self.SendPacket()

    def changeID(self, bID, data):
        pByte = [0] * 1
        pByte[0] = (data & 0x00FF)
        # change local actuator id for following write
        self.setID(pByte[0])
        self.write_data(bID, 0x03, pByte, 1)

    def Acceleration(self, bID, acc):
        pByte = [0] * 1
        pByte[0] = acc
        self.write_data(bID, 0x21, pByte, 1)

    def Deceleration(self, bID, acc):
        pByte = [0] * 1
        pByte[0] = acc
        self.write_data(bID, 0x22, pByte, 1)

    def ShortStrokeLimit(self, bID, SStroke):
        pByte = [0] * 2
        pByte[0] = (SStroke & 0x00FF)
        pByte[1] = (SStroke >> 8) & 0xFF
        self.write_data(bID, 0x06, pByte, 2)

    def LongStrokeLimit(self, bID, LStroke):
        pByte = [0] * 2
        pByte[0] = (LStroke & 0x00FF)
        pByte[1] = (LStroke >> 8) & 0xFF
        self.write_data(bID, 0x08, pByte, 2)

    def ForceEnable(self, bID, enable):
        pByte = [0] * 1
        pByte[0] = 1 if enable == 1 else 0
        self.write_data(bID, 0x80, pByte, 1)

    def SetShutDownEnable(self, bID, flag):
        pByte = [0] * 1
        pByte[0] = flag
        self.write_data(bID, 0x12, pByte, 1)

    def GetShutDownEnable(self, bID):
        self.read_data(bID, 0x12, 1)
        timeout = self.ReceivePacket(bID, 8)
        if timeout == 1:
            return self.rx_buffer[6]
        else:
            return -1

    def SetErrorIndicatorEnable(self, bID, flag):
        pByte = [0] * 1
        pByte[0] = flag
        self.write_data(bID, 0x11, pByte, 1)

    def GetErrorIndicatorEnable(self, bID):
        self.read_data(bID, 0x11, 1)
        timeout = self.ReceivePacket(bID, 8)
        if timeout == 1:
            return self.rx_buffer[6]
        else:
            return -1


