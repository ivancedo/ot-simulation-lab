"""Tridium Niagara 'Fox' supervisor / JACE (TCP/1911).

Fox is a text-framed protocol. This emulates the hello handshake and a point
subscription that streams a couple of station points back to the workstation.
"""
import logging
import math
import socket
import threading
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("fox-jace")

HELLO = ("fox a 1 -1 fox hello\n{\n"
         "fox.version=s:1.0.1\n"
         "id=i:1\n"
         "hostName=s:jace-ahu-01\n"
         "vmName=s:niagara\n"
         "}\n;;\n")


def handle(conn, peer):
    conn.sendall(HELLO.encode())
    log.info("fox hello sent to %s", peer[0])
    conn.settimeout(2.0)
    while True:
        try:
            data = conn.recv(256)
            if data == b"":
                return
        except socket.timeout:
            data = b""
        if data and b"subscribe" in data.lower():
            log.info("point subscription from workstation")
        t = time.time()
        chw = 6.5 + 0.5 * math.sin(t / 10.0)        # wall-clock so it stays continuous
        occ = 1 if int(t / 15) % 2 == 0 else 0
        msg = ("fox a 1 -1 fox event\n{\n"
               "chilledWaterTemp=f:%.2f\n"
               "occupancy=b:%s\n"
               "}\n;;\n" % (chw, "true" if occ else "false"))
        try:
            conn.sendall(msg.encode())
        except OSError:
            return
        t += 1
        time.sleep(3)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 1911))
    srv.listen(5)
    log.info("Niagara Fox station online on tcp/1911")
    while True:
        conn, peer = srv.accept()
        threading.Thread(target=handle, args=(conn, peer), daemon=True).start()


if __name__ == "__main__":
    main()
