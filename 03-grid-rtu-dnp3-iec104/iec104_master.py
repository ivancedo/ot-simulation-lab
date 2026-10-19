"""IEC 60870-5-104 controlling station - control-center SCADA (TCP/2404).

Opens the data link (STARTDT), issues a general interrogation, acknowledges the
returned ASDUs with S-frames, and periodically sends a single command to the
remote substation breaker.
"""
import logging
import socket
import struct
import time

import iec104_lib as i

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("iec104-mst")

STATION = "172.30.3.12"
CA = 12
LABEL = {1001: "V(kV)", 1002: "P(MW)", 1003: "tap", 2001: "breaker"}


def connect():
    while True:
        try:
            s = socket.create_connection((STATION, 2404), timeout=3)
            log.info("TCP up - sending STARTDT act")
            s.sendall(i.u_frame(i.STARTDT_ACT))
            return s
        except OSError:
            time.sleep(1)


def main():
    sock = connect()
    ns, nr = 0, 0
    last_gi = 0                      # trigger a general interrogation immediately
    last_cmd = time.time()          # but hold the first command for 32 s
    breaker_cmd = True
    sock.settimeout(1.0)
    while True:
        now = time.time()
        if now - last_gi > 15:
            sock.sendall(i.i_frame(ns, nr, i.asdu(100, 6, CA, [(0, i.interrogation())])))
            ns = (ns + 1) & 0x7FFF
            last_gi = now
            log.info("general interrogation sent")
        if now - last_cmd > 32:
            breaker_cmd = not breaker_cmd
            sock.sendall(i.i_frame(ns, nr, i.asdu(45, 6, CA,
                         [(2001, i.single_cmd(breaker_cmd))])))
            ns = (ns + 1) & 0x7FFF
            last_cmd = now
            log.warning("single command: breaker -> %s", "CLOSE" if breaker_cmd else "OPEN")
        try:
            msg = i.parse(sock)
        except socket.timeout:
            continue
        except OSError:
            log.warning("link lost - reconnecting"); sock = connect(); sock.settimeout(1.0)
            ns, nr = 0, 0; continue
        if not msg:
            sock = connect(); sock.settimeout(1.0); ns, nr = 0, 0; continue
        if msg["kind"] == "U":
            log.info("U-frame 0x%02x (STARTDT con)", msg["code"])
        elif msg["kind"] == "I":
            nr = (msg["ns"] + 1) & 0x7FFF
            vals = []
            for ioa, payload in i.iter_objects(msg):
                if msg["type_id"] in (13, 11):
                    vals.append("%s=%.2f" % (LABEL.get(ioa, ioa), struct.unpack("<f", payload[:4])[0]))
                elif msg["type_id"] == 1:
                    vals.append("%s=%s" % (LABEL.get(ioa, ioa), "ON" if payload[0] & 1 else "OFF"))
            if vals:
                log.info("ASDU t=%d cot=%d  %s", msg["type_id"], msg["cot"], "  ".join(vals))
            sock.sendall(i.s_frame(nr))            # acknowledge


if __name__ == "__main__":
    main()
