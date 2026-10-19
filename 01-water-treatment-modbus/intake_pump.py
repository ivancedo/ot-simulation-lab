"""Raw-water intake pump station (Modbus/TCP slave, unit 1).

CO0 START    - run the intake pump
IR0 FLOW     - intake flow, L/s x10
IR1 SCREEN   - travelling-screen differential, mbar x10 (rises with debris)
"""
import logging
import threading
import time

import modbus_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("intake")

store = m.DataStore()


def physics():
    flow = 0.0
    screen = 20.0
    while True:
        run = store.co[0]
        flow += (90 - flow) * 0.3 if run else -flow * 0.3   # L/s
        screen += 0.4 if run else -0.2                       # clogs while flowing
        screen = max(15.0, min(120.0, screen))
        with store.lock:
            store.ir[0] = int(flow * 10)
            store.ir[1] = int(screen * 10)
        time.sleep(1)


threading.Thread(target=physics, daemon=True).start()
log.info("intake pump online - CO0=START, IR0=flow, IR1=screen dP")
m.serve(store, port=502)
