"""DoIP diagnostic tester - workshop / test-bench scan tool.

UDP vehicle identification, TCP routing activation, then a UDS sequence:
read VIN, start an extended session, read engine RPM and coolant, and read DTCs.
"""
import logging
import socket
import struct
import time

import doip_lib as d

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("tester")

GATEWAY = "172.30.13.10"
TESTER_ADDR = 0x0E80
ENGINE, BODY = 0x1001, 0x1002


def identify():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.settimeout(3)
    u.sendto(d.header(d.VEHICLE_ID_REQ, b""), (GATEWAY, d.PORT))
    try:
        data, _ = u.recvfrom(256)
        vin = d.read_msg_bytes(data)["payload"][:17].decode(errors="ignore")
        log.info("vehicle identified: VIN=%s", vin)
    except socket.timeout:
        log.warning("no vehicle identification response")
    u.close()


def uds_request(sock, target, uds):
    sock.sendall(d.diag_message(TESTER_ADDR, target, uds))
    while True:
        msg = d.read_msg(sock)
        if not msg:
            return b""
        if msg["ptype"] == d.DIAG_MESSAGE:
            _s, _t, resp = d.parse_diag(msg["payload"])
            return resp


def main():
    identify()
    while True:
        try:
            sock = socket.create_connection((GATEWAY, d.PORT), timeout=3)
            sock.sendall(d.routing_activation_request(TESTER_ADDR))
            d.read_msg(sock)
            log.info("routing activated - starting UDS scan")
            break
        except OSError:
            time.sleep(1)

    while True:
        try:
            vin = uds_request(sock, ENGINE, bytes([0x22, 0xF1, 0x90]))
            uds_request(sock, ENGINE, bytes([0x10, 0x03]))        # extended session
            rpm = uds_request(sock, ENGINE, bytes([0x22, 0x01, 0x0C]))
            temp = uds_request(sock, ENGINE, bytes([0x22, 0x01, 0x05]))
            dtc = uds_request(sock, ENGINE, bytes([0x19, 0x02, 0xFF]))
            rpm_val = struct.unpack(">H", rpm[3:5])[0] / 4 if len(rpm) >= 5 else 0
            temp_val = temp[3] - 40 if len(temp) >= 4 else 0
            ndtc = (len(dtc) - 3) // 4 if len(dtc) > 3 else 0
            log.info("VIN=%s  RPM=%.0f  coolant=%d C  stored DTCs=%d",
                     vin[3:].decode(errors="ignore"), rpm_val, temp_val, ndtc)
        except OSError:
            log.warning("link lost - re-activating"); return
        time.sleep(3)


if __name__ == "__main__":
    main()
