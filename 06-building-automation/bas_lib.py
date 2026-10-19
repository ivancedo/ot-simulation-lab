"""Framing helpers for the building-automation lab - pure stdlib.

BACnet/IP  : BVLC + NPDU + a minimal APDU (confirmed ReadProperty request and
             ComplexACK with a real-valued property).
KNXnet/IP  : the 6-byte KNXnet/IP header and a cEMI L_Data group-write telegram.
"""
import struct

# ---------------------------------------------------------------- BACnet/IP
BACNET_PORT = 47808
OBJ = {"analog-input": 0, "analog-output": 1, "analog-value": 2}
OBJ_REV = {v: k for k, v in OBJ.items()}


def bvlc(function, npdu):
    # 0x81 = BACnet/IP, function 0x0A unicast / 0x0B broadcast
    return struct.pack(">BBH", 0x81, function, len(npdu) + 4) + npdu


def unbvlc(data):
    if len(data) < 4 or data[0] != 0x81:
        return None
    return data[4:]


def read_request(objtype, instance, propid, invoke=1):
    objid = (objtype << 22) | instance
    npci = bytes([0x01, 0x04])                        # version, control (expecting reply)
    apdu = bytes([0x00, 0x05, invoke, 12])            # conf-req, maxresp, invoke, svc=ReadProperty
    apdu += bytes([0x0C]) + struct.pack(">I", objid)  # ctx tag 0: object id
    apdu += bytes([0x19, propid])                     # ctx tag 1: property id
    return npci + apdu


def read_ack(objtype, instance, propid, value, invoke=1):
    objid = (objtype << 22) | instance
    npci = bytes([0x01, 0x00])
    apdu = bytes([0x30, invoke, 12])                  # complex-ack, invoke, svc
    apdu += bytes([0x0C]) + struct.pack(">I", objid)
    apdu += bytes([0x19, propid])
    apdu += bytes([0x3E, 0x44]) + struct.pack(">f", value) + bytes([0x3F])  # tag3 open, real, close
    return npci + apdu


def parse_bacnet(npdu):
    apdu = npdu[2:]                                   # skip NPCI (version+control)
    pdu_type = apdu[0] & 0xF0
    if pdu_type == 0x00:                              # confirmed request
        invoke, svc = apdu[2], apdu[3]
        objid = struct.unpack(">I", apdu[5:9])[0]
        propid = apdu[10]
        return dict(kind="request", invoke=invoke, svc=svc,
                    objtype=objid >> 22, instance=objid & 0x3FFFFF, propid=propid)
    if pdu_type == 0x30:                              # complex ack
        invoke, svc = apdu[1], apdu[2]
        objid = struct.unpack(">I", apdu[4:8])[0]
        propid = apdu[9]
        value = struct.unpack(">f", apdu[12:16])[0]
        return dict(kind="ack", invoke=invoke, objtype=objid >> 22,
                    instance=objid & 0x3FFFFF, propid=propid, value=value)
    return None


# ---------------------------------------------------------------- KNXnet/IP
KNX_PORT = 3671
ROUTING_INDICATION = 0x0530
CONNECT_REQUEST = 0x0205
CONNECT_RESPONSE = 0x0206


def knx_frame(service, body):
    total = 6 + len(body)
    return struct.pack(">BBHH", 0x06, 0x10, service, total) + body


def knx_parse(data):
    if len(data) < 6 or data[0] != 0x06:
        return None
    _hl, _ver, service, total = struct.unpack(">BBHH", data[:6])
    return dict(service=service, body=data[6:total])


def cemi_group_write(src, group_addr, value):
    # cEMI: msgcode 0x29 (L_Data.ind), addil 0, ctrl1 0xBC, ctrl2 0xE0,
    #       src addr, dest group addr, npdu len, TPCI/APCI (group write) + data
    return struct.pack(">BBBBHHB", 0x29, 0x00, 0xBC, 0xE0, src, group_addr, 1) + \
        bytes([0x00, 0x80 | (value & 0x3F)])


def cemi_parse(body):
    src, group = struct.unpack(">HH", body[4:8])
    value = body[-1] & 0x3F
    return dict(src=src, group=group, value=value)
