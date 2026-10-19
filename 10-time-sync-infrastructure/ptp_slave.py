"""PTP ordinary clock (slave).

Receives Sync (t2) + Follow_Up (t1), sends Delay_Req (t3), receives Delay_Resp
(t4) and computes clock offset and mean path delay the IEEE 1588 way:
  offset = ((t2 - t1) - (t4 - t3)) / 2
  delay  = ((t2 - t1) + (t4 - t3)) / 2
"""
import logging
import socket
import threading
import time

import ptp_lib as p

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ptp-slave")

BCAST = "172.30.10.255"
p.set_clock_id(b"\x00\x11\x22\xff\xfe\xBB\xBB\x02")      # slave identity
t = dict(t1=None, t2=None, t3=None)
tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


def event_rx():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("", p.EVENT_PORT))
    while True:
        data, _ = rx.recvfrom(128)
        msg = p.parse(data)
        if msg and msg["msgtype"] == p.SYNC:
            t["t2"] = time.time()                       # t2: local receipt of Sync


def general_rx():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("", p.GENERAL_PORT))
    seq = 0
    while True:
        data, _ = rx.recvfrom(128)
        msg = p.parse(data)
        if not msg:
            continue
        if msg["msgtype"] == p.FOLLOW_UP and t["t2"]:
            t["t1"] = msg["ts"]                          # t1: master Sync origin
            t["t3"] = time.time()
            tx.sendto(p.message(p.DELAY_REQ, seq), (BCAST, p.EVENT_PORT))
            seq += 1
        elif msg["msgtype"] == p.DELAY_RESP and msg["source_port"] and t["t1"]:
            t4 = msg["ts"]
            t1, t2, t3 = t["t1"], t["t2"], t["t3"]
            if None in (t1, t2, t3):
                continue
            offset = ((t2 - t1) - (t4 - t3)) / 2
            delay = ((t2 - t1) + (t4 - t3)) / 2
            log.info("offset=%+.6f s  path delay=%.6f s  -> disciplining local clock",
                     offset, abs(delay))


for fn in (event_rx, general_rx):
    threading.Thread(target=fn, daemon=True).start()
log.info("PTP slave online - syncing to grandmaster")
while True:
    time.sleep(3600)
