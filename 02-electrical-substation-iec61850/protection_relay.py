"""Feeder protection relay / IED (PTOC overcurrent + XCBR breaker).

* subscribes to the Merging Unit SV stream and runs a 1000 A overcurrent element
* publishes GOOSE (0x88B8) with the trip + breaker-position dataset, bursting on
  every state change and heart-beating otherwise
* publishes a GSSE (0x88B9) status word
* serves MMS (ISO-on-TCP / 102) so the station bay controller can read
  XCBR1.Pos and the PTOC1 operation counter
"""
import logging
import socket
import struct
import threading
import time

import station_lib as s

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("relay")

PICKUP = 1000          # A
RECLOSE_SEC = 6
GO_ID = "REL01/LLN0$GO$gcbTrip"

state = dict(breaker_closed=True, trip=False, stnum=1, op_count=0, ia=0)
lock = threading.Lock()
goose_dirty = threading.Event()


def watch_sv():
    rx = s.listener(s.SV_PORT)
    over_samples = 0
    while True:
        data, _ = rx.recvfrom(2048)
        try:
            sv = s.sv_unpack(data)
        except Exception:
            continue
        ia = sv["channels"][0]
        with lock:
            state["ia"] = ia
            if state["breaker_closed"] and ia > PICKUP:
                over_samples += 1
                if over_samples >= 3:            # ~150 ms of overcurrent
                    state.update(breaker_closed=False, trip=True,
                                 op_count=state["op_count"] + 1,
                                 stnum=state["stnum"] + 1)
                    over_samples = 0
                    log.warning("PTOC1 TRIP - Ia=%dA > %dA, opening XCBR1", ia, PICKUP)
                    goose_dirty.set()
                    threading.Timer(RECLOSE_SEC, reclose).start()
            else:
                over_samples = 0


def reclose():
    with lock:
        state.update(breaker_closed=True, trip=False, stnum=state["stnum"] + 1)
    log.info("auto-reclose - XCBR1 CLOSED")
    goose_dirty.set()


def goose_publisher():
    tx = s.sender()
    sqnum = 0
    while True:
        changed = goose_dirty.wait(timeout=1.0)
        goose_dirty.clear()
        sqnum = 0 if changed else sqnum + 1
        with lock:
            bools = [state["trip"], state["breaker_closed"]]
            stnum = state["stnum"]
        ttl = 10 if changed else 2000
        s.publish(tx, s.GOOSE_PORT, s.goose_pack(GO_ID, stnum, sqnum, ttl, False, bools))
        gbits = (1 if bools[0] else 0) | (2 if bools[1] else 0)
        s.publish(tx, s.GSSE_PORT, s.gsse_pack(stnum, gbits))
        if changed:                              # fast burst after an event
            for i in range(1, 4):
                time.sleep(0.01 * i)
                s.publish(tx, s.GOOSE_PORT,
                          s.goose_pack(GO_ID, stnum, sqnum + i, ttl, False, bools))


def mms_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 102))
    srv.listen(5)
    log.info("MMS server on tcp/102 (XCBR1.Pos, PTOC1.OpCnt, MMXU1.A)")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=mms_client, args=(conn,), daemon=True).start()


def mms_client(conn):
    with conn:
        while True:
            req = s.tpkt_recv(conn)
            if not req:
                return
            # req = 0xA0 (read) + ascii object name
            name = req[1:].decode(errors="ignore")
            with lock:
                val = {"XCBR1.Pos": 2 if state["breaker_closed"] else 1,
                       "PTOC1.OpCnt": state["op_count"],
                       "MMXU1.A": state["ia"]}.get(name, -1)
            s.tpkt_send(conn, b"\xa1" + struct.pack(">i", val))


threading.Thread(target=watch_sv, daemon=True).start()
threading.Thread(target=goose_publisher, daemon=True).start()
mms_server()
