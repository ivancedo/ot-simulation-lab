"""Framing for the plant real-time controller lab - pure stdlib.

Four vendor real-time networks, each emulated over the sim subnet:
  FL-net (OPCN-2)  UDP 55000-55004, token + common-memory cyclic broadcast
  TCnet (Toshiba)  ethertype 0x888B cyclic broadcast
  EPA              ethertype 0x88BC cyclic broadcast
  Vnet/IP (Yokogawa) TCP/UDP 5313 request/response for a DCS tag
"""
import socket
import struct

BCAST = "172.30.14.255"
FLNET_PORT = 55000
TCNET_PORT = 55010
EPA_PORT = 55020
VNET_PORT = 5313


def sender():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return s


def listener(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    return s


# ---- FL-net : node no, token-holder node, common-memory word + value ---------
def flnet_pack(node, token_node, seq, value):
    return b"FLN" + struct.pack(">BBHf", node, token_node, seq, value)


def flnet_parse(data):
    if data[:3] != b"FLN":
        return None
    node, token, seq, value = struct.unpack(">BBHf", data[3:11])
    return dict(node=node, token=token, seq=seq, value=value)


# ---- TCnet : ethertype 0x888B, block number, cyclic value --------------------
def tcnet_pack(block, value):
    return struct.pack(">HBf", 0x888B, block, value)


def tcnet_parse(data):
    ether, block, value = struct.unpack(">HBf", data[:7])
    return dict(block=block, value=value) if ether == 0x888B else None


# ---- EPA : ethertype 0x88BC, cyclic value ------------------------------------
def epa_pack(channel, value):
    return struct.pack(">HBf", 0x88BC, channel, value)


def epa_parse(data):
    ether, ch, value = struct.unpack(">HBf", data[:7])
    return dict(channel=ch, value=value) if ether == 0x88BC else None


# ---- Vnet/IP : simple TCP tag read -------------------------------------------
def vnet_request(tag):
    t = tag.encode()
    return struct.pack(">H", len(t)) + t


def vnet_response(tag, value):
    t = tag.encode()
    return struct.pack(">H", len(t)) + t + struct.pack(">f", value)


def vnet_read_tcp(sock):
    hdr = _recvn(sock, 2)
    if not hdr:
        return None
    n = struct.unpack(">H", hdr)[0]
    tag = _recvn(sock, n).decode()
    return tag


def vnet_read_resp(sock):
    hdr = _recvn(sock, 2)
    n = struct.unpack(">H", hdr)[0]
    tag = _recvn(sock, n).decode()
    value = struct.unpack(">f", _recvn(sock, 4))[0]
    return tag, value


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
