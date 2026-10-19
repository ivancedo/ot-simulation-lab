"""DLMS/COSEM smart electricity meter (server, TCP/4059).

One script runs several meters via the METER_ID / BASE_W environment variables.
Serves the application association (AARQ/AARE), GET-Request-Normal for the energy
register and instantaneous values, and the ACTION service on the disconnect
control object (remote disconnect / reconnect).
"""
import logging
import math
import os
import socket
import threading
import time

import dlms_lib as x

METER_ID = os.environ.get("METER_ID", "LGZ0001")
BASE_W = float(os.environ.get("BASE_W", "2200"))
SERVER_WPORT = 1

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("meter")

state = dict(energy_wh=1_250_000, power=BASE_W, voltage=230, current=0, connected=1)
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            if state["connected"]:
                state["power"] = max(0.0, BASE_W * (1 + 0.3 * math.sin(t / 13.0)))
            else:
                state["power"] = 0.0
            state["voltage"] = int(230 + 4 * math.sin(t / 17.0))
            state["current"] = int(state["power"] / max(1, state["voltage"]))
            state["energy_wh"] += int(state["power"] / 3600.0 * 5)   # per 5 s tick
        t += 1
        time.sleep(5)


def value_for(obis):
    with lock:
        if obis == x.OBIS["energy_import"]:
            return state["energy_wh"], x.TAG_DOUBLE_LONG_U
        if obis == x.OBIS["power_import"]:
            return int(state["power"]), x.TAG_DOUBLE_LONG_U
        if obis == x.OBIS["voltage_l1"]:
            return state["voltage"], x.TAG_LONG_U
        if obis == x.OBIS["current_l1"]:
            return state["current"], x.TAG_LONG_U
        if obis == x.OBIS["disconnect"]:
            return state["connected"], x.TAG_UNSIGNED
    return 0, x.TAG_UNSIGNED


def handle(conn, peer):
    with conn:
        while True:
            pdu = x.read_wpdu(conn)
            if not pdu:
                return
            apdu = pdu["apdu"]
            tag = apdu[0]
            if tag == 0x60:                                    # AARQ
                conn.sendall(x.wrap(SERVER_WPORT, pdu["src"], x.aare()))
            elif tag == 0xC0:                                  # GET-Request
                req = x.parse_get_request(apdu)
                val, dtag = value_for(req["obis"])
                conn.sendall(x.wrap(SERVER_WPORT, pdu["src"], x.get_response(val, dtag)))
            elif tag == 0xC3:                                  # ACTION-Request
                req = x.parse_action_request(apdu)
                if req["obis"] == x.OBIS["disconnect"]:
                    with lock:
                        state["connected"] = 1 if req["method"] == 2 else 0
                    log.warning("remote %s via ACTION",
                                "RECONNECT" if state["connected"] else "DISCONNECT")
                conn.sendall(x.wrap(SERVER_WPORT, pdu["src"], x.action_response()))


def main():
    threading.Thread(target=physics, daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", x.PORT))
    srv.listen(5)
    log.info("DLMS meter %s online on tcp/%d (base load %.0f W)", METER_ID, x.PORT, BASE_W)
    while True:
        conn, peer = srv.accept()
        threading.Thread(target=handle, args=(conn, peer), daemon=True).start()


if __name__ == "__main__":
    main()
