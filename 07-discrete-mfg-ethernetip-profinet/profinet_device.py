"""PROFINET IO-device - 6-axis pick & place robot.

Answers DCP Identify and runs the RT cyclic exchange: consumes the controller's
output frame (target pose + gripper) and produces its input frame (arm position,
gripper feedback, status) every cycle. Emulated over UDP broadcast (0x8892 RT).
"""
import logging
import socket
import struct
import threading
import time

import cell_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("pn-device")

BCAST, PORT = "172.30.7.255", 34962
STATION = "robot-cell-01"
state = dict(pos=0, gripper=0, target=0, grip_cmd=0)
lock = threading.Lock()


def rx_loop(sock):
    while True:
        data, peer = sock.recvfrom(256)
        f = c.pn_parse(data)
        if not f:
            continue
        if f["frame_id"] == c.PN_DCP_IDENT and not f["iodata"]:   # request has empty payload
            resp = c.pn_rt(c.PN_DCP_IDENT, b"\x05\x04" + STATION.encode(), 0)
            sock.sendto(resp, (BCAST, PORT))
            log.info("DCP Identify answered as '%s'", STATION)
        elif f["frame_id"] == c.PN_OUTPUTS:
            with lock:
                state["target"], state["grip_cmd"] = f["iodata"][0], f["iodata"][1]


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))
    threading.Thread(target=rx_loop, args=(sock,), daemon=True).start()
    log.info("PROFINET IO-device '%s' online (RT cyclic, udp/%d)", STATION, PORT)

    cycle = 0
    while True:
        with lock:
            goal = state["target"] * 100
            state["pos"] += 25 if state["pos"] < goal else (-25 if state["pos"] > goal else 0)
            state["pos"] = max(0, min(100, state["pos"]))
            state["gripper"] = state["grip_cmd"]
            iodata = bytes([state["pos"], state["gripper"], 0x01])     # inputs + status
        sock.sendto(c.pn_rt(c.PN_INPUTS, iodata, cycle), (BCAST, PORT))
        cycle += 1
        if cycle % 20 == 0:
            log.info("arm pos=%d%% gripper=%s", state["pos"], "CLOSED" if state["gripper"] else "OPEN")
        time.sleep(0.128)       # 128 ms cyclic (scaled for the lab)


if __name__ == "__main__":
    main()
