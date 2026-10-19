"""Station bay controller / HMI + PDC.

* subscribes to the relay GOOSE and GSSE status
* reads XCBR1.Pos / PTOC1.OpCnt / MMXU1.A from the relay over MMS (tcp/102)
* collects the PMU C37.118 synchrophasor stream (phasor data concentrator)
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
log = logging.getLogger("bay-ctrl")

RELAY = "172.30.2.11"
last_stnum = 0


def goose_sub():
    global last_stnum
    rx = s.listener(s.GOOSE_PORT)
    while True:
        data, _ = rx.recvfrom(2048)
        try:
            g = s.goose_unpack(data)
        except Exception:
            continue
        if g["stnum"] != last_stnum:
            last_stnum = g["stnum"]
            trip, closed = g["bools"][0], g["bools"][1]
            log.warning("GOOSE stNum=%d  TRIP=%s  BREAKER=%s  (goID=%s)",
                        g["stnum"], trip, "CLOSED" if closed else "OPEN", g["goid"])


def gsse_sub():
    rx = s.listener(s.GSSE_PORT)
    while True:
        data, _ = rx.recvfrom(1024)
        try:
            s.gsse_unpack(data)   # received, status mirrored by GOOSE log above
        except Exception:
            pass


def c37_pdc():
    rx = s.listener(4712)
    n = 0
    while True:
        data, _ = rx.recvfrom(2048)
        if len(data) < 8 or data[0] != 0xAA:
            continue
        n += 1
        if n % 50 == 0:                       # ~1 summary every 5 s
            idcode, soc, fracsec, stat = struct.unpack(">HIIH", data[4:16])
            mag, ang = struct.unpack(">ff", data[16:24])
            freq, rocof = struct.unpack(">ff", data[24:32])
            log.info("PDC: PMU%d  V=%.0fV  f=%.3fHz  ROCOF=%+.3f", idcode, mag, freq, rocof)


def mms_read(name):
    with socket.create_connection((RELAY, 102), timeout=3) as c:
        s.tpkt_send(c, b"\xa0" + name.encode())
        resp = s.tpkt_recv(c)
        return struct.unpack(">i", resp[1:5])[0]


def main():
    for fn in (goose_sub, gsse_sub, c37_pdc):
        threading.Thread(target=fn, daemon=True).start()
    log.info("bay controller online - GOOSE/GSSE subscriber, MMS client, PDC")
    while True:
        try:
            pos = mms_read("XCBR1.Pos")
            ops = mms_read("PTOC1.OpCnt")
            amp = mms_read("MMXU1.A")
            log.info("MMS poll: XCBR1.Pos=%s  PTOC1.OpCnt=%d  MMXU1.A=%dA",
                     "CLOSED" if pos == 2 else "OPEN", ops, amp)
        except OSError:
            log.warning("relay MMS unreachable, retrying")
        time.sleep(5)


if __name__ == "__main__":
    main()
