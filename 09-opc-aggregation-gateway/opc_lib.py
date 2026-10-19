"""OPC UA binary transport (UA-TCP, port 4840) - pure stdlib.

Implements the real OPC UA connection protocol message framing from Part 6:
3-byte message type (HEL/ACK/MSG/CLO/ERR), 1-byte chunk type, 4-byte LE size,
and the Hello/Acknowledge handshake bodies. On top of the transport a simplified
Read service exchanges node values (full UA binary secure channel / session
encoding is out of scope for the lab).
"""
import struct

UA_PORT = 4840


def ua_frame(mtype, body, chunk=b"F"):
    size = 8 + len(body)
    return mtype + chunk + struct.pack("<I", size) + body


def read_ua(sock):
    hdr = _recvn(sock, 8)
    if not hdr:
        return None
    mtype = hdr[:3]
    size = struct.unpack("<I", hdr[4:8])[0]
    body = _recvn(sock, size - 8) if size > 8 else b""
    return dict(mtype=mtype, body=body or b"")


def hello(endpoint):
    ep = endpoint.encode()
    return ua_frame(b"HEL", struct.pack("<IIIII", 0, 65536, 65536, 0, 0) +
                    struct.pack("<I", len(ep)) + ep)


def ack():
    return ua_frame(b"ACK", struct.pack("<IIIII", 0, 65536, 65536, 0, 0))


def read_request(node_id):
    return ua_frame(b"MSG", b"READ" + bytes([node_id]))


def read_response(node_id, value):
    return ua_frame(b"MSG", b"RESP" + bytes([node_id]) + struct.pack("<d", value))


def parse_msg(body):
    if body[:4] == b"READ":
        return dict(kind="read", node=body[4])
    if body[:4] == b"RESP":
        return dict(kind="resp", node=body[4], value=struct.unpack("<d", body[5:13])[0])
    return dict(kind="?")


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
