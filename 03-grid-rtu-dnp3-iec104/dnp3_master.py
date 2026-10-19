"""DNP3 master - control-center front-end processor (IEEE 1815 / TCP 20000).

Runs a 5 s integrity poll of the feeder RTU and, every ~30 s, exercises the
breaker with a DIRECT OPERATE control to demonstrate supervisory control.
"""
import logging
import socket
import time

import dnp3_lib as d

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("dnp3-master")

RTU = "172.30.3.10"
ADDR, OUTSTATION = 1, 4


def connect():
    while True:
        try:
            s = socket.create_connection((RTU, 20000), timeout=3)
            log.info("connected to outstation addr=%d", OUTSTATION)
            return s
        except OSError:
            time.sleep(1)


def main():
    sock = connect()
    seq = 0
    ticks = 0
    breaker_cmd = True
    while True:
        try:
            sock.sendall(d.build(OUTSTATION, ADDR, 0xC4, d.read_user(seq)))
            seq = (seq + 1) & 0x0F
            frame = d.parse(sock)
            if frame:
                analogs, binaries = d.parse_response(frame[3])
                if analogs:
                    log.info("poll: V=%.2fkV I=%.0fA P=%.2fMW breaker=%s earth=%s",
                             analogs[0], analogs[1], analogs[2],
                             "CLOSED" if binaries[0] else "OPEN",
                             "CLOSED" if binaries[1] else "OPEN")
            ticks += 1
            if ticks % 6 == 0:                     # every ~30 s
                breaker_cmd = not breaker_cmd
                log.warning("sending DIRECT OPERATE: breaker -> %s",
                            "CLOSE" if breaker_cmd else "TRIP")
                sock.sendall(d.build(OUTSTATION, ADDR, 0xC4, d.op_user(0, breaker_cmd, seq)))
                seq = (seq + 1) & 0x0F
                d.parse(sock)
        except OSError:
            log.warning("link lost - reconnecting")
            sock = connect()
        time.sleep(5)


if __name__ == "__main__":
    main()
