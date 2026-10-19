"""ICCP/TASE.2 client - Control Center B (MMS over tcp/102).

Associates with the peer control center, periodically reads the bilateral-table
points on demand, and receives the DSTransferSet Information-Reports streamed by
the server.
"""
import logging
import socket
import threading
import time

import iccp_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("iccp-B")

PEER = "172.30.11.10"
POINTS = ["VCC_A/MW_Gen_Total", "VCC_A/TieLine_Flow", "VCC_A/Frequency", "VCC_A/ACE"]


def connect():
    while True:
        try:
            s = socket.create_connection((PEER, c.PORT), timeout=3)
            s.settimeout(None)                      # block for transfer-set reports
            log.info("associated with Control Center A")
            return s
        except OSError:
            time.sleep(1)


def reader(sock):
    while True:
        pdu = c.tpkt_recv(sock)
        if not pdu:
            return
        msg = c.parse(pdu)
        if msg["tag"] == c.INFO_REPORT:
            log.info("TransferSet report: %-22s = %8.3f", msg["name"], msg["value"])
        elif msg["tag"] == c.READ_RESP:
            log.info("on-demand read:     %-22s = %8.3f", msg["name"], msg["value"])


def main():
    sock = connect()
    threading.Thread(target=reader, args=(sock,), daemon=True).start()
    while True:
        try:
            c.tpkt_send(sock, c.read_request("VCC_A/ACE"))      # on-demand read
            time.sleep(10)
        except OSError:
            log.warning("association lost - reconnecting")
            sock = connect()
            threading.Thread(target=reader, args=(sock,), daemon=True).start()


if __name__ == "__main__":
    main()
