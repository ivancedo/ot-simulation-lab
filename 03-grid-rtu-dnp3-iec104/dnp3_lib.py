"""Minimal DNP3 (IEEE 1815) over TCP - pure stdlib.

Implements the real DNP3 data-link layer: 0x0564 start octets, length, control,
16-bit DEST/SRC, and CRC-DNP over the header and each 16-byte data block, plus
the transport header and application header (READ / RESPONSE, function codes and
IIN). The object layer is simplified: analog inputs as group 30 var 5 (32-bit
float) and binary inputs as group 1 var 2, which both sides agree on.
"""
import struct


def crc(data):
    c = 0
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xA6BC if c & 1 else c >> 1
    return (~c) & 0xFFFF


def _blocks(user):
    """Split user data into 16-byte blocks, each followed by its CRC (LE)."""
    out = b""
    for i in range(0, len(user), 16):
        blk = user[i:i + 16]
        out += blk + struct.pack("<H", crc(blk))
    return out


def build(dest, src, ctrl, user):
    hdr = struct.pack("<BBBBHH", 0x05, 0x64, len(user) + 5, ctrl, dest, src)
    return hdr + struct.pack("<H", crc(hdr)) + _blocks(user)


def parse(sock):
    """Read one DNP3 frame from a socket, return (ctrl, dest, src, user)."""
    hdr = _recvn(sock, 10)
    if not hdr:
        return None
    start0, start1, length, ctrl, dest, src = struct.unpack("<BBBBHH", hdr[:8])
    if (start0, start1) != (0x05, 0x64):
        return None
    nuser = length - 5
    user = b""
    remaining = nuser
    while remaining > 0:
        take = min(16, remaining)
        blk = _recvn(sock, take + 2)       # data + CRC
        user += blk[:take]
        remaining -= take
    return ctrl, dest, src, user


# --------------------------------------------------- application object helpers
def resp_user(iin, analogs, binaries, seq=0):
    """Build RESPONSE app fragment. analogs: list[float]; binaries: list[bool]."""
    transport = bytes([0xC0 | (seq & 0x3F)])          # FIR+FIN+seq
    app = bytes([0xC0 | (seq & 0x0F), 0x81]) + struct.pack("<H", iin)
    # group 30 var 5 analog inputs, qualifier 0x17 (1-byte count + index prefix)
    app += bytes([30, 5, 0x17, len(analogs)])
    for i, v in enumerate(analogs):
        app += bytes([i, 0x01]) + struct.pack("<f", v)   # index, flag=online, value
    # group 1 var 2 binary inputs with flags
    app += bytes([1, 2, 0x17, len(binaries)])
    for i, b in enumerate(binaries):
        app += bytes([i, 0x81 if b else 0x01])           # index, flag (bit7=state)
    return transport + app


def read_user(seq=0):
    transport = bytes([0xC0 | (seq & 0x3F)])
    app = bytes([0xC0 | (seq & 0x0F), 0x01, 60, 1, 0x06])  # READ class 0 (all static)
    return transport + app


def op_user(index, on, seq=0):
    """CROB control (group 12 var 1) DIRECT OPERATE on a binary output."""
    transport = bytes([0xC0 | (seq & 0x3F)])
    code = 0x41 if on else 0x81                            # LATCH_ON / LATCH_OFF
    app = bytes([0xC0 | (seq & 0x0F), 0x05, 12, 1, 0x17, 1, index, code])
    app += struct.pack("<BIIB", 1, 100, 100, 0)           # count, on/off time, status
    return transport + app


def parse_response(user):
    """Return (analogs, binaries) from a RESPONSE fragment built by resp_user."""
    p = user[1:]                              # strip transport header
    if len(p) < 4 or p[1] != 0x81:
        return [], []
    i = 4                                     # app ctrl, func, IIN(2)
    analogs, binaries = [], []
    while i + 3 < len(p):
        grp, var, qual, cnt = p[i], p[i + 1], p[i + 2], p[i + 3]
        i += 4
        for _ in range(cnt):
            if grp == 30 and var == 5:
                analogs.append(struct.unpack("<f", p[i + 2:i + 6])[0]); i += 6
            elif grp == 1 and var == 2:
                binaries.append(bool(p[i + 1] & 0x80)); i += 2
            else:
                return analogs, binaries
    return analogs, binaries


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
