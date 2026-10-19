"""DLMS/COSEM Head-End System (HES) / data concentrator - client.

Associates with each meter, reads the billing register and instantaneous
values on a schedule, and periodically exercises the remote disconnect /
reconnect ACTION to demonstrate supervisory control of the meter breaker.
"""
import logging
import socket
import time

import dlms_lib as x

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("head-end")

METERS = {"meter-1": "172.30.4.10", "meter-2": "172.30.4.11"}
CLIENT_WPORT = 16


def associate(host):
    s = socket.create_connection((host, x.PORT), timeout=3)
    s.sendall(x.wrap(CLIENT_WPORT, 1, x.aarq()))
    x.read_wpdu(s)                                   # AARE
    return s


def get(sock, name, class_id=3):
    sock.sendall(x.wrap(CLIENT_WPORT, 1, x.get_request(class_id, x.OBIS[name])))
    return x.parse_get_response(x.read_wpdu(sock)["apdu"])


def main():
    conns = {}
    for name, host in METERS.items():
        while name not in conns:
            try:
                conns[name] = associate(host)
                log.info("associated with %s", name)
            except OSError:
                time.sleep(1)

    tick = 0
    while True:
        for name, sock in list(conns.items()):
            try:
                energy = get(sock, "energy_import")
                power = get(sock, "power_import")
                volt = get(sock, "voltage_l1")
                conn_state = get(sock, "disconnect", class_id=70)
                log.info("%s  +A=%.3f kWh  P=%d W  U=%d V  breaker=%s",
                         name, energy / 1000.0, power, volt,
                         "CLOSED" if conn_state else "OPEN")
            except OSError:
                log.warning("%s link lost - re-associating", name)
                try:
                    conns[name] = associate(METERS[name])
                except OSError:
                    pass
        tick += 1
        if tick % 8 == 0:                            # remote disconnect drill on meter-2
            s = conns.get("meter-2")
            if s:
                method = 1 if (tick // 8) % 2 == 1 else 2
                s.sendall(x.wrap(CLIENT_WPORT, 1, x.action_request(70, x.OBIS["disconnect"], method)))
                x.read_wpdu(s)
                log.warning("meter-2 remote %s issued",
                            "DISCONNECT" if method == 1 else "RECONNECT")
        time.sleep(5)


if __name__ == "__main__":
    main()
