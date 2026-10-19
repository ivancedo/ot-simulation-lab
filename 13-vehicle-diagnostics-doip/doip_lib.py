"""DoIP - Diagnostics over IP (ISO 13400, TCP/UDP 13400) - pure stdlib.

Real DoIP generic header (protocol version 0x02 + inverse, payload type, payload
length) and the common payload types: vehicle identification, routing activation
and the UDS diagnostic message / ack. UDS services are carried as the diagnostic
message payload.
"""
import struct

PORT = 13400

VEHICLE_ID_REQ = 0x0001
VEHICLE_ID_RESP = 0x0004
ROUTING_ACT_REQ = 0x0005
ROUTING_ACT_RESP = 0x0006
DIAG_MESSAGE = 0x8001
DIAG_ACK = 0x8002
DIAG_NACK = 0x8003


def header(payload_type, payload):
    return struct.pack(">BBHI", 0x02, 0xFD, payload_type, len(payload)) + payload


def read_msg(sock):
    hdr = _recvn(sock, 8)
    if not hdr:
        return None
    ver, inv, ptype, plen = struct.unpack(">BBHI", hdr)
    payload = _recvn(sock, plen) if plen else b""
    return dict(ptype=ptype, payload=payload or b"")


def vehicle_id_response(vin, logical_addr):
    return header(VEHICLE_ID_RESP, vin.encode()[:17].ljust(17, b"\x00") +
                  struct.pack(">H", logical_addr) + b"\x00" * 6 + b"\x00" * 6 + b"\x00")


def routing_activation_request(source_addr, act_type=0x00):
    return header(ROUTING_ACT_REQ, struct.pack(">HB", source_addr, act_type) + b"\x00" * 4)


def routing_activation_response(tester_addr, entity_addr, code=0x10):
    return header(ROUTING_ACT_RESP, struct.pack(">HHB", tester_addr, entity_addr, code) + b"\x00" * 4)


def diag_message(source, target, uds):
    return header(DIAG_MESSAGE, struct.pack(">HH", source, target) + uds)


def diag_ack(source, target, code=0x00):
    return header(DIAG_ACK, struct.pack(">HHB", source, target, code))


def read_msg_bytes(data):
    if len(data) < 8:
        return None
    ver, inv, ptype, plen = struct.unpack(">BBHI", data[:8])
    return dict(ptype=ptype, payload=data[8:8 + plen])


def parse_diag(payload):
    source, target = struct.unpack(">HH", payload[:4])
    return source, target, payload[4:]


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
