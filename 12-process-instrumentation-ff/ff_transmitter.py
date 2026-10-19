"""Foundation Fieldbus HSE field device - flow transmitter (TCP/1089).

Runs an Analog Input (AI) function block. The flow it measures depends on the
valve travel reported by the control valve, so the loop closes through the DCS.
"""
import logging
import socket
import threading
import time

import ff_lib as f

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ff-xmtr")

VALVE = ("172.30.12.11", 1090)
state = dict(flow=0.0)
lock = threading.Lock()


def physics():
    flow = 0.0
    while True:
        travel = 50.0
        try:                                          # read valve travel to model the process
            s = socket.create_connection(VALVE, timeout=2)
            s.sendall(f.frame(f.msg(f.READ_REQ, 1, *f.AO_OUT)))
            travel = f.parse(f.read_frame(s))["value"]
            s.close()
        except OSError:
            pass
        target = travel * 2.4                          # flow m3/h proportional to valve
        flow += (target - flow) * 0.3
        with lock:
            state["flow"] = flow
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            payload = f.read_frame(conn)
            if not payload:
                return
            m = f.parse(payload)
            if m["mtype"] == f.READ_REQ and (m["block"], m["param"]) == f.AI_OUT:
                with lock:
                    val = state["flow"]
                conn.sendall(f.frame(f.msg(f.READ_RESP, m["invoke"], *f.AI_OUT, value=val)))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 1089))
    srv.listen(5)
    log.info("FF HSE flow transmitter (AI block) online on tcp/1089")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
