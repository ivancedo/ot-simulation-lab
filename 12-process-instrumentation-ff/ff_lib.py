"""Foundation Fieldbus HSE (High Speed Ethernet) - pure stdlib.

FF HSE carries Field Device Access (FDA) sessions over TCP/UDP 1089-1091. This
implements a simplified FDA message: a 'FF' signature, message type (function-
block parameter read/write request/response), invoke id, function-block index
and parameter id, plus a float value - enough to run function-block loops
(AI -> PID -> AO) across devices.
"""
import struct

PORTS = (1089, 1090, 1091)

READ_REQ, READ_RESP, WRITE_REQ, WRITE_RESP = 0x01, 0x02, 0x03, 0x04

# function blocks / parameters
AI_OUT = (1, 8)       # Analog Input, OUT
AO_SP = (2, 8)        # Analog Output, SP (setpoint)
AO_OUT = (2, 9)       # Analog Output, OUT (valve travel readback)


def msg(mtype, invoke, block, param, value=0.0):
    return struct.pack(">BBBBBf", 0x46, mtype, invoke, block, param, value)   # 'F' + ...


def frame(payload):
    return struct.pack(">H", len(payload)) + payload


def read_frame(sock):
    hdr = _recvn(sock, 2)
    if not hdr:
        return None
    length = struct.unpack(">H", hdr)[0]
    return _recvn(sock, length)


def parse(payload):
    _sig, mtype, invoke, block, param, value = struct.unpack(">BBBBBf", payload[:9])
    return dict(mtype=mtype, invoke=invoke, block=block, param=param, value=value)


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
