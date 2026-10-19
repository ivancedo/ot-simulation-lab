"""Motion controller / managing node - coordinates four servo axes.

Runs a 2 ms-class cyclic loop (scaled for the lab), generating a coordinated
motion profile and exchanging the cyclic PDO of each axis's protocol:
  X : EtherCAT   Y : Sercos III   Z : Ethernet Powerlink   W : MECHATROLINK-III
"""
import logging
import math
import socket
import time

import motion_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("motion-ctrl")

AXES = [
    ("X", "ethercat", "172.30.8.10"),
    ("Y", "sercos", "172.30.8.11"),
    ("Z", "powerlink", "172.30.8.12"),
    ("W", "mechatrolink", "172.30.8.13"),
]


def cmd_frame(proto, target):
    return {"ethercat": m.ethercat_cmd, "sercos": m.sercos_mdt,
            "powerlink": m.powerlink_preq, "mechatrolink": m.mechatrolink_cmd}[proto](target)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.5)
    log.info("managing node online - coordinating %d axes", len(AXES))
    t = 0.0
    n = 0
    while True:
        results = {}
        for i, (axis, proto, ip) in enumerate(AXES):
            target = int(500000 * math.sin(t + i * math.pi / 2))     # coordinated profile
            try:
                sock.sendto(cmd_frame(proto, target), (ip, m.PORTS[proto]))
                data, _ = sock.recvfrom(64)
                results[axis] = m.parse_resp(proto, data)
            except socket.timeout:
                results[axis] = None
        n += 1
        if n % 50 == 0:
            log.info("  ".join("%s:%s=%d" % (a, p, results[a][0]) if results[a] else "%s:--" % a
                               for a, p, _ in AXES))
        t += 0.02
        time.sleep(0.01)      # ~100 Hz cyclic (scaled for the lab)


if __name__ == "__main__":
    main()
