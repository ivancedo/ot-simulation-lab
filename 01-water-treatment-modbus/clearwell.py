"""Treated-water clearwell / storage reservoir (Modbus/TCP slave, unit 1).

CO0 FILL   - open the inlet valve from the filters
CO1 DRAW   - open the outlet to the distribution pumps
IR0 LEVEL  - clearwell level, % x10
"""
import logging
import threading
import time

import modbus_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("clearwell")

store = m.DataStore()


def physics():
    level = 55.0  # %
    while True:
        if store.co[0]:          # FILL
            level += 1.6
        if store.co[1]:          # DRAW
            level -= 1.1
        level = max(0.0, min(100.0, level))
        with store.lock:
            store.ir[0] = int(level * 10)
        time.sleep(1)


threading.Thread(target=physics, daemon=True).start()
log.info("clearwell online - CO0=FILL, CO1=DRAW, IR0=level")
m.serve(store, port=502)
