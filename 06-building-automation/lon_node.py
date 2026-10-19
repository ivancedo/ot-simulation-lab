"""LonWorks / LonTalk (EIA-709) node - VAV terminal box (TCP/1628).

Simplified LonTalk-over-IP: answers a network-variable (NV) poll with the
current SNVT values for the VAV box.
  NV 0  nvoSpaceTemp (degC)   NV 1  nvoFlowVolume (L/s)   NV 2  nvoDamperPos (%)
"""
import logging
import math
import socket
import struct
import threading
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("lon-vav")

nv = [21.5, 120.0, 55.0]
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            nv[0] = 21.5 + 0.8 * math.sin(t / 25.0)
            nv[2] = 55 + 25 * math.sin(t / 12.0)
            nv[1] = 80 + nv[2]
        t += 1
        time.sleep(2)


def handle(conn):
    with conn:
        while True:
            req = conn.recv(8)
            if not req:
                return
            if req[0] == 0x73 and len(req) >= 2:        # NV poll (update request)
                idx = req[1]
                with lock:
                    val = nv[idx] if idx < len(nv) else 0.0
                conn.sendall(bytes([0x74, idx]) + struct.pack(">f", val))   # NV update


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 1628))
    srv.listen(5)
    log.info("LonTalk VAV node online on tcp/1628")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
