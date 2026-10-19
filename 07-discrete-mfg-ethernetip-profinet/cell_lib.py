"""Framing for the manufacturing-cell lab - pure stdlib.

EtherNet/IP : the 24-byte encapsulation header (RegisterSession, SendRRData,
              ListIdentity) and CIP messaging (GetAttributeSingle / response)
              wrapped in the CPF item list. Explicit messaging over TCP/44818,
              implicit I/O over UDP/2222.
PROFINET    : RT cyclic frames (ethertype 0x8892, frame ID, cyclic I/O, cycle
              counter, data status) and a DCP Identify exchange, emulated over
              UDP broadcast on the sim subnet.
"""
import struct

ENIP_TCP = 44818
ENIP_UDP = 2222

# encapsulation commands
REGISTER_SESSION = 0x0065
UNREGISTER_SESSION = 0x0066
SEND_RRDATA = 0x006F
LIST_IDENTITY = 0x0063


def encap(command, session, data, status=0, context=b"\x00" * 8):
    return struct.pack("<HHII8sI", command, len(data), session, status, context, 0) + data


def read_encap(sock):
    hdr = _recvn(sock, 24)
    if not hdr:
        return None
    command, length, session, status, context, _opt = struct.unpack("<HHII8sI", hdr)
    data = _recvn(sock, length) if length else b""
    return dict(command=command, session=session, status=status, data=data or b"")


def cip_request(service, class_id, instance, attribute=None):
    path = bytes([0x20, class_id, 0x24, instance])          # 8-bit class / instance segments
    if attribute is not None:
        path += bytes([0x30, attribute])
    return bytes([service, len(path) // 2]) + path


def cip_response(service, status, data=b""):
    return bytes([service | 0x80, 0x00, status, 0x00]) + data


def send_rrdata(cip):
    # CPF: interface handle, timeout, item count=2, null addr item, unconnected data item
    cpf = struct.pack("<IH", 0, 0)
    cpf += struct.pack("<H", 2)
    cpf += struct.pack("<HH", 0x0000, 0)                     # null address item
    cpf += struct.pack("<HH", 0x00B2, len(cip)) + cip        # unconnected data item
    return cpf


def extract_cip(rrdata):
    # skip interface handle(4)+timeout(2)+count(2)+null item(4) -> data item header(4)
    off = 4 + 2 + 2 + 4
    _type, length = struct.unpack("<HH", rrdata[off:off + 4])
    return rrdata[off + 4:off + 4 + length]


# ------------------------------------------------------------------ PROFINET
PN_INPUTS = 0x8000       # device -> controller cyclic frame ID
PN_OUTPUTS = 0x8001      # controller -> device cyclic frame ID
PN_DCP_IDENT = 0xFEFE


def pn_rt(frame_id, iodata, cycle):
    status = 0x35                                            # data status: valid, run, primary
    return struct.pack(">HH", 0x8892, frame_id) + iodata + struct.pack(">HBB", cycle & 0xFFFF, status, 0x00)


def pn_parse(data):
    ether, frame_id = struct.unpack(">HH", data[:4])
    if ether != 0x8892:
        return None
    iodata = data[4:-4]
    cycle, status, _tr = struct.unpack(">HBB", data[-4:])
    return dict(frame_id=frame_id, iodata=iodata, cycle=cycle, status=status)


def _recvn(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf
