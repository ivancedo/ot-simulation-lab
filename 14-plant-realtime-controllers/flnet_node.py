"""FL-net (OPCN-2) node - batch sequencer (UDP 55000).

Participates in the FL-net token ring and broadcasts its common-memory area
cyclically (batch-step progress). The token node rotates each cycle.
"""
import logging
import time

import rt_lib as r

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("flnet-node")

NODE = 1


def main():
    tx = r.sender()
    log.info("FL-net node %d online - broadcasting common memory (udp/%d)", NODE, r.FLNET_PORT)
    seq = 0
    progress = 0.0
    while True:
        progress = (progress + 7) % 100
        token = 1 + (seq % 3)                      # token rotates across 3 nodes
        tx.sendto(r.flnet_pack(NODE, token, seq, progress), (r.BCAST, r.FLNET_PORT))
        if seq % 5 == 0:
            log.info("common memory: batch_progress=%.0f%% (token holder node %d)", progress, token)
        seq = (seq + 1) & 0xFFFF
        time.sleep(1)


if __name__ == "__main__":
    main()
