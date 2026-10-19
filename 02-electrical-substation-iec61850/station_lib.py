"""Shared transport + framing helpers for the IEC 61850 substation lab.

GOOSE (0x88B8), GSSE (0x88B9) and Sampled Values (0x88BA) are layer-2
publisher/subscriber protocols. Containers on one Docker bridge share an L2
segment, so here they are emulated as UDP broadcast on the sim subnet - the
frames carry the real ethertype, APPID and the state/sample counters that
IEC 61850 IEDs and IDS tools key on.

MMS (ISO-on-TCP, port 102) is framed with a genuine TPKT + COTP data header.
"""
import socket
import struct

BCAST = "172.30.2.255"
GOOSE_PORT = 10200
SV_PORT = 10201
GSSE_PORT = 10202


# ---------------------------------------------------------------- UDP pub/sub
def sender():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return s


def listener(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    return s


def publish(sock, port, payload):
    sock.sendto(payload, (BCAST, port))


# -------------------------------------------------------------------- GOOSE
def goose_pack(goid, stnum, sqnum, ttl_ms, test, bools):
    gid = goid.encode()
    body = struct.pack(">IIIB", stnum, sqnum, ttl_ms, 1 if test else 0)
    body += bytes([len(bools)]) + bytes(1 if b else 0 for b in bools)
    return struct.pack(">HHB", 0x88B8, 0x0001, len(gid)) + gid + body


def goose_unpack(data):
    _ether, _appid, glen = struct.unpack(">HHB", data[:5])
    goid = data[5:5 + glen].decode()
    off = 5 + glen
    stnum, sqnum, ttl, test = struct.unpack(">IIIB", data[off:off + 13])
    n = data[off + 13]
    bools = [bool(b) for b in data[off + 14:off + 14 + n]]
    return dict(goid=goid, stnum=stnum, sqnum=sqnum, ttl=ttl, test=test, bools=bools)


# ---------------------------------------------------------- Sampled Values
def sv_pack(svid, smpcnt, channels):
    sid = svid.encode()
    body = struct.pack(">HB", smpcnt, len(channels))
    body += struct.pack(">%di" % len(channels), *[int(c) for c in channels])
    return struct.pack(">HHB", 0x88BA, 0x4000, len(sid)) + sid + body


def sv_unpack(data):
    _e, _a, sl = struct.unpack(">HHB", data[:5])
    svid = data[5:5 + sl].decode()
    off = 5 + sl
    smpcnt, n = struct.unpack(">HB", data[off:off + 3])
    ch = struct.unpack(">%di" % n, data[off + 3:off + 3 + n * 4])
    return dict(svid=svid, smpcnt=smpcnt, channels=list(ch))


# --------------------------------------------------------------------- GSSE
def gsse_pack(stnum, status_bits):
    return struct.pack(">HIH", 0x88B9, stnum, status_bits)


def gsse_unpack(data):
    _e, stnum, bits = struct.unpack(">HIH", data[:8])
    return dict(stnum=stnum, bits=bits)


# ------------------------------------------------- MMS over ISO-on-TCP (TPKT)
def tpkt_send(conn, payload):
    conn.sendall(struct.pack(">BBH", 0x03, 0x00, len(payload) + 4) + payload)


def tpkt_recv(conn):
    hdr = _recvn(conn, 4)
    if not hdr:
        return None
    _v, _r, length = struct.unpack(">BBH", hdr)
    return _recvn(conn, length - 4)


def _recvn(conn, n):
    buf = b""
    while len(buf) < n:
        c = conn.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
