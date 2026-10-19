"""NTP client - polls the stratum-1 server and computes offset / delay.

  offset = ((t2 - t1) + (t3 - t4)) / 2
  delay  = (t4 - t1) - (t3 - t2)
"""
import logging
import socket
import struct
import time

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ntp-client")

SERVER = "172.30.10.12"
NTP_EPOCH = 2208988800


def from_ntp(b):
    secs, frac = struct.unpack(">II", b)
    return (secs - NTP_EPOCH) + frac / (1 << 32)


def to_ntp(t):
    secs = int(t) + NTP_EPOCH
    frac = int((t - int(t)) * (1 << 32))
    return struct.pack(">II", secs & 0xFFFFFFFF, frac & 0xFFFFFFFF)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    log.info("NTP client polling %s", SERVER)
    while True:
        try:
            t1 = time.time()
            pkt = struct.pack(">BBBb", 0x1B, 0, 4, -20) + b"\x00" * 36 + to_ntp(t1)  # mode 3
            sock.sendto(pkt, (SERVER, 123))
            data, _ = sock.recvfrom(96)
            t4 = time.time()
            t2 = from_ntp(data[32:40])          # server receive timestamp
            t3 = from_ntp(data[40:48])          # server transmit timestamp
            offset = ((t2 - t1) + (t3 - t4)) / 2
            delay = (t4 - t1) - (t3 - t2)
            log.info("stratum=%d offset=%+.6f s  delay=%.6f s", data[1], offset, abs(delay))
        except socket.timeout:
            log.warning("no NTP reply")
        time.sleep(4)


if __name__ == "__main__":
    main()
