"""IEEE 1588 PTP (Precision Time Protocol) framing - pure stdlib.

Real PTPv2 common header (34 bytes) + message bodies for Sync, Follow_Up,
Delay_Req and Delay_Resp, carried over UDP (event messages on port 319, general
messages on port 320) as PTP-over-UDP.
"""
import struct
import time

EVENT_PORT = 319
GENERAL_PORT = 320

SYNC, DELAY_REQ, FOLLOW_UP, DELAY_RESP = 0x00, 0x01, 0x08, 0x09

CLOCK_ID = b"\x00\x11\x22\xff\xfe\x33\x44\x55"


def set_clock_id(cid):
    global CLOCK_ID
    CLOCK_ID = cid


def my_port():
    return CLOCK_ID + struct.pack(">H", 1)


def now_ts():
    t = time.time()
    secs = int(t)
    nanos = int((t - secs) * 1e9)
    return secs, nanos


def _ts_bytes(secs, nanos):
    return secs.to_bytes(6, "big") + struct.pack(">I", nanos)


def _ts_parse(b):
    secs = int.from_bytes(b[:6], "big")
    nanos = struct.unpack(">I", b[6:10])[0]
    return secs + nanos / 1e9


def header(msgtype, seq, length):
    port_identity = my_port()                            # clock identity + port number
    control = {SYNC: 0, DELAY_REQ: 1, FOLLOW_UP: 2, DELAY_RESP: 3}.get(msgtype, 5)
    return struct.pack(">BBHBBHq", msgtype, 0x02, length, 0, 0, 0x0000, 0) + \
        b"\x00\x00\x00\x00" + port_identity + struct.pack(">HBB", seq, control, 0x7F)


def message(msgtype, seq, ts=None, requesting_port=None):
    body = _ts_bytes(*(ts or now_ts()))
    if requesting_port:
        body += requesting_port
    length = 34 + len(body)
    return header(msgtype, seq, length) + body


def parse(data):
    if len(data) < 34:
        return None
    msgtype = data[0] & 0x0F
    seq = struct.unpack(">H", data[30:32])[0]
    ts = _ts_parse(data[34:44]) if len(data) >= 44 else None
    return dict(msgtype=msgtype, seq=seq, ts=ts, source_port=data[20:30])
