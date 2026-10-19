"""EPA (Ethernet for Plant Automation) device - product analyser
(ethertype 0x88BC, UDP 55020).

Broadcasts a cyclic measurement channel (product concentration).
"""
import logging
import math
import time

import rt_lib as r

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("epa-device")


def main():
    tx = r.sender()
    log.info("EPA analyser online - cyclic channel broadcast (udp/%d)", r.EPA_PORT)
    t = 0
    while True:
        conc = 98.0 + 1.2 * math.sin(t / 15.0)
        tx.sendto(r.epa_pack(0, conc), (r.BCAST, r.EPA_PORT))
        if t % 5 == 0:
            log.info("channel 0: product_concentration=%.2f%%", conc)
        t += 1
        time.sleep(1)


if __name__ == "__main__":
    main()
