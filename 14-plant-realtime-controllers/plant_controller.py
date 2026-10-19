"""Plant real-time controller / integrated DCS console.

Subscribes to the FL-net, TCnet and EPA cyclic broadcasts and polls the Vnet/IP
station over TCP, then prints one integrated plant view.
"""
import logging
import socket
import threading
import time

import rt_lib as r

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("plant-ctrl")

VNET = "172.30.14.13"
latest = dict(batch=0.0, pressure=0.0, conc=0.0, temp=0.0)


def sub(port, parse, key, field):
    rx = r.listener(port)
    while True:
        data, _ = rx.recvfrom(256)
        d = parse(data)
        if d:
            latest[key] = d[field]


def vnet_poll():
    while True:
        try:
            s = socket.create_connection((VNET, r.VNET_PORT), timeout=3)
            s.sendall(r.vnet_request("RJ001.REACTOR.TEMP"))
            _tag, val = r.vnet_read_resp(s)
            latest["temp"] = val
            s.close()
        except OSError:
            pass
        time.sleep(2)


def main():
    threading.Thread(target=sub, args=(r.FLNET_PORT, r.flnet_parse, "batch", "value"), daemon=True).start()
    threading.Thread(target=sub, args=(r.TCNET_PORT, r.tcnet_parse, "pressure", "value"), daemon=True).start()
    threading.Thread(target=sub, args=(r.EPA_PORT, r.epa_parse, "conc", "value"), daemon=True).start()
    threading.Thread(target=vnet_poll, daemon=True).start()
    log.info("plant controller online - integrating FL-net / TCnet / EPA / Vnet-IP")
    while True:
        time.sleep(3)
        log.info("reactor=%.1f C (Vnet) | batch=%.0f%% (FL-net) | utility=%.1f kPa (TCnet) | "
                 "product=%.2f%% (EPA)", latest["temp"], latest["batch"],
                 latest["pressure"], latest["conc"])


if __name__ == "__main__":
    main()
