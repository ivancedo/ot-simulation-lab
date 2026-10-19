"""NTP server (SNTP/NTP, UDP/123), stratum 1.

Answers mode-3 client requests with a mode-4 response carrying the four NTP
timestamps so the client can compute offset and round-trip delay.
"""
import logging
import socket
import struct
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ntp-server")

NTP_EPOCH = 2208988800      # seconds between 1900-01-01 and 1970-01-01


def to_ntp(t):
    secs = int(t) + NTP_EPOCH
    frac = int((t - int(t)) * (1 << 32))
    return struct.pack(">II", secs & 0xFFFFFFFF, frac & 0xFFFFFFFF)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 123))
    log.info("NTP stratum-1 server online on udp/123")
    n = 0
    while True:
        data, peer = sock.recvfrom(96)
        rx = time.time()
        xmt = data[40:48] if len(data) >= 48 else b"\x00" * 8     # client transmit timestamp
        pkt = struct.pack(">BBBb", 0x24, 1, 4, -20)               # LI/VN/Mode, stratum, poll, prec
        pkt += struct.pack(">II", 0, 0)                           # root delay / dispersion
        pkt += b"GPS\x00"                                         # reference id
        pkt += to_ntp(rx)                                         # reference timestamp
        pkt += xmt                                                # originate = client xmt
        pkt += to_ntp(rx)                                         # receive timestamp
        pkt += to_ntp(time.time())                               # transmit timestamp
        sock.sendto(pkt, peer)
        n += 1
        if n % 5 == 0:
            log.info("served %d time requests (last from %s)", n, peer[0])


if __name__ == "__main__":
    main()
