"""
    DO NOT REVISE ME!
"""


import time
import sys
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Internal constants  (from robotis_def.py)
# ──────────────────────────────────────────────────────────────────────────────
BROADCAST_ID = 0xFE  # 254
MAX_ID = 0xFC        # 252

# Instruction set
INST_PING          = 1
INST_READ          = 2
INST_WRITE         = 3
INST_REG_WRITE     = 4
INST_ACTION        = 5
INST_FACTORY_RESET = 6
INST_CLEAR         = 16
INST_SYNC_WRITE    = 0x83
INST_BULK_READ     = 0x92
INST_REBOOT        = 8
INST_STATUS        = 0x55
INST_SYNC_READ     = 0x82
INST_FAST_SYNC_READ = 0x8A
INST_BULK_WRITE    = 0x93
INST_FAST_BULK_READ = 0x9A

# Communication result codes
COMM_SUCCESS       =  0
COMM_PORT_BUSY     = -1000
COMM_TX_FAIL       = -1001
COMM_RX_FAIL       = -1002
COMM_TX_ERROR      = -2000
COMM_RX_WAITING    = -3000
COMM_RX_TIMEOUT    = -3001
COMM_RX_CORRUPT    = -3002
COMM_NOT_AVAILABLE = -9000

# Protocol 1 error bits
ERRBIT_VOLTAGE     = 1
ERRBIT_ANGLE       = 2
ERRBIT_OVERHEAT    = 4
ERRBIT_RANGE       = 8
ERRBIT_CHECKSUM    = 16
ERRBIT_OVERLOAD    = 32
ERRBIT_INSTRUCTION = 64

# Protocol 2 error numbers
ERRNUM_RESULT_FAIL  = 1
ERRNUM_INSTRUCTION  = 2
ERRNUM_CRC          = 3
ERRNUM_DATA_RANGE   = 4
ERRNUM_DATA_LENGTH  = 5
ERRNUM_DATA_LIMIT   = 6
ERRNUM_ACCESS       = 7
ERRBIT_ALERT        = 128

# Packet layout constants
LATENCY_TIMER = 16

# Protocol 1 packet offsets
P1_HEADER0      = 0
P1_HEADER1      = 1
P1_ID           = 2
P1_LENGTH       = 3
P1_INSTRUCTION  = 4
P1_ERROR        = 4
P1_PARAMETER0   = 5
TXPACKET_MAX_LEN_P1 = 250
RXPACKET_MAX_LEN_P1 = 250

# Protocol 2 packet offsets
P2_HEADER0      = 0
P2_HEADER1      = 1
P2_HEADER2      = 2
P2_RESERVED     = 3
P2_ID           = 4
P2_LENGTH_L     = 5
P2_LENGTH_H     = 6
P2_INSTRUCTION  = 7
P2_ERROR        = 8
P2_PARAMETER0   = 8
TXPACKET_MAX_LEN_P2 = 1024
RXPACKET_MAX_LEN_P2 = 1024


# ──────────────────────────────────────────────────────────────────────────────
# Byte-manipulation helpers  (from robotis_def.py)
# ──────────────────────────────────────────────────────────────────────────────
def DXL_MAKEWORD(a, b):  return (a & 0xFF) | ((b & 0xFF) << 8)
def DXL_MAKEDWORD(a, b): return (a & 0xFFFF) | ((b & 0xFFFF) << 16)
def DXL_LOWORD(l):       return l & 0xFFFF
def DXL_HIWORD(l):       return (l >> 16) & 0xFFFF
def DXL_LOBYTE(w):       return w & 0xFF
def DXL_HIBYTE(w):       return (w >> 8) & 0xFF


# ──────────────────────────────────────────────────────────────────────────────
# Internal serial-port adapter
#   Wraps an external pyserial Serial so it behaves like the original PortHandler
# ──────────────────────────────────────────────────────────────────────────────
class _SerialPortAdapter:
    
    """Thin adapter that makes an external serial.Serial object look like the
    original Dynamixel PortHandler (used internally by DynamixelSDK)."""

    def __init__(self, ser):
        self.ser = ser
        self.is_open = True
        self.is_using = False
        self.baudrate = ser.baudrate
        self.tx_time_per_byte = (1000.0 / ser.baudrate) * 10.0
        self.packet_start_time = 0.0
        self.packet_timeout = 0.0

    # ── port helpers ──
    def clearPort(self):
        self.ser.reset_input_buffer()

    def readPort(self, length: int) -> bytes:
        data = self.ser.read(length)
        if sys.version_info < (3, 0):
            return [ord(c) for c in data]
        return data

    def writePort(self, packet) -> int:
        return self.ser.write(bytearray(packet))

    def getBaudRate(self) -> int:
        return self.ser.baudrate

    # ── timeout helpers ──
    def setPacketTimeout(self, packet_length: int):
        self.packet_start_time = self._now()
        self.packet_timeout = (self.tx_time_per_byte * packet_length) + (LATENCY_TIMER * 2.0) + 2.0

    def setPacketTimeoutMillis(self, msec: float):
        self.packet_start_time = self._now()
        self.packet_timeout = msec

    def isPacketTimeout(self) -> bool:
        if self._elapsed() > self.packet_timeout:
            self.packet_timeout = 0
            return True
        return False

    def _now(self) -> float:
        return round(time.time() * 1_000_000_000) / 1_000_000.0

    def _elapsed(self) -> float:
        t = self._now() - self.packet_start_time
        if t < 0.0:
            self.packet_start_time = self._now()
        return t


# ──────────────────────────────────────────────────────────────────────────────
# DynamixelSDK  — main public class
# ──────────────────────────────────────────────────────────────────────────────

class DynamixelSDK:
    """Unified Dynamixel SDK.

    Accepts an external ``serial.Serial`` handler and exposes Protocol 1 / 2
    read, write, sync-read/write and bulk-read/write operations through a
    single class.

    Args:
        serial_handler: A ``serial.Serial`` instance (or compatible object).
        protocol_version: ``1.0`` or ``2.0`` (default ``2.0``).
    """

    def __init__(self, serial_handler, protocol_version: float = 2.0):
        
        self.ser = serial_handler
        self.protocol_version = protocol_version
        
        self._port = _SerialPortAdapter(serial_handler)

    # ────────────────────────────────────────────────────────────────
    # Error / result string helpers
    # ────────────────────────────────────────────────────────────────
    def getTxRxResult(self, result: int) -> str:
        table = {
            COMM_SUCCESS:       "[TxRxResult] Communication success!",
            COMM_PORT_BUSY:     "[TxRxResult] Port is in use!",
            COMM_TX_FAIL:       "[TxRxResult] Failed transmit instruction packet!",
            COMM_RX_FAIL:       "[TxRxResult] Failed get status packet from device!",
            COMM_TX_ERROR:      "[TxRxResult] Incorrect instruction packet!",
            COMM_RX_WAITING:    "[TxRxResult] Now receiving status packet!",
            COMM_RX_TIMEOUT:    "[TxRxResult] There is no status packet!",
            COMM_RX_CORRUPT:    "[TxRxResult] Incorrect status packet!",
            COMM_NOT_AVAILABLE: "[TxRxResult] Protocol does not support this function!",
        }
        return table.get(result, "")

    def getRxPacketError(self, error: int) -> str:
        if self.protocol_version == 1.0:
            return self._p1_error_str(error)
        return self._p2_error_str(error)

    def _p1_error_str(self, error: int) -> str:
        for bit, msg in [
            (ERRBIT_VOLTAGE,     "[RxPacketError] Input voltage error!"),
            (ERRBIT_ANGLE,       "[RxPacketError] Angle limit error!"),
            (ERRBIT_OVERHEAT,    "[RxPacketError] Overheat error!"),
            (ERRBIT_RANGE,       "[RxPacketError] Out of range error!"),
            (ERRBIT_CHECKSUM,    "[RxPacketError] Checksum error!"),
            (ERRBIT_OVERLOAD,    "[RxPacketError] Overload error!"),
            (ERRBIT_INSTRUCTION, "[RxPacketError] Instruction code error!"),
        ]:
            if error & bit:
                return msg
        return ""

    def _p2_error_str(self, error: int) -> str:
        if error & ERRBIT_ALERT:
            return "[RxPacketError] Hardware error occurred. Check the Hardware Error Status!"
        na = error & ~ERRBIT_ALERT
        table = {
            0:                  "",
            ERRNUM_RESULT_FAIL: "[RxPacketError] Failed to process the instruction packet!",
            ERRNUM_INSTRUCTION: "[RxPacketError] Undefined instruction or incorrect instruction!",
            ERRNUM_CRC:         "[RxPacketError] CRC doesn't match!",
            ERRNUM_DATA_RANGE:  "[RxPacketError] The data value is out of range!",
            ERRNUM_DATA_LENGTH: "[RxPacketError] The data length does not match as expected!",
            ERRNUM_DATA_LIMIT:  "[RxPacketError] The data value exceeds the limit value!",
            ERRNUM_ACCESS:      "[RxPacketError] Writing or Reading is not available to target address!",
        }
        return table.get(na, "[RxPacketError] Unknown error code!")

    # ────────────────────────────────────────────────────────────────
    # Protocol 1.0 — internal packet helpers
    # ────────────────────────────────────────────────────────────────
    def _p1_tx_packet(self, txpacket: list) -> int:
        port = self._port
        if port.is_using:
            return COMM_PORT_BUSY
        port.is_using = True

        total_len = txpacket[P1_LENGTH] + 4
        if total_len > TXPACKET_MAX_LEN_P1:
            port.is_using = False
            return COMM_TX_ERROR

        txpacket[P1_HEADER0] = 0xFF
        txpacket[P1_HEADER1] = 0xFF

        checksum = 0
        for i in range(2, total_len - 1):
            checksum += txpacket[i]
        txpacket[total_len - 1] = ~checksum & 0xFF

        port.clearPort()
        written = port.writePort(txpacket)
        if total_len != written:
            port.is_using = False
            return COMM_TX_FAIL
        return COMM_SUCCESS

    def _p1_rx_packet(self) -> Tuple[list, int]:
        port = self._port
        rxpacket: list = []
        result = COMM_TX_FAIL
        checksum = 0
        rx_length = 0
        wait_length = 6

        while True:
            rxpacket.extend(port.readPort(wait_length - rx_length))
            rx_length = len(rxpacket)
            if rx_length >= wait_length:
                for idx in range(rx_length - 1):
                    if rxpacket[idx] == 0xFF and rxpacket[idx + 1] == 0xFF:
                        break
                if idx == 0:
                    if (rxpacket[P1_ID] > 0xFD or rxpacket[P1_LENGTH] > RXPACKET_MAX_LEN_P1
                            or rxpacket[P1_ERROR] > 0x7F):
                        del rxpacket[0]
                        rx_length -= 1
                        continue
                    if wait_length != rxpacket[P1_LENGTH] + P1_LENGTH + 1:
                        wait_length = rxpacket[P1_LENGTH] + P1_LENGTH + 1
                        continue
                    if rx_length < wait_length:
                        if port.isPacketTimeout():
                            result = COMM_RX_TIMEOUT if rx_length == 0 else COMM_RX_CORRUPT
                            break
                        continue
                    checksum = 0
                    for i in range(2, wait_length - 1):
                        checksum += rxpacket[i]
                    checksum = ~checksum & 0xFF
                    result = COMM_SUCCESS if rxpacket[wait_length - 1] == checksum else COMM_RX_CORRUPT
                    break
                else:
                    del rxpacket[0:idx]
                    rx_length -= idx
            else:
                if port.isPacketTimeout():
                    result = COMM_RX_TIMEOUT if rx_length == 0 else COMM_RX_CORRUPT
                    break
        port.is_using = False
        return rxpacket, result

    def _p1_txrx_packet(self, txpacket: list) -> Tuple[Optional[list], int, int]:
        rxpacket = None
        error = 0
        result = self._p1_tx_packet(txpacket)
        if result != COMM_SUCCESS:
            return rxpacket, result, error
        if txpacket[P1_INSTRUCTION] == INST_BULK_READ:
            result = COMM_NOT_AVAILABLE
        if txpacket[P1_ID] == BROADCAST_ID:
            self._port.is_using = False
            return rxpacket, result, error
        if txpacket[P1_INSTRUCTION] == INST_READ:
            self._port.setPacketTimeout(txpacket[P1_PARAMETER0 + 1] + 6)
        else:
            self._port.setPacketTimeout(6)
        while True:
            rxpacket, result = self._p1_rx_packet()
            if result != COMM_SUCCESS or txpacket[P1_ID] == rxpacket[P1_ID]:
                break
        if result == COMM_SUCCESS and txpacket[P1_ID] == rxpacket[P1_ID]:
            error = rxpacket[P1_ERROR]
        return rxpacket, result, error

    # ────────────────────────────────────────────────────────────────
    # Protocol 2.0 — CRC / stuffing helpers
    # ────────────────────────────────────────────────────────────────
    _CRC_TABLE = [
        0x0000, 0x8005, 0x800F, 0x000A, 0x801B, 0x001E, 0x0014, 0x8011,
        0x8033, 0x0036, 0x003C, 0x8039, 0x0028, 0x802D, 0x8027, 0x0022,
        0x8063, 0x0066, 0x006C, 0x8069, 0x0078, 0x807D, 0x8077, 0x0072,
        0x0050, 0x8055, 0x805F, 0x005A, 0x804B, 0x004E, 0x0044, 0x8041,
        0x80C3, 0x00C6, 0x00CC, 0x80C9, 0x00D8, 0x80DD, 0x80D7, 0x00D2,
        0x00F0, 0x80F5, 0x80FF, 0x00FA, 0x80EB, 0x00EE, 0x00E4, 0x80E1,
        0x00A0, 0x80A5, 0x80AF, 0x00AA, 0x80BB, 0x00BE, 0x00B4, 0x80B1,
        0x8093, 0x0096, 0x009C, 0x8099, 0x0088, 0x808D, 0x8087, 0x0082,
        0x8183, 0x0186, 0x018C, 0x8189, 0x0198, 0x819D, 0x8197, 0x0192,
        0x01B0, 0x81B5, 0x81BF, 0x01BA, 0x81AB, 0x01AE, 0x01A4, 0x81A1,
        0x01E0, 0x81E5, 0x81EF, 0x01EA, 0x81FB, 0x01FE, 0x01F4, 0x81F1,
        0x81D3, 0x01D6, 0x01DC, 0x81D9, 0x01C8, 0x81CD, 0x81C7, 0x01C2,
        0x0140, 0x8145, 0x814F, 0x014A, 0x815B, 0x015E, 0x0154, 0x8151,
        0x8173, 0x0176, 0x017C, 0x8179, 0x0168, 0x816D, 0x8167, 0x0162,
        0x8123, 0x0126, 0x012C, 0x8129, 0x0138, 0x813D, 0x8137, 0x0132,
        0x0110, 0x8115, 0x811F, 0x011A, 0x810B, 0x010E, 0x0104, 0x8101,
        0x8303, 0x0306, 0x030C, 0x8309, 0x0318, 0x831D, 0x8317, 0x0312,
        0x0330, 0x8335, 0x833F, 0x033A, 0x832B, 0x032E, 0x0324, 0x8321,
        0x0360, 0x8365, 0x836F, 0x036A, 0x837B, 0x037E, 0x0374, 0x8371,
        0x8353, 0x0356, 0x035C, 0x8359, 0x0348, 0x834D, 0x8347, 0x0342,
        0x03C0, 0x83C5, 0x83CF, 0x03CA, 0x83DB, 0x03DE, 0x03D4, 0x83D1,
        0x83F3, 0x03F6, 0x03FC, 0x83F9, 0x03E8, 0x83ED, 0x83E7, 0x03E2,
        0x83A3, 0x03A6, 0x03AC, 0x83A9, 0x03B8, 0x83BD, 0x83B7, 0x03B2,
        0x0390, 0x8395, 0x839F, 0x039A, 0x838B, 0x038E, 0x0384, 0x8381,
        0x0280, 0x8285, 0x828F, 0x028A, 0x829B, 0x029E, 0x0294, 0x8291,
        0x82B3, 0x02B6, 0x02BC, 0x82B9, 0x02A8, 0x82AD, 0x82A7, 0x02A2,
        0x82E3, 0x02E6, 0x02EC, 0x82E9, 0x02F8, 0x82FD, 0x82F7, 0x02F2,
        0x02D0, 0x82D5, 0x82DF, 0x02DA, 0x82CB, 0x02CE, 0x02C4, 0x82C1,
        0x8243, 0x0246, 0x024C, 0x8249, 0x0258, 0x825D, 0x8257, 0x0252,
        0x0270, 0x8275, 0x827F, 0x027A, 0x826B, 0x026E, 0x0264, 0x8261,
        0x0220, 0x8225, 0x822F, 0x022A, 0x823B, 0x023E, 0x0234, 0x8231,
        0x8213, 0x0216, 0x021C, 0x8219, 0x0208, 0x820D, 0x8207, 0x0202,
    ]

    def _update_crc(self, crc_accum: int, data: list, size: int) -> int:
        for j in range(size):
            i = ((crc_accum >> 8) ^ data[j]) & 0xFF
            crc_accum = ((crc_accum << 8) ^ self._CRC_TABLE[i]) & 0xFFFF
        return crc_accum

    def _add_stuffing(self, packet: list) -> list:
        pkt_len_in = DXL_MAKEWORD(packet[P2_LENGTH_L], packet[P2_LENGTH_H])
        pkt_len_out = pkt_len_in
        temp = [0] * TXPACKET_MAX_LEN_P2
        temp[P2_HEADER0: P2_LENGTH_H + 1] = packet[P2_HEADER0: P2_LENGTH_H + 1]
        idx = P2_INSTRUCTION
        for i in range(pkt_len_in - 2):
            temp[idx] = packet[i + P2_INSTRUCTION]
            idx += 1
            if (packet[i + P2_INSTRUCTION] == 0xFD
                    and packet[i + P2_INSTRUCTION - 1] == 0xFF
                    and packet[i + P2_INSTRUCTION - 2] == 0xFF):
                temp[idx] = 0xFD
                idx += 1
                pkt_len_out += 1
        temp[idx] = packet[P2_INSTRUCTION + pkt_len_in - 2]
        temp[idx + 1] = packet[P2_INSTRUCTION + pkt_len_in - 1]
        idx += 2
        if pkt_len_in != pkt_len_out:
            packet = [0] * idx
        packet[0:idx] = temp[0:idx]
        packet[P2_LENGTH_L] = DXL_LOBYTE(pkt_len_out)
        packet[P2_LENGTH_H] = DXL_HIBYTE(pkt_len_out)
        return packet

    def _remove_stuffing(self, packet: list) -> list:
        pkt_len_in = DXL_MAKEWORD(packet[P2_LENGTH_L], packet[P2_LENGTH_H])
        pkt_len_out = pkt_len_in
        idx = P2_INSTRUCTION
        for i in range(pkt_len_in - 2):
            if (packet[i + P2_INSTRUCTION] == 0xFD
                    and packet[i + P2_INSTRUCTION + 1] == 0xFD
                    and packet[i + P2_INSTRUCTION - 1] == 0xFF
                    and packet[i + P2_INSTRUCTION - 2] == 0xFF):
                pkt_len_out -= 1
            else:
                packet[idx] = packet[i + P2_INSTRUCTION]
                idx += 1
        packet[idx] = packet[P2_INSTRUCTION + pkt_len_in - 2]
        packet[idx + 1] = packet[P2_INSTRUCTION + pkt_len_in - 1]
        packet[P2_LENGTH_L] = DXL_LOBYTE(pkt_len_out)
        packet[P2_LENGTH_H] = DXL_HIBYTE(pkt_len_out)
        return packet

    # ────────────────────────────────────────────────────────────────
    # Protocol 2.0 — internal packet helpers
    # ────────────────────────────────────────────────────────────────
    def _p2_tx_packet(self, txpacket: list) -> int:
        port = self._port
        if port.is_using:
            return COMM_PORT_BUSY
        port.is_using = True

        self._add_stuffing(txpacket)
        total_len = DXL_MAKEWORD(txpacket[P2_LENGTH_L], txpacket[P2_LENGTH_H]) + 7
        if total_len > TXPACKET_MAX_LEN_P2:
            port.is_using = False
            return COMM_TX_ERROR

        txpacket[P2_HEADER0] = 0xFF
        txpacket[P2_HEADER1] = 0xFF
        txpacket[P2_HEADER2] = 0xFD
        txpacket[P2_RESERVED] = 0x00

        crc = self._update_crc(0, txpacket, total_len - 2)
        txpacket[total_len - 2] = DXL_LOBYTE(crc)
        txpacket[total_len - 1] = DXL_HIBYTE(crc)

        port.clearPort()
        written = port.writePort(txpacket)
        if total_len != written:
            port.is_using = False
            return COMM_TX_FAIL
        return COMM_SUCCESS

    def _p2_rx_packet(self, fast_option: bool = False) -> Tuple[list, int]:
        port = self._port
        rxpacket: list = []
        packet_id = BROADCAST_ID if fast_option else MAX_ID
        result = COMM_TX_FAIL
        rx_length = 0
        wait_length = 11

        while True:
            rxpacket.extend(port.readPort(wait_length - rx_length))
            rx_length = len(rxpacket)
            if rx_length >= wait_length:
                for idx in range(rx_length - 3):
                    if (rxpacket[idx] == 0xFF and rxpacket[idx+1] == 0xFF
                            and rxpacket[idx+2] == 0xFD and rxpacket[idx+3] != 0xFD):
                        break
                if idx == 0:
                    if (rxpacket[P2_RESERVED] != 0x00
                            or rxpacket[P2_ID] > packet_id
                            or DXL_MAKEWORD(rxpacket[P2_LENGTH_L], rxpacket[P2_LENGTH_H]) > RXPACKET_MAX_LEN_P2
                            or rxpacket[P2_INSTRUCTION] != 0x55):
                        del rxpacket[0]
                        rx_length -= 1
                        continue
                    new_wait = DXL_MAKEWORD(rxpacket[P2_LENGTH_L], rxpacket[P2_LENGTH_H]) + P2_LENGTH_H + 1
                    if wait_length != new_wait:
                        wait_length = new_wait
                        continue
                    if rx_length < wait_length:
                        if port.isPacketTimeout():
                            result = COMM_RX_TIMEOUT if rx_length == 0 else COMM_RX_CORRUPT
                            break
                        continue
                    crc = DXL_MAKEWORD(rxpacket[wait_length - 2], rxpacket[wait_length - 1])
                    result = COMM_SUCCESS if self._update_crc(0, rxpacket, wait_length - 2) == crc else COMM_RX_CORRUPT
                    break
                else:
                    del rxpacket[0:idx]
                    rx_length -= idx
            else:
                if port.isPacketTimeout():
                    result = COMM_RX_TIMEOUT if rx_length == 0 else COMM_RX_CORRUPT
                    break

        port.is_using = False
        if result == COMM_SUCCESS and not fast_option:
            rxpacket = self._remove_stuffing(rxpacket)
        return rxpacket, result

    def _p2_txrx_packet(self, txpacket: list) -> Tuple[Optional[list], int, int]:
        rxpacket = None
        error = 0
        result = self._p2_tx_packet(txpacket)
        if result != COMM_SUCCESS:
            return rxpacket, result, error
        if txpacket[P2_INSTRUCTION] in (INST_BULK_READ, INST_SYNC_READ):
            result = COMM_NOT_AVAILABLE
        if txpacket[P2_ID] == BROADCAST_ID or txpacket[P2_INSTRUCTION] == INST_ACTION:
            self._port.is_using = False
            return rxpacket, result, error
        if txpacket[P2_INSTRUCTION] == INST_READ:
            self._port.setPacketTimeout(
                DXL_MAKEWORD(txpacket[P2_PARAMETER0 + 2], txpacket[P2_PARAMETER0 + 3]) + 11)
        else:
            self._port.setPacketTimeout(11)
        while True:
            rxpacket, result = self._p2_rx_packet(False)
            if result != COMM_SUCCESS or txpacket[P2_ID] == rxpacket[P2_ID]:
                break
        if result == COMM_SUCCESS and txpacket[P2_ID] == rxpacket[P2_ID]:
            error = rxpacket[P2_ERROR]
        return rxpacket, result, error

    # ──────────────────────── routing helper ────────────────────────
    def _txrx(self, txpacket: list) -> Tuple[Optional[list], int, int]:
        if self.protocol_version == 1.0:
            return self._p1_txrx_packet(txpacket)
        return self._p2_txrx_packet(txpacket)

    # ────────────────────────────────────────────────────────────────
    # Ping
    # ────────────────────────────────────────────────────────────────
    def ping(self, dxl_id: int) -> Tuple[int, int, int]:
        """Ping a Dynamixel and return (model_number, result, error)."""
        if self.protocol_version == 1.0:
            return self._p1_ping(dxl_id)
        return self._p2_ping(dxl_id)

    def _p1_ping(self, dxl_id):
        model_number = 0
        if dxl_id >= BROADCAST_ID:
            return model_number, COMM_NOT_AVAILABLE, 0
        txpacket = [0] * 6
        txpacket[P1_ID] = dxl_id
        txpacket[P1_LENGTH] = 2
        txpacket[P1_INSTRUCTION] = INST_PING
        rxpacket, result, error = self._p1_txrx_packet(txpacket)
        if result == COMM_SUCCESS:
            data, result, error = self.read2ByteTxRx(dxl_id, 0)
            if result == COMM_SUCCESS:
                model_number = data
        return model_number, result, error

    def _p2_ping(self, dxl_id):
        model_number = 0
        if dxl_id >= BROADCAST_ID:
            return model_number, COMM_NOT_AVAILABLE, 0
        txpacket = [0] * 10
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = 3
        txpacket[P2_LENGTH_H] = 0
        txpacket[P2_INSTRUCTION] = INST_PING
        rxpacket, result, error = self._p2_txrx_packet(txpacket)
        if result == COMM_SUCCESS:
            model_number = DXL_MAKEWORD(rxpacket[P2_PARAMETER0 + 1], rxpacket[P2_PARAMETER0 + 2])
        return model_number, result, error

    # ────────────────────────────────────────────────────────────────
    # Reboot / Factory reset / Action
    # ────────────────────────────────────────────────────────────────
    def reboot(self, dxl_id: int) -> Tuple[int, int]:
        if self.protocol_version == 1.0:
            return COMM_NOT_AVAILABLE, 0
        txpacket = [0] * 10
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = 3
        txpacket[P2_LENGTH_H] = 0
        txpacket[P2_INSTRUCTION] = INST_REBOOT
        _, result, error = self._p2_txrx_packet(txpacket)
        return result, error

    def factoryReset(self, dxl_id: int, option: int = 0) -> Tuple[int, int]:
        if self.protocol_version == 1.0:
            txpacket = [0] * 6
            txpacket[P1_ID] = dxl_id
            txpacket[P1_LENGTH] = 2
            txpacket[P1_INSTRUCTION] = INST_FACTORY_RESET
            _, result, error = self._p1_txrx_packet(txpacket)
            return result, error
        txpacket = [0] * 11
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = 4
        txpacket[P2_LENGTH_H] = 0
        txpacket[P2_INSTRUCTION] = INST_FACTORY_RESET
        txpacket[P2_PARAMETER0] = option
        _, result, error = self._p2_txrx_packet(txpacket)
        return result, error

    def action(self, dxl_id: int) -> int:
        if self.protocol_version == 1.0:
            txpacket = [0] * 6
            txpacket[P1_ID] = dxl_id
            txpacket[P1_LENGTH] = 2
            txpacket[P1_INSTRUCTION] = INST_ACTION
            _, result, _ = self._p1_txrx_packet(txpacket)
            return result
        txpacket = [0] * 10
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = 3
        txpacket[P2_LENGTH_H] = 0
        txpacket[P2_INSTRUCTION] = INST_ACTION
        _, result, _ = self._p2_txrx_packet(txpacket)
        return result

    # ────────────────────────────────────────────────────────────────
    # Read
    # ────────────────────────────────────────────────────────────────
    def readTxRx(self, dxl_id: int, address: int, length: int) -> Tuple[list, int, int]:
        """Read `length` bytes from `address`. Returns (data, result, error)."""
        if self.protocol_version == 1.0:
            return self._p1_read_txrx(dxl_id, address, length)
        return self._p2_read_txrx(dxl_id, address, length)

    def _p1_read_txrx(self, dxl_id, address, length):
        txpacket = [0] * 8
        data: list = []
        if dxl_id >= BROADCAST_ID:
            return data, COMM_NOT_AVAILABLE, 0
        txpacket[P1_ID] = dxl_id
        txpacket[P1_LENGTH] = 4
        txpacket[P1_INSTRUCTION] = INST_READ
        txpacket[P1_PARAMETER0 + 0] = address
        txpacket[P1_PARAMETER0 + 1] = length
        rxpacket, result, error = self._p1_txrx_packet(txpacket)
        if result == COMM_SUCCESS:
            error = rxpacket[P1_ERROR]
            data.extend(rxpacket[P1_PARAMETER0: P1_PARAMETER0 + length])
        return data, result, error

    def _p2_read_txrx(self, dxl_id, address, length):
        txpacket = [0] * 14
        data: list = []
        if dxl_id >= BROADCAST_ID:
            return data, COMM_NOT_AVAILABLE, 0
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = 7
        txpacket[P2_LENGTH_H] = 0
        txpacket[P2_INSTRUCTION] = INST_READ
        txpacket[P2_PARAMETER0 + 0] = DXL_LOBYTE(address)
        txpacket[P2_PARAMETER0 + 1] = DXL_HIBYTE(address)
        txpacket[P2_PARAMETER0 + 2] = DXL_LOBYTE(length)
        txpacket[P2_PARAMETER0 + 3] = DXL_HIBYTE(length)
        rxpacket, result, error = self._p2_txrx_packet(txpacket)
        if result == COMM_SUCCESS:
            error = rxpacket[P2_ERROR]
            data.extend(rxpacket[P2_PARAMETER0 + 1: P2_PARAMETER0 + 1 + length])
        return data, result, error

    def read1ByteTxRx(self, dxl_id: int, address: int) -> Tuple[int, int, int]:
        data, result, error = self.readTxRx(dxl_id, address, 1)
        return (data[0] if result == COMM_SUCCESS else 0), result, error

    def read2ByteTxRx(self, dxl_id: int, address: int) -> Tuple[int, int, int]:
        data, result, error = self.readTxRx(dxl_id, address, 2)
        v = DXL_MAKEWORD(data[0], data[1]) if result == COMM_SUCCESS else 0
        return v, result, error

    def read4ByteTxRx(self, dxl_id: int, address: int) -> Tuple[int, int, int]:
        data, result, error = self.readTxRx(dxl_id, address, 4)
        v = DXL_MAKEDWORD(DXL_MAKEWORD(data[0], data[1]), DXL_MAKEWORD(data[2], data[3])) if result == COMM_SUCCESS else 0
        return v, result, error

    # ────────────────────────────────────────────────────────────────
    # Write
    # ────────────────────────────────────────────────────────────────
    def writeTxOnly(self, dxl_id: int, address: int, length: int, data: list) -> int:
        if self.protocol_version == 1.0:
            return self._p1_write_tx_only(dxl_id, address, length, data)
        return self._p2_write_tx_only(dxl_id, address, length, data)

    def writeTxRx(self, dxl_id: int, address: int, length: int, data: list) -> Tuple[int, int]:
        if self.protocol_version == 1.0:
            return self._p1_write_txrx(dxl_id, address, length, data)
        return self._p2_write_txrx(dxl_id, address, length, data)

    def _p1_write_tx_only(self, dxl_id, address, length, data):
        txpacket = [0] * (length + 7)
        txpacket[P1_ID] = dxl_id
        txpacket[P1_LENGTH] = length + 3
        txpacket[P1_INSTRUCTION] = INST_WRITE
        txpacket[P1_PARAMETER0] = address
        txpacket[P1_PARAMETER0 + 1: P1_PARAMETER0 + 1 + length] = data[0:length]
        result = self._p1_tx_packet(txpacket)
        self._port.is_using = False
        return result

    def _p1_write_txrx(self, dxl_id, address, length, data):
        txpacket = [0] * (length + 7)
        txpacket[P1_ID] = dxl_id
        txpacket[P1_LENGTH] = length + 3
        txpacket[P1_INSTRUCTION] = INST_WRITE
        txpacket[P1_PARAMETER0] = address
        txpacket[P1_PARAMETER0 + 1: P1_PARAMETER0 + 1 + length] = data[0:length]
        _, result, error = self._p1_txrx_packet(txpacket)
        return result, error

    def _p2_write_tx_only(self, dxl_id, address, length, data):
        txpacket = [0] * (length + 12)
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = DXL_LOBYTE(length + 5)
        txpacket[P2_LENGTH_H] = DXL_HIBYTE(length + 5)
        txpacket[P2_INSTRUCTION] = INST_WRITE
        txpacket[P2_PARAMETER0 + 0] = DXL_LOBYTE(address)
        txpacket[P2_PARAMETER0 + 1] = DXL_HIBYTE(address)
        txpacket[P2_PARAMETER0 + 2: P2_PARAMETER0 + 2 + length] = data[0:length]
        result = self._p2_tx_packet(txpacket)
        self._port.is_using = False
        return result

    def _p2_write_txrx(self, dxl_id, address, length, data):
        txpacket = [0] * (length + 12)
        txpacket[P2_ID] = dxl_id
        txpacket[P2_LENGTH_L] = DXL_LOBYTE(length + 5)
        txpacket[P2_LENGTH_H] = DXL_HIBYTE(length + 5)
        txpacket[P2_INSTRUCTION] = INST_WRITE
        txpacket[P2_PARAMETER0 + 0] = DXL_LOBYTE(address)
        txpacket[P2_PARAMETER0 + 1] = DXL_HIBYTE(address)
        txpacket[P2_PARAMETER0 + 2: P2_PARAMETER0 + 2 + length] = data[0:length]
        _, result, error = self._p2_txrx_packet(txpacket)
        return result, error

    def write1ByteTxRx(self, dxl_id: int, address: int, data: int) -> Tuple[int, int]:
        return self.writeTxRx(dxl_id, address, 1, [data])

    def write2ByteTxRx(self, dxl_id: int, address: int, data: int) -> Tuple[int, int]:
        return self.writeTxRx(dxl_id, address, 2, [DXL_LOBYTE(data), DXL_HIBYTE(data)])

    def write4ByteTxRx(self, dxl_id: int, address: int, data: int) -> Tuple[int, int]:
        d = [DXL_LOBYTE(DXL_LOWORD(data)), DXL_HIBYTE(DXL_LOWORD(data)),
             DXL_LOBYTE(DXL_HIWORD(data)), DXL_HIBYTE(DXL_HIWORD(data))]
        return self.writeTxRx(dxl_id, address, 4, d)

    def write1ByteTxOnly(self, dxl_id: int, address: int, data: int) -> int:
        return self.writeTxOnly(dxl_id, address, 1, [data])

    def write2ByteTxOnly(self, dxl_id: int, address: int, data: int) -> int:
        return self.writeTxOnly(dxl_id, address, 2, [DXL_LOBYTE(data), DXL_HIBYTE(data)])

    def write4ByteTxOnly(self, dxl_id: int, address: int, data: int) -> int:
        d = [DXL_LOBYTE(DXL_LOWORD(data)), DXL_HIBYTE(DXL_LOWORD(data)),
             DXL_LOBYTE(DXL_HIWORD(data)), DXL_HIBYTE(DXL_HIWORD(data))]
        
        return self.writeTxOnly(dxl_id, address, 4, d)

    # ────────────────────────────────────────────────────────────────
    # Sync Write
    # ────────────────────────────────────────────────────────────────
    def syncWrite(self, start_address: int, data_length: int,
                  data_dict: Dict[int, List[int]]) -> int:
        """Sync-write to multiple Dynamixels at once.

        Args:
            start_address: Control table start address.
            data_length: Number of bytes per device.
            data_dict: ``{dxl_id: [byte0, byte1, ...], ...}``

        Returns:
            Communication result code.
        """
        if not data_dict:
            return COMM_NOT_AVAILABLE

        param: list = []
        if self.protocol_version == 1.0:
            for dxl_id, d in data_dict.items():
                param.append(dxl_id)
                param.extend(d)
            param_length = len(param)
            txpacket = [0] * (param_length + 8)
            txpacket[P1_ID] = BROADCAST_ID
            txpacket[P1_LENGTH] = param_length + 4
            txpacket[P1_INSTRUCTION] = INST_SYNC_WRITE
            txpacket[P1_PARAMETER0 + 0] = start_address
            txpacket[P1_PARAMETER0 + 1] = data_length
            txpacket[P1_PARAMETER0 + 2: P1_PARAMETER0 + 2 + param_length] = param[0:param_length]
            _, result, _ = self._p1_txrx_packet(txpacket)
            return result
        else:
            for dxl_id, d in data_dict.items():
                param.append(dxl_id)
                param.extend(d)
            param_length = len(param)
            txpacket = [0] * (param_length + 14)
            txpacket[P2_ID] = BROADCAST_ID
            txpacket[P2_LENGTH_L] = DXL_LOBYTE(param_length + 7)
            txpacket[P2_LENGTH_H] = DXL_HIBYTE(param_length + 7)
            txpacket[P2_INSTRUCTION] = INST_SYNC_WRITE
            txpacket[P2_PARAMETER0 + 0] = DXL_LOBYTE(start_address)
            txpacket[P2_PARAMETER0 + 1] = DXL_HIBYTE(start_address)
            txpacket[P2_PARAMETER0 + 2] = DXL_LOBYTE(data_length)
            txpacket[P2_PARAMETER0 + 3] = DXL_HIBYTE(data_length)
            txpacket[P2_PARAMETER0 + 4: P2_PARAMETER0 + 4 + param_length] = param[0:param_length]
            _, result, _ = self._p2_txrx_packet(txpacket)
            return result

    # ────────────────────────────────────────────────────────────────
    # Sync Read  (Protocol 2.0 only)
    # ────────────────────────────────────────────────────────────────
    def syncRead(self, start_address: int, data_length: int,
                 dxl_ids: List[int]) -> Tuple[Dict[int, list], int]:
        """Sync-read from multiple Dynamixels.

        Returns:
            ``(data_dict, result)`` where ``data_dict`` maps each ID to its
            raw byte list. Protocol 1.0 returns ``({}, COMM_NOT_AVAILABLE)``.
        """
        if self.protocol_version == 1.0:
            return {}, COMM_NOT_AVAILABLE
        if not dxl_ids:
            return {}, COMM_NOT_AVAILABLE

        param = list(dxl_ids)
        param_length = len(param)
        txpacket = [0] * (param_length + 14)
        txpacket[P2_ID] = BROADCAST_ID
        txpacket[P2_LENGTH_L] = DXL_LOBYTE(param_length + 7)
        txpacket[P2_LENGTH_H] = DXL_HIBYTE(param_length + 7)
        txpacket[P2_INSTRUCTION] = INST_SYNC_READ
        txpacket[P2_PARAMETER0 + 0] = DXL_LOBYTE(start_address)
        txpacket[P2_PARAMETER0 + 1] = DXL_HIBYTE(start_address)
        txpacket[P2_PARAMETER0 + 2] = DXL_LOBYTE(data_length)
        txpacket[P2_PARAMETER0 + 3] = DXL_HIBYTE(data_length)
        txpacket[P2_PARAMETER0 + 4: P2_PARAMETER0 + 4 + param_length] = param[0:param_length]

        result = self._p2_tx_packet(txpacket)
        if result != COMM_SUCCESS:
            return {}, result

        self._port.setPacketTimeout((11 + data_length) * param_length)

        data_dict: Dict[int, list] = {}
        overall = COMM_SUCCESS
        for dxl_id in dxl_ids:
            rxpacket = None
            while True:
                rxpacket, res = self._p2_rx_packet(False)
                if res != COMM_SUCCESS or rxpacket[P2_ID] == dxl_id:
                    break
            if res == COMM_SUCCESS and rxpacket[P2_ID] == dxl_id:
                data_dict[dxl_id] = list(rxpacket[P2_PARAMETER0 + 1: P2_PARAMETER0 + 1 + data_length])
            else:
                overall = res
        return data_dict, overall

    # ────────────────────────────────────────────────────────────────
    # Bulk Read  (Protocol 2.0 only)
    # ────────────────────────────────────────────────────────────────
    def bulkRead(self, requests: Dict[int, Tuple[int, int]]) -> Tuple[Dict[int, list], int]:
        """Bulk-read from multiple Dynamixels with different addresses/lengths.

        Args:
            requests: ``{dxl_id: (start_address, data_length), ...}``

        Returns:
            ``(data_dict, result)`` — same key structure as `requests`.
        """
        if self.protocol_version == 1.0:
            return {}, COMM_NOT_AVAILABLE
        if not requests:
            return {}, COMM_NOT_AVAILABLE

        param: list = []
        for dxl_id, (addr, length) in requests.items():
            param.extend([dxl_id,
                          DXL_LOBYTE(addr), DXL_HIBYTE(addr),
                          DXL_LOBYTE(length), DXL_HIBYTE(length)])
        param_length = len(param)

        txpacket = [0] * (param_length + 10)
        txpacket[P2_ID] = BROADCAST_ID
        txpacket[P2_LENGTH_L] = DXL_LOBYTE(param_length + 3)
        txpacket[P2_LENGTH_H] = DXL_HIBYTE(param_length + 3)
        txpacket[P2_INSTRUCTION] = INST_BULK_READ
        txpacket[P2_PARAMETER0: P2_PARAMETER0 + param_length] = param[0:param_length]

        result = self._p2_tx_packet(txpacket)
        if result != COMM_SUCCESS:
            return {}, result

        wait_length = sum(length + 10 for _, (_, length) in requests.items())
        self._port.setPacketTimeout(wait_length)

        data_dict: Dict[int, list] = {}
        overall = COMM_SUCCESS
        for dxl_id, (_, length) in requests.items():
            rxpacket = None
            while True:
                rxpacket, res = self._p2_rx_packet(False)
                if res != COMM_SUCCESS or rxpacket[P2_ID] == dxl_id:
                    break
            if res == COMM_SUCCESS and rxpacket[P2_ID] == dxl_id:
                data_dict[dxl_id] = list(rxpacket[P2_PARAMETER0 + 1: P2_PARAMETER0 + 1 + length])
            else:
                overall = res
        return data_dict, overall

    # ────────────────────────────────────────────────────────────────
    # Bulk Write  (Protocol 2.0 only)
    # ────────────────────────────────────────────────────────────────
    def bulkWrite(self, requests: Dict[int, Tuple[int, int, List[int]]]) -> int:
        """Bulk-write to multiple Dynamixels with different addresses/lengths.

        Args:
            requests: ``{dxl_id: (start_address, data_length, [bytes]), ...}``

        Returns:
            Communication result code.
        """
        if self.protocol_version == 1.0:
            return COMM_NOT_AVAILABLE
        if not requests:
            return COMM_NOT_AVAILABLE

        param: list = []
        for dxl_id, (addr, length, data) in requests.items():
            param.extend([dxl_id,
                          DXL_LOBYTE(addr), DXL_HIBYTE(addr),
                          DXL_LOBYTE(length), DXL_HIBYTE(length)])
            param.extend(data[0:length])
        param_length = len(param)

        txpacket = [0] * (param_length + 10)
        txpacket[P2_ID] = BROADCAST_ID
        txpacket[P2_LENGTH_L] = DXL_LOBYTE(param_length + 3)
        txpacket[P2_LENGTH_H] = DXL_HIBYTE(param_length + 3)
        txpacket[P2_INSTRUCTION] = INST_BULK_WRITE
        txpacket[P2_PARAMETER0: P2_PARAMETER0 + param_length] = param[0:param_length]

        _, result, _ = self._p2_txrx_packet(txpacket)
        return result
