"""EtherNet/IP adapter - remote I/O block for conveyor + press (TCP/44818, UDP/2222).

Explicit messaging (TCP): RegisterSession and CIP GetAttributeSingle on the
assembly object (class 0x04): instance 100 = input assembly (sensors),
instance 150 = output assembly (actuators).
Implicit I/O (UDP/2222): consumes the scanner's output assembly and produces the
input assembly each cycle.
"""
import logging
import random
import socket
import struct
import threading
import time

import cell_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("enip-adapter")

io = dict(conveyor=0, part=0, press_cmd=0, press_pos=0, conveyor_cmd=0)
lock = threading.Lock()


def physics():
    while True:
        with lock:
            io["conveyor"] = io["conveyor_cmd"]
            if io["conveyor"]:
                io["part"] = 1 if random.random() < 0.3 or io["part"] else io["part"]
            io["press_pos"] = min(100, io["press_pos"] + 20) if io["press_cmd"] \
                else max(0, io["press_pos"] - 20)
        time.sleep(0.5)


def input_assembly():
    with lock:
        return bytes([io["conveyor"], io["part"], io["press_cmd"], io["press_pos"]])


def handle_tcp(conn):
    session = 0
    with conn:
        while True:
            msg = c.read_encap(conn)
            if not msg:
                return
            if msg["command"] == c.REGISTER_SESSION:
                session = random.randint(1, 0xFFFF)
                conn.sendall(c.encap(c.REGISTER_SESSION, session, b"\x01\x00\x00\x00"))
            elif msg["command"] == c.SEND_RRDATA:
                cip = c.extract_cip(msg["data"])
                service, instance = cip[0], cip[5] if len(cip) > 5 else 0
                if service == 0x0E and instance == 100:          # GetAttributeSingle input asm
                    resp = c.cip_response(0x0E, 0x00, input_assembly())
                elif service == 0x01:                            # GetAttributesAll (Identity)
                    resp = c.cip_response(0x01, 0x00,
                                          struct.pack("<HHH", 0x01, 0x0C, 0x01) + b"CELL-IO-1")
                else:
                    resp = c.cip_response(service, 0x00, b"")
                conn.sendall(c.encap(c.SEND_RRDATA, session, c.send_rrdata(resp)))


def handle_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", c.ENIP_UDP))
    while True:
        data, peer = sock.recvfrom(256)
        if len(data) >= 6:
            seq = struct.unpack("<I", data[:4])[0]
            with lock:
                io["conveyor_cmd"], io["press_cmd"] = data[4], data[5]
            sock.sendto(struct.pack("<I", seq) + input_assembly(), peer)   # produce inputs


def main():
    threading.Thread(target=physics, daemon=True).start()
    threading.Thread(target=handle_udp, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", c.ENIP_TCP))
    srv.listen(5)
    log.info("EtherNet/IP adapter online (tcp/44818 explicit, udp/2222 implicit)")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_tcp, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
