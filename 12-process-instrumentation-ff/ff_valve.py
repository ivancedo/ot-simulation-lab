"""Foundation Fieldbus HSE field device - control valve (TCP/1090).

Runs an Analog Output (AO) function block: accepts a setpoint (SP) write from the
DCS and moves the valve travel (OUT) toward it; serves the OUT readback.
"""
import logging
import socket
import threading
import time

import ff_lib as f

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ff-valve")

state = dict(sp=50.0, out=50.0)
lock = threading.Lock()


def physics():
    while True:
        with lock:
            state["out"] += (state["sp"] - state["out"]) * 0.4    # actuator dynamics
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            payload = f.read_frame(conn)
            if not payload:
                return
            m = f.parse(payload)
            if m["mtype"] == f.WRITE_REQ and (m["block"], m["param"]) == f.AO_SP:
                with lock:
                    state["sp"] = max(0.0, min(100.0, m["value"]))
                conn.sendall(f.frame(f.msg(f.WRITE_RESP, m["invoke"], *f.AO_SP, value=state["sp"])))
            elif m["mtype"] == f.READ_REQ and (m["block"], m["param"]) == f.AO_OUT:
                with lock:
                    out = state["out"]
                conn.sendall(f.frame(f.msg(f.READ_RESP, m["invoke"], *f.AO_OUT, value=out)))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 1090))
    srv.listen(5)
    log.info("FF HSE control valve (AO block) online on tcp/1090")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
