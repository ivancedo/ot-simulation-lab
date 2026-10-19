"""Minimal DLMS/COSEM over TCP (IEC 62056 / 'green & blue book') - pure stdlib.

Uses the real DLMS 'wrapper' transport header used for Modbus-like TCP/UDP
framing (version 0x0001, source/destination wPort, length) and simplified
xDLMS APDUs: AARQ/AARE for the application association and GET-Request-Normal /
GET-Response-Normal addressing COSEM objects by class-id + OBIS + attribute.
"""
import struct

WRAPPER_VERSION = 0x0001
PORT = 4059

# A few common OBIS codes (6 octets: A B C D E F)
OBIS = {
    "energy_import":  bytes([1, 0, 1, 8, 0, 255]),   # +A total active energy (Wh)
    "power_import":   bytes([1, 0, 1, 7, 0, 255]),   # +P instantaneous (W)
    "voltage_l1":     bytes([1, 0, 32, 7, 0, 255]),  # UL1 (V)
    "current_l1":     bytes([1, 0, 31, 7, 0, 255]),  # IL1 (A)
    "disconnect":     bytes([0, 0, 96, 3, 10, 255]), # disconnect control (class 70)
}
OBIS_REV = {v: k for k, v in OBIS.items()}


# ----------------------------------------------------------------- wrapper
def wrap(src, dst, apdu):
    return struct.pack(">HHHH", WRAPPER_VERSION, src, dst, len(apdu)) + apdu


def read_wpdu(sock):
    hdr = _recvn(sock, 8)
    if not hdr:
        return None
    ver, src, dst, length = struct.unpack(">HHHH", hdr)
    apdu = _recvn(sock, length)
    return dict(src=src, dst=dst, apdu=apdu)


# -------------------------------------------------------------- association
def aarq():
    # application-context-name = LN referencing, no ciphering (abbreviated)
    return bytes([0x60, 0x1D, 0xA1, 0x09, 0x06, 0x07, 0x60, 0x85, 0x74,
                  0x05, 0x08, 0x01, 0x01])


def aare():
    return bytes([0x61, 0x1D, 0xA1, 0x09, 0x06, 0x07, 0x60, 0x85, 0x74,
                  0x05, 0x08, 0x01, 0x01, 0xA2, 0x03, 0x02, 0x01, 0x00])


# --------------------------------------------------------------- GET service
def get_request(class_id, obis, attribute=2, invoke=0x81):
    return bytes([0xC0, 0x01, invoke]) + struct.pack(">H", class_id) + obis + \
        bytes([attribute, 0x00])


def parse_get_request(apdu):
    if len(apdu) < 12 or apdu[0] != 0xC0:
        return None
    class_id = struct.unpack(">H", apdu[3:5])[0]
    obis = apdu[5:11]
    attribute = apdu[11]
    return dict(class_id=class_id, obis=obis, attribute=attribute)


def get_response(value, tag, invoke=0x81):
    data = encode(value, tag)
    return bytes([0xC4, 0x01, invoke, 0x00]) + data        # result 0x00 = data


def parse_get_response(apdu):
    if len(apdu) < 4 or apdu[0] != 0xC4:
        return None
    return decode(apdu[4:])


# --------------------------------------------------------------- ACTION service
def action_request(class_id, obis, method_id, invoke=0x81):
    # remote disconnect (method 1) / reconnect (method 2) on class 70
    return bytes([0xC3, 0x01, invoke]) + struct.pack(">H", class_id) + obis + \
        bytes([method_id, 0x00])


def parse_action_request(apdu):
    if len(apdu) < 12 or apdu[0] != 0xC3:
        return None
    return dict(class_id=struct.unpack(">H", apdu[3:5])[0],
                obis=apdu[5:11], method=apdu[11])


def action_response(invoke=0x81):
    return bytes([0xC7, 0x01, invoke, 0x00])     # action result success


# --------------------------------------------------------- A-XDR data coding
TAG_DOUBLE_LONG_U = 0x06   # uint32
TAG_LONG_U = 0x12          # uint16
TAG_UNSIGNED = 0x11        # uint8


def encode(value, tag):
    if tag == TAG_DOUBLE_LONG_U:
        return bytes([tag]) + struct.pack(">I", int(value) & 0xFFFFFFFF)
    if tag == TAG_LONG_U:
        return bytes([tag]) + struct.pack(">H", int(value) & 0xFFFF)
    return bytes([TAG_UNSIGNED, int(value) & 0xFF])


def decode(data):
    tag = data[0]
    if tag == TAG_DOUBLE_LONG_U:
        return struct.unpack(">I", data[1:5])[0]
    if tag == TAG_LONG_U:
        return struct.unpack(">H", data[1:3])[0]
    return data[1]


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
