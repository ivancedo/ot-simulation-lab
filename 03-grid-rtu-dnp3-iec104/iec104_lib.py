"""Minimal IEC 60870-5-104 - pure stdlib.

Real APCI framing (0x68 start, length, 4 control octets; I/S/U formats with the
N(S)/N(R) send/receive sequence numbers) and ASDU encoding for the common types:
  M_SP_NA_1 (1)  single-point information
  M_ME_NC_1 (13) measured value, short float
  C_SC_NA_1 (45) single command
  C_IC_NA_1 (100) interrogation command
"""
import struct

# U-format function codes (first control octet)
STARTDT_ACT, STARTDT_CON = 0x07, 0x0B
STOPDT_ACT, STOPDT_CON = 0x13, 0x23
TESTFR_ACT, TESTFR_CON = 0x43, 0x83


def u_frame(code):
    return bytes([0x68, 0x04, code, 0x00, 0x00, 0x00])


def s_frame(nr):
    return bytes([0x68, 0x04, 0x01, 0x00]) + struct.pack("<H", (nr << 1) & 0xFFFF)


def i_frame(ns, nr, asdu):
    ctrl = struct.pack("<HH", (ns << 1) & 0xFFFF, (nr << 1) & 0xFFFF)
    return bytes([0x68, len(asdu) + 4]) + ctrl + asdu


def asdu(type_id, cot, ca, objects):
    """objects: list of (ioa, payload_bytes). Non-SQ (each object carries its IOA)."""
    body = struct.pack("<BBHH", type_id, len(objects), cot, ca)
    for ioa, payload in objects:
        body += struct.pack("<I", ioa)[:3] + payload   # 3-octet IOA
    return body


def meas_float(value):
    return struct.pack("<fB", value, 0x00)              # value + QDS (good)


def single_point(on):
    return bytes([0x01 if on else 0x00])                # SIQ


def single_cmd(on):
    return bytes([0x01 if on else 0x00])                # SCO: SCS bit


def interrogation(qoi=20):
    return bytes([qoi])                                 # 20 = station interrogation


def parse(sock):
    """Read one APDU. Returns dict with kind and (for I) the decoded ASDU head."""
    hdr = _recvn(sock, 2)
    if not hdr or hdr[0] != 0x68:
        return None
    length = hdr[1]
    apdu = _recvn(sock, length)
    if apdu is None:
        return None
    c0 = apdu[0]
    if c0 & 0x01 == 0:                                   # I-format
        ns = struct.unpack("<H", apdu[0:2])[0] >> 1
        nr = struct.unpack("<H", apdu[2:4])[0] >> 1
        body = apdu[4:]
        type_id, vsq, cot, ca = struct.unpack("<BBHH", body[:6])
        return dict(kind="I", ns=ns, nr=nr, type_id=type_id, vsq=vsq & 0x7F,
                    cot=cot, ca=ca, body=body)
    if c0 & 0x03 == 0x01:                                # S-format
        nr = struct.unpack("<H", apdu[2:4])[0] >> 1
        return dict(kind="S", nr=nr)
    return dict(kind="U", code=c0)                       # U-format


def iter_objects(info):
    """Yield (ioa, payload) from a parsed I-frame dict."""
    body = info["body"]
    type_id, n = body[0], body[1] & 0x7F
    i = 6
    size = {1: 1, 13: 5, 45: 1, 100: 1}.get(type_id, 1)
    for _ in range(n):
        ioa = body[i] | body[i + 1] << 8 | body[i + 2] << 16
        payload = body[i + 3:i + 3 + size]
        yield ioa, payload
        i += 3 + size


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
