"""HART-IP field device - wellhead multivariable transmitter (TCP/5094).

Handles the HART-IP session-initiate handshake and token-passing PDUs for HART
command 0 (read unique identifier) and command 3 (read dynamic variables):
  PV = wellhead pressure (psi)   SV = temperature (degC)
  TV = flow (%)                  QV = valve position (%)
"""
import logging
import math
import socket
import threading
import time

import hartip_lib as h

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("hart-device")

ADDRESS = bytes([0x26, 0x06, 0x12, 0x34, 0x56])     # long-frame unique address
state = dict(pv=1450.0, sv=78.0, tv=62.0, qv=55.0)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            state["pv"] = 1450 + 60 * math.sin(t / 8.0)
            state["sv"] = 78 + 3 * math.sin(t / 15.0)
            state["tv"] = 62 + 8 * math.sin(t / 6.0)
            state["qv"] = 55 + 10 * math.sin(t / 10.0)
        t += 1
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            msg = h.read_msg(conn)
            if not msg:
                return
            if msg["mid"] == h.ID_SESSION_INIT:
                conn.sendall(h.hdr(h.RESPONSE, h.ID_SESSION_INIT, msg["seq"], msg["body"]))
                log.info("session initiated")
            elif msg["mid"] == h.ID_KEEPALIVE:
                conn.sendall(h.hdr(h.RESPONSE, h.ID_KEEPALIVE, msg["seq"], b""))
            elif msg["mid"] == h.ID_PDU:
                pdu = h.parse_pdu(msg["body"])
                if pdu["command"] == 0:
                    data = h.cmd0_data(0x26, 0x06, 0x123456)
                    resp = h.hart_pdu(ADDRESS, 0, data, response=True)
                elif pdu["command"] == 3:
                    with lock:
                        mA = 4 + (state["pv"] - 1390) / 120 * 16
                        data = h.cmd3_data(mA, state["pv"], state["sv"], state["tv"], state["qv"])
                    resp = h.hart_pdu(ADDRESS, 3, data, response=True)
                else:
                    resp = h.hart_pdu(ADDRESS, pdu["command"], bytes([0x40, 0x00]), response=True)
                conn.sendall(h.hdr(h.RESPONSE, h.ID_PDU, msg["seq"], resp))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", h.PORT))
    srv.listen(5)
    log.info("HART-IP transmitter online on tcp/%d", h.PORT)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
