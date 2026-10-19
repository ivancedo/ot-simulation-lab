"""Cyclic motion-bus frame builders - pure stdlib.

Four real-time industrial-Ethernet motion protocols, each emulated as a
request/response cyclic exchange over UDP. Every frame carries the protocol's
ethertype and command/telegram identifier so captures are recognisable; the
process data is a servo PDO (target/actual position, velocity, torque).

  EtherCAT          ethertype 0x88A4, LRW datagram + working counter
  Sercos III        ethertype 0x88CD, MDT (master) / AT (drive) telegrams
  Ethernet Powerlink ethertype 0x88AB, PReq (poll request) / PRes (poll response)
  MECHATROLINK-III  command 0x34 POSING / status response
"""
import struct

PORTS = {"ethercat": 34980, "sercos": 35021, "powerlink": 3819, "mechatrolink": 35100}

# ---- EtherCAT (ethertype 0x88A4) : LRW = 0x0C -------------------------------
def ethercat_cmd(target):
    return struct.pack(">HBi", 0x88A4, 0x0C, target)                 # LRW + outputs


def ethercat_resp(actual, vel, torque, wkc):
    return struct.pack(">HBihhH", 0x88A4, 0x0C, actual, vel, torque, wkc)  # inputs + WKC


# ---- Sercos III (ethertype 0x88CD) : MDT/AT ---------------------------------
def sercos_mdt(target):
    return struct.pack(">HBi", 0x88CD, 0x01, target)                 # MDT, device control


def sercos_at(actual, vel, torque):
    return struct.pack(">HBihh", 0x88CD, 0x02, actual, vel, torque)  # AT, drive status


# ---- Ethernet Powerlink (ethertype 0x88AB) : PReq=0x03 PRes=0x04 ------------
def powerlink_preq(target):
    return struct.pack(">HBi", 0x88AB, 0x03, target)


def powerlink_pres(actual, vel, torque):
    return struct.pack(">HBihh", 0x88AB, 0x04, actual, vel, torque)


# ---- MECHATROLINK-III : POSING = 0x34 ---------------------------------------
def mechatrolink_cmd(target):
    return struct.pack(">BBi", 0x34, 0x00, target)                  # command, option, ref


def mechatrolink_resp(actual, vel, torque):
    return struct.pack(">BBihh", 0x34, 0x10, actual, vel, torque)   # cmd, status, actual


# ---- generic decoders -------------------------------------------------------
def parse_cmd(proto, data):
    if proto == "mechatrolink":
        return struct.unpack(">BBi", data[:6])[2]
    return struct.unpack(">HBi", data[:7])[2]      # 0x88xx protocols: target is last int


def parse_resp(proto, data):
    if proto == "ethercat":
        _e, _c, actual, vel, torque, wkc = struct.unpack(">HBihhH", data[:13])
    elif proto == "mechatrolink":
        _c, _s, actual, vel, torque = struct.unpack(">BBihh", data[:10])
    else:
        _e, _t, actual, vel, torque = struct.unpack(">HBihh", data[:11])
    return actual, vel, torque
