"""DNP3 outstation - distribution feeder RTU (IEEE 1815 over TCP/20000).

Analog inputs : [0]=bus voltage kV, [1]=feeder current A, [2]=load MW
Binary inputs : [0]=breaker closed, [1]=earth switch closed
Binary output : index 0 = breaker trip/close (DIRECT OPERATE)
"""
import logging
import math
import socket
import threading
import time

import dnp3_lib as d

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("dnp3-rtu")

ADDR, MASTER = 4, 1
state = dict(v=11.2, a=180.0, mw=3.0, breaker=True, earth=False)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            if state["breaker"]:
                state["a"] = 180 + 60 * math.sin(t / 9.0)
                state["mw"] = max(0.1, 3.0 + 1.2 * math.sin(t / 9.0))
                state["v"] = 11.2 - state["mw"] * 0.05
            else:
                state["a"], state["mw"], state["v"] = 0.0, 0.0, 11.5
        t += 1
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            frame = d.parse(conn)
            if not frame:
                return
            _ctrl, _dst, _src, user = frame
            func = user[2] if len(user) > 2 else 0
            if func == 0x01:                       # READ (integrity poll)
                with lock:
                    analogs = [state["v"], state["a"], state["mw"]]
                    binaries = [state["breaker"], state["earth"]]
                conn.sendall(d.build(MASTER, ADDR, 0x44, d.resp_user(0x0000, analogs, binaries)))
            elif func == 0x05:                     # DIRECT OPERATE (CROB)
                code = user[8] if len(user) > 8 else 0
                on = (code == 0x41)
                with lock:
                    state["breaker"] = on
                log.warning("control from master: breaker -> %s", "CLOSE" if on else "TRIP")
                conn.sendall(d.build(MASTER, ADDR, 0x44, d.resp_user(0x0000,
                             [state["v"], state["a"], state["mw"]],
                             [state["breaker"], state["earth"]])))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 20000))
    srv.listen(5)
    log.info("DNP3 outstation addr=%d listening on tcp/20000", ADDR)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
