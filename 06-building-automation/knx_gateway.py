"""KNXnet/IP gateway - lighting & blinds (UDP/3671).

Handles CONNECT_REQUEST (tunnelling) and ROUTING_INDICATION group-write
telegrams (cEMI L_Data), keeping the state of a few group addresses:
  1/0/1 office lighting   1/0/2 corridor lighting   2/0/1 blinds
"""
import logging
import socket
import threading

import bas_lib as b

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("knx-gw")

GROUPS = {0x0801: "office-light", 0x0802: "corridor-light", 0x1001: "blinds"}
state = {g: 0 for g in GROUPS}
lock = threading.Lock()


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", b.KNX_PORT))
    log.info("KNXnet/IP gateway online on udp/%d", b.KNX_PORT)
    while True:
        data, peer = sock.recvfrom(1500)
        f = b.knx_parse(data)
        if not f:
            continue
        if f["service"] == b.CONNECT_REQUEST:
            resp = b.knx_frame(b.CONNECT_RESPONSE, bytes([0x01, 0x00, 0x08, 0x01,
                               172, 30, 6, 11, 0x0E, 0x57, 0x04, 0x04, 0x00]))
            sock.sendto(resp, peer)
            log.info("tunnelling connection established with %s", peer[0])
        elif f["service"] == b.ROUTING_INDICATION:
            c = b.cemi_parse(f["body"])
            name = GROUPS.get(c["group"], "?")
            with lock:
                state[c["group"]] = c["value"]
            log.info("group write %s -> %s", name, "ON" if c["value"] else "OFF")


if __name__ == "__main__":
    main()
