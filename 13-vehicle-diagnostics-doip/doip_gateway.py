"""DoIP vehicle gateway / edge node (TCP + UDP 13400).

Answers UDP vehicle-identification requests, handles TCP routing activation, and
routes UDS diagnostic messages to the target ECU by its logical address over the
internal vehicle network, wrapping the ECU's UDS response back into DoIP.
"""
import logging
import socket
import struct
import threading

import doip_lib as d

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("doip-gw")

VIN = "WVWZZZ1KZAW000001"
ENTITY_ADDR = 0x0010
ECUS = {0x1001: ("172.30.13.11", 22001),       # engine
        0x1002: ("172.30.13.12", 22002)}       # body


def forward_uds(target, uds):
    try:
        s = socket.create_connection(ECUS[target], timeout=2)
        s.sendall(struct.pack(">H", len(uds)) + uds)
        n = struct.unpack(">H", s.recv(2))[0]
        resp = b""
        while len(resp) < n:
            resp += s.recv(n - len(resp))
        s.close()
        return resp
    except (OSError, KeyError):
        return bytes([0x7F, uds[0], 0x25])         # noResponseFromSubnetComponent


def udp_identity():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", d.PORT))
    while True:
        data, peer = sock.recvfrom(256)
        msg = d.read_msg_bytes(data)
        if msg and msg["ptype"] == d.VEHICLE_ID_REQ:
            sock.sendto(d.vehicle_id_response(VIN, ENTITY_ADDR), peer)
            log.info("vehicle identification -> %s (VIN %s)", peer[0], VIN)


def handle_tcp(conn, peer):
    tester = 0
    with conn:
        while True:
            msg = d.read_msg(conn)
            if not msg:
                return
            if msg["ptype"] == d.ROUTING_ACT_REQ:
                tester = struct.unpack(">H", msg["payload"][:2])[0]
                conn.sendall(d.routing_activation_response(tester, ENTITY_ADDR, 0x10))
                log.info("routing activation from tester 0x%04X -> accepted", tester)
            elif msg["ptype"] == d.DIAG_MESSAGE:
                source, target, uds = d.parse_diag(msg["payload"])
                conn.sendall(d.diag_ack(ENTITY_ADDR, source, 0x00))
                resp = forward_uds(target, uds)
                conn.sendall(d.diag_message(target, source, resp))
                log.info("UDS 0x%02X -> ECU 0x%04X, resp 0x%02X", uds[0], target, resp[0])


def main():
    threading.Thread(target=udp_identity, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", d.PORT))
    srv.listen(5)
    log.info("DoIP gateway online (tcp/udp 13400), entity 0x%04X", ENTITY_ADDR)
    while True:
        conn, peer = srv.accept()
        threading.Thread(target=handle_tcp, args=(conn, peer), daemon=True).start()


if __name__ == "__main__":
    main()
