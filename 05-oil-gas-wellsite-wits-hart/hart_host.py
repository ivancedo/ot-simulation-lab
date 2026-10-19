"""HART-IP host / asset-management gateway (TCP/5094 client).

Opens a HART-IP session, reads the device identity (command 0) once, then polls
the dynamic variables (command 3) on a schedule.
"""
import logging
import socket
import time

import hartip_lib as h

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("hart-host")

DEVICE = "172.30.5.12"
MASTER_ADDR = bytes([0x80, 0x00, 0x00, 0x00, 0x00])
UNITS = {12: "psi", 32: "degC", 57: "%", 250: ""}


def connect():
    while True:
        try:
            s = socket.create_connection((DEVICE, h.PORT), timeout=3)
            s.sendall(h.hdr(h.REQUEST, h.ID_SESSION_INIT, 1,
                            bytes([0x01]) + (0).to_bytes(4, "big")))
            h.read_msg(s)
            log.info("HART-IP session established")
            return s
        except OSError:
            time.sleep(1)


def poll(sock, command, seq):
    sock.sendall(h.hdr(h.REQUEST, h.ID_PDU, seq, h.hart_pdu(MASTER_ADDR, command)))
    msg = h.read_msg(sock)
    return h.parse_pdu(msg["body"]) if msg else None


def main():
    sock = connect()
    ident = poll(sock, 0, 2)
    if ident:
        log.info("device identified (cmd 0, %d id bytes)", len(ident["data"]))
    seq = 3
    while True:
        try:
            pdu = poll(sock, 3, seq)
            seq = (seq + 1) & 0xFFFF
            if pdu and pdu["command"] == 3:
                cur, dyn = h.parse_cmd3(pdu["data"])
                desc = "  ".join("%s%.1f%s" % (n, v, UNITS.get(u, ""))
                                 for (u, v), n in zip(dyn, ("PV=", "SV=", "TV=", "QV=")))
                log.info("loop=%.2fmA  %s", cur, desc)
        except OSError:
            log.warning("session lost - reconnecting")
            sock = connect()
            seq = 3
        time.sleep(4)


if __name__ == "__main__":
    main()
