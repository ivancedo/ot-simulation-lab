"""Servo drive / motion slave - one script, four protocols via PROTO env.

Listens for the cyclic command frame of its protocol, moves the axis toward the
commanded target, and returns actual position, velocity and torque.
"""
import logging
import os
import socket

import motion_lib as m

PROTO = os.environ.get("PROTO", "ethercat")
AXIS = os.environ.get("AXIS", "X")
MAXSTEP = int(os.environ.get("MAXSTEP", "4000"))     # counts per cycle (max velocity)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("drive-" + AXIS.lower())


def respond(actual, vel, torque, wkc):
    if PROTO == "ethercat":
        return m.ethercat_resp(actual, vel, torque, wkc)
    if PROTO == "sercos":
        return m.sercos_at(actual, vel, torque)
    if PROTO == "powerlink":
        return m.powerlink_pres(actual, vel, torque)
    return m.mechatrolink_resp(actual, vel, torque)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", m.PORTS[PROTO]))
    log.info("%s servo drive axis %s online (udp/%d)", PROTO, AXIS, m.PORTS[PROTO])

    actual = 0
    wkc = 0
    n = 0
    while True:
        data, peer = sock.recvfrom(64)
        target = m.parse_cmd(PROTO, data)
        delta = max(-MAXSTEP, min(MAXSTEP, target - actual))
        actual += delta
        vel = delta
        torque = int(delta * 0.05)                   # crude load model
        wkc = (wkc + 1) & 0xFFFF
        sock.sendto(respond(actual, vel, torque, wkc), peer)
        n += 1
        if n % 50 == 0:
            log.info("axis %s pos=%d vel=%d torque=%d", AXIS, actual, vel, torque)


if __name__ == "__main__":
    main()
