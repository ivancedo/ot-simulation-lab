"""Vnet/IP (Yokogawa) station - DCS reactor controller (TCP/5313).

Answers a Vnet/IP tag read with the current reactor temperature.
"""
import logging
import math
import socket
import threading
import time

import rt_lib as r

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("vnet-stn")

state = dict(temp=185.0)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            state["temp"] = 185 + 6 * math.sin(t / 12.0)
        t += 1
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            tag = r.vnet_read_tcp(conn)
            if not tag:
                return
            with lock:
                val = state["temp"] if "TEMP" in tag.upper() else 0.0
            conn.sendall(r.vnet_response(tag, val))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", r.VNET_PORT))
    srv.listen(5)
    log.info("Vnet/IP DCS station online on tcp/%d", r.VNET_PORT)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
