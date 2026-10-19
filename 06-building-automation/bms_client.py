"""Building Management System workstation.

Supervises the building across four protocols:
  * BACnet/IP  - ReadProperty the AHU supply/return temps and damper
  * KNXnet/IP  - connect + group-write the lighting and blinds on a schedule
  * LonTalk    - poll the VAV network variables
  * Fox        - receive the Niagara station point stream
"""
import logging
import socket
import struct
import threading
import time

import bas_lib as b

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("bms")

AHU = "172.30.6.10"
KNX = "172.30.6.11"
LON = "172.30.6.12"
FOX = "172.30.6.13"


def bacnet_read(sock, objtype, instance, invoke):
    sock.sendto(b.bvlc(0x0A, b.read_request(objtype, instance, 85, invoke)), (AHU, b.BACNET_PORT))
    try:
        data, _ = sock.recvfrom(1500)
        return b.parse_bacnet(b.unbvlc(data))["value"]
    except (socket.timeout, TypeError):
        return None


def fox_listener():
    while True:
        try:
            s = socket.create_connection((FOX, 1911), timeout=3)
            hello = s.recv(512)
            if b"fox hello" in hello:
                log.info("Fox: connected to Niagara station")
            s.sendall(b"fox a 1 -1 fox subscribe\n{\n}\n;;\n")
            while True:
                data = s.recv(512)
                if not data:
                    break
                try:
                    if b"chilledWaterTemp" in data:
                        txt = data.decode(errors="ignore")
                        chw = txt.split("chilledWaterTemp=f:")[1].split("\n")[0]
                        occ = "occupancy=b:true" in txt
                        log.info("Fox: chilledWater=%s degC  occupancy=%s", chw, occ)
                except (IndexError, ValueError):
                    continue
        except OSError:
            time.sleep(2)


def lon_poll():
    try:
        s = socket.create_connection((LON, 1628), timeout=3)
        vals = []
        for idx in range(3):
            s.sendall(bytes([0x73, idx]))
            r = s.recv(8)
            vals.append(struct.unpack(">f", r[2:6])[0])
        s.close()
        return vals
    except OSError:
        return None


def main():
    bac = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bac.settimeout(2.0)
    knx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    knx.sendto(b.knx_frame(b.CONNECT_REQUEST, bytes([0x08, 0x01, 172, 30, 6, 20, 0x0E, 0x57])),
               (KNX, b.KNX_PORT))

    threading.Thread(target=fox_listener, daemon=True).start()
    log.info("BMS workstation online - supervising BACnet / KNX / LON / Fox")

    invoke, tick = 1, 0
    while True:
        sat = bacnet_read(bac, b.OBJ["analog-input"], 1, invoke); invoke += 1
        rat = bacnet_read(bac, b.OBJ["analog-input"], 2, invoke); invoke += 1
        dmp = bacnet_read(bac, b.OBJ["analog-output"], 1, invoke); invoke += 1
        if sat is not None:
            log.info("BACnet AHU: supply=%.1f degC  return=%.1f degC  damper=%.0f%%", sat, rat, dmp)

        vav = lon_poll()
        if vav:
            log.info("LON VAV: space=%.1f degC  flow=%.0f L/s  damper=%.0f%%", vav[0], vav[1], vav[2])

        # drive the KNX lighting/blinds on a slow schedule
        on = (tick // 2) % 2
        for group in (0x0801, 0x0802, 0x1001):
            knx.sendto(b.knx_frame(b.ROUTING_INDICATION, b.cemi_group_write(0x1114, group, on)),
                       (KNX, b.KNX_PORT))
        tick += 1
        time.sleep(5)


if __name__ == "__main__":
    main()
