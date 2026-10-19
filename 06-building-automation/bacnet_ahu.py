"""BACnet/IP device - Air Handling Unit controller (UDP/47808).

Answers confirmed ReadProperty for present-value (85) of:
  analog-input 1  supply-air temperature (degC)
  analog-input 2  return-air temperature (degC)
  analog-output 1 cooling-coil / damper command (%)
"""
import logging
import math
import socket
import threading
import time

import bas_lib as b

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("bacnet-ahu")

state = dict(sat=14.0, rat=22.0, damper=45.0)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            state["rat"] = 22 + 1.5 * math.sin(t / 20.0)
            state["damper"] = 45 + 20 * math.sin(t / 15.0)
            state["sat"] = 14 + (state["damper"] - 45) * 0.05
        t += 1
        time.sleep(2)


def present_value(objtype, instance):
    with lock:
        if objtype == b.OBJ["analog-input"] and instance == 1:
            return state["sat"]
        if objtype == b.OBJ["analog-input"] and instance == 2:
            return state["rat"]
        if objtype == b.OBJ["analog-output"] and instance == 1:
            return state["damper"]
    return 0.0


def main():
    threading.Thread(target=physics, daemon=True).start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", b.BACNET_PORT))
    log.info("BACnet/IP AHU device 1001 online on udp/%d", b.BACNET_PORT)
    while True:
        data, peer = sock.recvfrom(1500)
        npdu = b.unbvlc(data)
        if not npdu:
            continue
        req = b.parse_bacnet(npdu)
        if req and req["kind"] == "request" and req["propid"] == 85:
            val = present_value(req["objtype"], req["instance"])
            ack = b.read_ack(req["objtype"], req["instance"], 85, val, req["invoke"])
            sock.sendto(b.bvlc(0x0A, ack), peer)


if __name__ == "__main__":
    main()
