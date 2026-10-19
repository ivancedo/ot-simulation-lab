"""WITS Level 0 client - mudlogging / geology monitoring station (TCP/20000).

Reassembles WITS0 frames between '&&' and '!!' and decodes the record/item codes.
"""
import logging
import socket
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("wits-client")

SERVER = "172.30.5.10"
ITEMS = {"0108": "depth(m)", "0110": "hookload(t)", "0111": "WOB(t)",
         "0112": "RPM", "0113": "SPP(kPa)", "0114": "flow(Lpm)"}


def connect():
    while True:
        try:
            s = socket.create_connection((SERVER, 20000), timeout=3)
            log.info("connected to WITS feed")
            return s
        except OSError:
            time.sleep(1)


def main():
    sock = connect()
    buf = ""
    record = {}
    in_rec = False
    while True:
        try:
            data = sock.recv(1024).decode(errors="ignore")
        except OSError:
            data = ""
        if not data:
            sock = connect()
            continue
        buf += data
        while "\r\n" in buf:
            line, buf = buf.split("\r\n", 1)
            if line == "&&":
                record, in_rec = {}, True
            elif line == "!!":
                in_rec = False
                shown = "  ".join("%s=%s" % (ITEMS.get(c, c), v) for c, v in record.items()
                                  if c in ("0108", "0110", "0113", "0114"))
                log.info("record 01: %s", shown)
            elif in_rec and len(line) >= 4:
                record[line[:4]] = line[4:]


if __name__ == "__main__":
    main()
