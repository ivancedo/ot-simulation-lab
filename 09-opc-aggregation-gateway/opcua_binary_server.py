"""OPC UA server - binary (UA-TCP, port 4840). Production-line area.

HEL/ACK handshake then Read service for:
  node 1 = production rate (parts/min)  node 2 = line speed (m/min)
  node 3 = reject count
"""
import logging
import math
import socket
import threading
import time

import opc_lib as o

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("opcua-bin")

nodes = {1: 120.0, 2: 45.0, 3: 0.0}
lock = threading.Lock()


def physics():
    t = 0
    rejects = 0
    while True:
        with lock:
            nodes[1] = 120 + 15 * math.sin(t / 10.0)
            nodes[2] = 45 + 5 * math.sin(t / 10.0)
            if t % 12 == 0:
                rejects += 1
            nodes[3] = rejects
        t += 1
        time.sleep(1)


def handle(conn):
    with conn:
        while True:
            msg = o.read_ua(conn)
            if not msg:
                return
            if msg["mtype"] == b"HEL":
                conn.sendall(o.ack())
            elif msg["mtype"] == b"MSG":
                req = o.parse_msg(msg["body"])
                if req["kind"] == "read":
                    with lock:
                        val = nodes.get(req["node"], 0.0)
                    conn.sendall(o.read_response(req["node"], val))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", o.UA_PORT))
    srv.listen(5)
    log.info("OPC UA binary server online on tcp/%d", o.UA_PORT)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
