"""TCnet (Toshiba) node - utility monitoring (ethertype 0x888B, UDP 55010).

Broadcasts a cyclic data block (utility header pressure).
"""
import logging
import math
import time

import rt_lib as r

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("tcnet-node")


def main():
    tx = r.sender()
    log.info("TCnet node online - cyclic block broadcast (udp/%d)", r.TCNET_PORT)
    t = 0
    while True:
        pressure = 500 + 25 * math.sin(t / 8.0)
        tx.sendto(r.tcnet_pack(1, pressure), (r.BCAST, r.TCNET_PORT))
        if t % 5 == 0:
            log.info("block 1: utility_pressure=%.1f kPa", pressure)
        t += 1
        time.sleep(1)


if __name__ == "__main__":
    main()
