"""PROFINET IO-controller - cell PLC driving the robot.

Sends a DCP Identify-All at startup, then runs the RT cyclic exchange: produces
the output frame (target pose + gripper command) and consumes the device input
frame, sequencing a pick -> place -> home robot cycle.
"""
import logging
import socket
import threading
import time

import cell_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("pn-controller")

BCAST, PORT = "172.30.7.255", 34962
pos = [0]
gripper = [0]


def rx_loop(sock):
    while True:
        data, _ = sock.recvfrom(256)
        f = c.pn_parse(data)
        if not f:
            continue
        if f["frame_id"] == c.PN_INPUTS:
            pos[0], gripper[0] = f["iodata"][0], f["iodata"][1]
        elif f["frame_id"] == c.PN_DCP_IDENT and len(f["iodata"]) > 2:
            log.info("DCP Identify response: station '%s'", f["iodata"][2:].decode(errors="ignore"))


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))
    threading.Thread(target=rx_loop, args=(sock,), daemon=True).start()

    time.sleep(1)
    sock.sendto(c.pn_rt(c.PN_DCP_IDENT, b"", 0), (BCAST, PORT))     # DCP Identify-All
    log.info("PROFINET IO-controller online - DCP Identify sent")

    phase = 0          # 0=pick, 1=place, 2=home
    cycle = 0
    while True:
        target = {0: 0, 1: 1, 2: 0}[phase]
        grip = 1 if phase in (1,) else 0
        sock.sendto(c.pn_rt(c.PN_OUTPUTS, bytes([target, grip]), cycle), (BCAST, PORT))
        cycle += 1
        if phase == 0 and pos[0] == 0:
            phase = 1
        elif phase == 1 and pos[0] >= 100:
            phase = 2
        elif phase == 2 and pos[0] == 0:
            phase = 0
        if cycle % 20 == 0:
            log.info("cmd phase=%s  robot pos=%d%% gripper=%s",
                     ["PICK", "PLACE", "HOME"][phase], pos[0],
                     "CLOSED" if gripper[0] else "OPEN")
        time.sleep(0.128)


if __name__ == "__main__":
    main()
