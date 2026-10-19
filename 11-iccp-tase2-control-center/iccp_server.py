"""ICCP/TASE.2 server - Control Center A (MMS over tcp/102).

Exposes the bilateral-table points of control area A and runs a DSTransferSet
that streams them to the peer control center as MMS Information-Reports.
  VCC_A/MW_Gen_Total  VCC_A/TieLine_Flow  VCC_A/Frequency  VCC_A/ACE
"""
import logging
import math
import socket
import threading
import time

import iccp_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("iccp-A")

points = {"VCC_A/MW_Gen_Total": 1850.0, "VCC_A/TieLine_Flow": 120.0,
          "VCC_A/Frequency": 50.0, "VCC_A/ACE": 0.0}
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            points["VCC_A/MW_Gen_Total"] = 1850 + 80 * math.sin(t / 18.0)
            points["VCC_A/TieLine_Flow"] = 120 + 40 * math.sin(t / 12.0)
            points["VCC_A/Frequency"] = 50.0 + 0.03 * math.sin(t / 9.0)
            points["VCC_A/ACE"] = -points["VCC_A/TieLine_Flow"] * 0.1
        t += 1
        time.sleep(1)


def handle(conn):
    stop = threading.Event()

    def transfer_set():
        while not stop.is_set():
            time.sleep(5)
            try:
                with lock:
                    snap = dict(points)
                for name, val in snap.items():
                    c.tpkt_send(conn, c.info_report(name, val))
            except OSError:
                return

    threading.Thread(target=transfer_set, daemon=True).start()
    log.info("peer associated - DSTransferSet active")
    with conn:
        while True:
            pdu = c.tpkt_recv(conn)
            if not pdu:
                stop.set()
                return
            msg = c.parse(pdu)
            if msg["tag"] == c.READ:
                with lock:
                    val = points.get(msg["name"], 0.0)
                c.tpkt_send(conn, c.read_response(msg["name"], val))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", c.PORT))
    srv.listen(5)
    log.info("TASE.2 server (Control Center A) online on tcp/102")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
