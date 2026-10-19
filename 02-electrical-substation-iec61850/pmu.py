"""Phasor Measurement Unit - IEEE C37.118.2 synchrophasor streamer.

Streams real C37.118 data frames (SYNC 0xAA01, IDCODE, SOC/FRACSEC time stamp,
one positive-sequence voltage phasor, frequency and ROCOF, CRC-CCITT) over UDP
to the station PDC in the bay controller.
"""
import logging
import math
import socket
import struct
import time

import station_lib as s

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("pmu")

IDCODE = 7
C37_PORT = 4712


def crc_ccitt(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def data_frame(mag, ang, freq, rocof):
    soc = int(time.time())
    fracsec = 0
    body = struct.pack(">H", 0xAA01)            # SYNC: data frame, v1
    rest = struct.pack(">HIIH", IDCODE, soc, fracsec, 0x0000)   # IDCODE SOC FRACSEC STAT
    rest += struct.pack(">ff", mag, ang)        # phasor (polar float)
    rest += struct.pack(">ff", freq, rocof)     # FREQ, DFREQ
    framesize = 2 + 2 + len(rest) + 2
    frame = body + struct.pack(">H", framesize) + rest
    return frame + struct.pack(">H", crc_ccitt(frame))


def main():
    tx = s.sender()
    log.info("C37.118 PMU IDCODE=%d streaming to PDC (udp/%d)", IDCODE, C37_PORT)
    t = 0
    while True:
        freq = 50.0 + 0.02 * math.sin(t / 7.0)
        rocof = 0.02 * math.cos(t / 7.0)
        mag = 63500 + 300 * math.sin(t / 3.0)
        ang = 0.1 * math.sin(t / 5.0)
        tx.sendto(data_frame(mag, ang, freq, rocof), (s.BCAST, C37_PORT))
        if t % 10 == 0:
            log.info("V=%.0fV f=%.3fHz ROCOF=%+.3fHz/s", mag, freq, rocof)
        t += 1
        time.sleep(0.1)


if __name__ == "__main__":
    main()
