"""EtherNet/IP scanner - cell PLC (TCP/44818 explicit + UDP/2222 implicit).

Registers a session, reads the Identity object once, then runs the conveyor/press
cycle: explicit GetAttributeSingle of the input assembly over TCP and implicit
output assembly over UDP each scan.
"""
import logging
import socket
import struct
import time

import cell_lib as c

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("enip-scanner")

ADAPTER = "172.30.7.10"


def register():
    while True:
        try:
            s = socket.create_connection((ADAPTER, c.ENIP_TCP), timeout=3)
            s.sendall(c.encap(c.REGISTER_SESSION, 0, b"\x01\x00\x00\x00"))
            session = c.read_encap(s)["session"]
            log.info("session 0x%04x registered", session)
            return s, session
        except OSError:
            time.sleep(1)


def read_assembly(sock, session, instance):
    cip = c.cip_request(0x0E, 0x04, instance, 0x03)
    sock.sendall(c.encap(c.SEND_RRDATA, session, c.send_rrdata(cip)))
    resp = c.read_encap(sock)
    return c.extract_cip(resp["data"])[4:]            # strip CIP resp header


def main():
    sock, session = register()
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.settimeout(1.0)
    cip = c.cip_request(0x01, 0x01, 1)                 # GetAttributesAll Identity
    sock.sendall(c.encap(c.SEND_RRDATA, session, c.send_rrdata(cip)))
    c.read_encap(sock)
    log.info("identity read - starting cell scan")

    seq, conveyor_cmd, press_cmd = 0, 1, 0
    while True:
        try:
            udp.sendto(struct.pack("<I", seq) + bytes([conveyor_cmd, press_cmd]),
                       (ADAPTER, c.ENIP_UDP))
            seq += 1
            try:
                reply, _ = udp.recvfrom(64)
            except socket.timeout:
                reply = b"\x00" * 8
            asm = read_assembly(sock, session, 100)
            conveyor, part, press, pos = asm[0], asm[1], asm[2], asm[3]
            # simple sequence: convey a part in, press it, retract
            if part and pos == 0 and not press_cmd:
                press_cmd, conveyor_cmd = 1, 0
            elif pos >= 100:
                press_cmd, conveyor_cmd = 0, 1
            log.info("conveyor=%d part=%d press=%d pos=%d%%", conveyor, part, press, pos)
        except OSError:
            log.warning("session lost - re-registering")
            sock, session = register()
        time.sleep(1)


if __name__ == "__main__":
    main()
