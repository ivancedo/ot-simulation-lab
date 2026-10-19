"""Classic OPC DA server (legacy MMI area).

Classic OPC Data Access runs over DCOM (RPC, no fixed port). DCOM is not
practical to containerise, so this emulates the OPC DA item read/write semantics
over a small TCP request/response: 'GET <item>' / 'VALUE <item> <value>'.
  Motor.Status (0/1)   Motor.Current (A)   Motor.Speed (rpm)
"""
import logging
import math
import socket
import threading
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("opc-da")

items = {"Motor.Status": 1.0, "Motor.Current": 0.0, "Motor.Speed": 0.0}
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            running = items["Motor.Status"]
            items["Motor.Speed"] = (1480 + 10 * math.sin(t / 7.0)) if running else 0
            items["Motor.Current"] = (14 + 2 * math.sin(t / 7.0)) if running else 0
        t += 1
        time.sleep(1)


def handle(conn):
    with conn:
        f = conn.makefile("rwb")
        for line in f:
            parts = line.decode(errors="ignore").split()
            if len(parts) >= 2 and parts[0] == "GET":
                with lock:
                    val = items.get(parts[1], 0.0)
                f.write(("VALUE %s %.2f\n" % (parts[1], val)).encode())
                f.flush()


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 7766))
    srv.listen(5)
    log.info("classic OPC DA (emulated) server online on tcp/7766")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
