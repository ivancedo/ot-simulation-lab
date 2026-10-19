"""Chlorine disinfection dosing skid (Modbus/TCP slave, unit 1).

CO0 DOSE     - energise the metering pump
IR0 RESIDUAL - free chlorine residual, ppm x100 (regulatory band 0.5-1.0)
IR1 TANK     - sodium hypochlorite day-tank level, % x10
"""
import logging
import threading
import time

import modbus_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("chlorine")

store = m.DataStore()


def physics():
    residual = 0.4   # ppm
    tank = 95.0      # %
    while True:
        dosing = store.co[0]
        residual += 0.08 if dosing else -0.05
        residual = max(0.0, min(2.0, residual))
        if dosing:
            tank = max(0.0, tank - 0.05)
        with store.lock:
            store.ir[0] = int(residual * 100)
            store.ir[1] = int(tank * 10)
        time.sleep(1)


threading.Thread(target=physics, daemon=True).start()
log.info("chlorine dosing online - CO0=DOSE, IR0=residual, IR1=tank")
m.serve(store, port=502)
