"""Vehicle ECU behind the DoIP gateway - answers UDS (ISO 14229).

One script serves several ECUs via ECU_NAME / VIN / INT_PORT. It receives raw
UDS requests (length-prefixed) forwarded by the gateway and answers:
  0x10 DiagnosticSessionControl   0x22 ReadDataByIdentifier
  0x19 ReadDTCInformation         0x3E TesterPresent
"""
import logging
import math
import os
import socket
import struct
import threading
import time

ECU_NAME = os.environ.get("ECU_NAME", "engine")
VIN = os.environ.get("VIN", "WVWZZZ1KZAW000001")
INT_PORT = int(os.environ.get("INT_PORT", "22001"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ecu-" + ECU_NAME)

live = dict(rpm=820, coolant=89)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            live["rpm"] = int(820 + 400 * abs(math.sin(t / 5.0)))
            live["coolant"] = int(89 + 5 * math.sin(t / 30.0))
        t += 1
        time.sleep(1)


def uds(req):
    sid = req[0]
    if sid == 0x10:                                   # DiagnosticSessionControl
        return bytes([0x50, req[1], 0x00, 0x32, 0x01, 0xF4])
    if sid == 0x3E:                                   # TesterPresent
        return bytes([0x7E, req[1] if len(req) > 1 else 0])
    if sid == 0x22:                                   # ReadDataByIdentifier
        did = struct.unpack(">H", req[1:3])[0]
        if did == 0xF190:
            return bytes([0x62]) + req[1:3] + VIN.encode()
        with lock:
            if did == 0x010C:
                return bytes([0x62]) + req[1:3] + struct.pack(">H", live["rpm"] * 4)
            if did == 0x0105:
                return bytes([0x62]) + req[1:3] + bytes([live["coolant"] + 40])
        return bytes([0x7F, 0x22, 0x31])              # requestOutOfRange
    if sid == 0x19 and len(req) > 1 and req[1] == 0x02:   # ReadDTCInformation
        # engine reports one stored DTC (P0171 system too lean) with status 0x08
        dtcs = bytes([0x01, 0x71, 0x00, 0x08]) if ECU_NAME == "engine" else b""
        return bytes([0x59, 0x02, 0xFF]) + dtcs
    return bytes([0x7F, sid, 0x11])                   # serviceNotSupported


def handle(conn):
    with conn:
        while True:
            hdr = conn.recv(2)
            if len(hdr) < 2:
                return
            n = struct.unpack(">H", hdr)[0]
            req = b""
            while len(req) < n:
                req += conn.recv(n - len(req))
            resp = uds(req)
            conn.sendall(struct.pack(">H", len(resp)) + resp)


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", INT_PORT))
    srv.listen(5)
    log.info("ECU '%s' online (UDS on internal tcp/%d)", ECU_NAME, INT_PORT)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
