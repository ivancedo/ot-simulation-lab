"""WITS Level 0 server - rig data aggregator / WITSML edge (TCP/20000).

Streams WITS0 record 01 (general time-based) as ASCII frames bracketed by
'&&' and '!!', each line being a 4-digit record/item code followed by the value.
"""
import logging
import math
import socket
import threading
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("wits-server")

ITEMS = {"0108": "BitDepth(m)", "0110": "Hookload(t)", "0111": "WOB(t)",
         "0112": "RPM", "0113": "SPP(kPa)", "0114": "FlowIn(Lpm)"}


def build_record(t, depth):
    vals = {
        "0108": depth,
        "0110": 95 + 12 * math.sin(t / 5.0),
        "0111": 8 + 3 * math.sin(t / 4.0),
        "0112": 120 + 10 * math.sin(t / 6.0),
        "0113": 18000 + 1500 * math.sin(t / 3.0),
        "0114": 2600 + 150 * math.sin(t / 7.0),
    }
    lines = ["&&"]
    for code, v in vals.items():
        lines.append("%s%.1f" % (code, v))
    lines.append("!!")
    return ("\r\n".join(lines) + "\r\n").encode(), vals


def serve(conn):
    t, depth = 0, 2450.0
    with conn:
        while True:
            depth += 0.08                      # ROP ~ steady penetration
            frame, vals = build_record(t, depth)
            try:
                conn.sendall(frame)
            except OSError:
                return
            if t % 5 == 0:
                log.info("depth %.1fm  hookload %.0ft  SPP %.0fkPa  flow %.0fLpm",
                         depth, vals["0110"], vals["0113"], vals["0114"])
            t += 1
            time.sleep(2)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 20000))
    srv.listen(5)
    log.info("WITS0 server streaming record 01 on tcp/20000")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=serve, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
