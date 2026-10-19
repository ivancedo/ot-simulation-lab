"""Minimal HART-IP (tcp/udp 5094) - pure stdlib.

Real 8-byte HART-IP header (version, message type, message id, status,
sequence number, byte count) wrapping a HART token-passing data-link PDU
(long-frame delimiter, 5-byte unique address, command, byte count, data, XOR
checksum). Implements HART command 0 (read unique identifier) and command 3
(read dynamic variables: loop current + PV/SV/TV/QV).
"""
import struct

PORT = 5094

# HART-IP message types / ids
REQUEST, RESPONSE, PUBLISH = 0, 1, 2
ID_SESSION_INIT, ID_SESSION_CLOSE, ID_KEEPALIVE, ID_PDU = 0, 1, 2, 3


def hdr(msgtype, msgid, seq, body):
    return struct.pack(">BBBBHH", 1, msgtype, msgid, 0, seq, 8 + len(body)) + body


def read_msg(sock):
    h = _recvn(sock, 8)
    if not h:
        return None
    ver, mtype, mid, status, seq, bc = struct.unpack(">BBBBHH", h)
    body = _recvn(sock, bc - 8) if bc > 8 else b""
    return dict(mtype=mtype, mid=mid, status=status, seq=seq, body=body or b"")


def _checksum(data):
    c = 0
    for b in data:
        c ^= b
    return c


def hart_pdu(address5, command, data=b"", response=False):
    delim = 0x86 if response else 0x82          # long frame STX / ACK
    frame = bytes([delim]) + address5 + bytes([command, len(data)]) + data
    return frame + bytes([_checksum(frame)])


def parse_pdu(body):
    delim = body[0]
    address5 = body[1:6]
    command = body[6]
    bc = body[7]
    data = body[8:8 + bc]
    return dict(delim=delim, address=address5, command=command, data=data)


# ----------------------------------------------------- command data encoders
def cmd0_data(mfr, dev_type, dev_id):
    # expansion + mfr id + dev type + preambles + ... (abbreviated), then device id
    return bytes([254, mfr, dev_type, 5, 7, 1, 0, 0]) + struct.pack(">I", dev_id)[1:]


def cmd3_data(current_ma, pv, sv, tv, qv):
    # response code (2) + loop current + 4 dynamic variables (unit code + float)
    out = bytes([0x00, 0x00]) + struct.pack(">f", current_ma)
    for unit, val in ((12, pv), (32, sv), (57, tv), (250, qv)):   # psi, degC, %, -
        out += bytes([unit]) + struct.pack(">f", val)
    return out


def parse_cmd3(data):
    cur = struct.unpack(">f", data[2:6])[0]
    off = 6
    dyn = []
    for _ in range(4):
        unit = data[off]
        val = struct.unpack(">f", data[off + 1:off + 5])[0]
        dyn.append((unit, val))
        off += 5
    return cur, dyn


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
