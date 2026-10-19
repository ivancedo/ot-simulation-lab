"""ICCP / TASE.2 (IEC 60870-6) over MMS - pure stdlib.

TASE.2 runs on MMS over the ISO-on-TCP stack (TPKT/COTP/ISO/MMS, tcp/102). This
uses a genuine TPKT (0x03 0x00 length) framing and simplified MMS service PDUs:
confirmed Read (A0) / ReadResponse (A1) for bilateral-table points and an
Information-Report (A3) used to deliver DSTransferSet reports.
"""
import struct

PORT = 102
READ, READ_RESP, INFO_REPORT = 0xA0, 0xA1, 0xA3


def tpkt_send(conn, payload):
    conn.sendall(struct.pack(">BBH", 0x03, 0x00, len(payload) + 4) + payload)


def tpkt_recv(conn):
    hdr = _recvn(conn, 4)
    if not hdr:
        return None
    _v, _r, length = struct.unpack(">BBH", hdr)
    return _recvn(conn, length - 4)


def read_request(name):
    n = name.encode()
    return bytes([READ, len(n)]) + n


def read_response(name, value):
    n = name.encode()
    return bytes([READ_RESP, len(n)]) + n + struct.pack(">f", value)


def info_report(name, value):
    n = name.encode()
    return bytes([INFO_REPORT, len(n)]) + n + struct.pack(">f", value)


def parse(pdu):
    tag = pdu[0]
    nlen = pdu[1]
    name = pdu[2:2 + nlen].decode(errors="ignore")
    rest = pdu[2 + nlen:]
    value = struct.unpack(">f", rest[:4])[0] if len(rest) >= 4 else None
    return dict(tag=tag, name=name, value=value)


def _recvn(conn, n):
    buf = b""
    while len(buf) < n:
        c = conn.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
