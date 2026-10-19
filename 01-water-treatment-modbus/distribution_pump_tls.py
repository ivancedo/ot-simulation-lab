"""High-lift distribution pump to the city network.

Exposes Modbus over TLS (Modbus Security, TCP/802) instead of plain 502 -
the same PDUs wrapped in a TLS session using a self-signed device cert.

CO0 RUN       - run the distribution pump
IR0 PRESSURE  - discharge header pressure, kPa x10
"""
import logging
import threading
import time

import modbus_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("distrib-tls")

store = m.DataStore()


def physics():
    pressure = 80.0  # kPa (static head)
    while True:
        run = store.co[0]
        target = 420.0 if run else 80.0
        pressure += (target - pressure) * 0.35
        with store.lock:
            store.ir[0] = int(pressure * 10)
        time.sleep(1)


threading.Thread(target=physics, daemon=True).start()
log.info("distribution pump online (Modbus/TLS) - CO0=RUN, IR0=pressure")
m.serve(store, port=802, tls=("modbus_tls.crt", "modbus_tls.key"))
