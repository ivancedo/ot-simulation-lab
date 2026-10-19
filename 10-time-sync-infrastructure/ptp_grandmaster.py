"""PTP grandmaster clock (IEEE 1588, two-step).

Broadcasts Sync (udp/319) + Follow_Up (udp/320) each second and answers
Delay_Req with Delay_Resp, so a slave can compute its offset and path delay.
"""
import logging
import socket
import threading
import time

import ptp_lib as p

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ptp-gm")

BCAST = "172.30.10.255"
p.set_clock_id(b"\x00\x11\x22\xff\xfe\xAA\xAA\x01")      # grandmaster identity


def sender():
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    seq = 0
    while True:
        t1 = p.now_ts()
        tx.sendto(p.message(p.SYNC, seq), (BCAST, p.EVENT_PORT))
        tx.sendto(p.message(p.FOLLOW_UP, seq, ts=t1), (BCAST, p.GENERAL_PORT))
        if seq % 5 == 0:
            log.info("announce + Sync/Follow_Up seq=%d (stratum-1 grandmaster)", seq)
        seq += 1
        time.sleep(1)


def delay_responder():
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("", p.EVENT_PORT))
    while True:
        data, _ = rx.recvfrom(128)
        msg = p.parse(data)
        if msg and msg["msgtype"] == p.DELAY_REQ:
            t4 = p.now_ts()
            resp = p.message(p.DELAY_RESP, msg["seq"], ts=t4, requesting_port=msg["source_port"])
            tx.sendto(resp, (BCAST, p.GENERAL_PORT))


threading.Thread(target=delay_responder, daemon=True).start()
log.info("PTP grandmaster online (event udp/319, general udp/320)")
sender()
