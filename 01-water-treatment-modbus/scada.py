"""Water-treatment SCADA master / HMI.

Polls every station once a second over Modbus (TCP for the plant, TLS for the
distribution pump) and runs the supervisory control loop:
  * keep the clearwell level inside 45-80 %
  * hold the free-chlorine residual near 0.8 ppm
  * supply the city while storage allows it
"""
import logging
import time

import modbus_lib as m

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("scada")

INTAKE = "172.30.1.10"
CHLORINE = "172.30.1.11"
CLEARWELL = "172.30.1.12"
DISTRIB = "172.30.1.13"

clients = {
    "intake": m.Client(INTAKE, 502),
    "chlorine": m.Client(CHLORINE, 502),
    "clearwell": m.Client(CLEARWELL, 502),
    "distrib": m.Client(DISTRIB, 802, tls=True),
}


def connect_all():
    for name, c in clients.items():
        while True:
            try:
                c.connect()
                log.info("connected to %s", name)
                break
            except OSError:
                time.sleep(1)


def main():
    connect_all()
    log.info("SCADA online - supervising potable water treatment")
    while True:
        try:
            flow = clients["intake"].read_input_regs(0, 2)[0] / 10.0
            residual = clients["chlorine"].read_input_regs(0, 2)[0] / 100.0
            level = clients["clearwell"].read_input_regs(0, 1)[0] / 10.0
            press = clients["distrib"].read_input_regs(0, 1)[0] / 10.0

            # Intake + clearwell inlet: fill below 60 %, stop above 80 %
            fill = level < 60 or (level < 80 and flow > 5)
            clients["intake"].write_coil(0, fill)
            clients["clearwell"].write_coil(0, fill)

            # Chlorination: bang-bang around the 0.5-1.0 ppm band
            if residual < 0.6:
                clients["chlorine"].write_coil(0, True)
            elif residual > 1.0:
                clients["chlorine"].write_coil(0, False)

            # Distribution: supply the city while storage is healthy
            supply = level > 45
            clients["distrib"].write_coil(0, supply)
            clients["clearwell"].write_coil(1, supply)

            log.info("flow %4.0f L/s | Cl %.2f ppm | clearwell %4.1f%% | head %5.1f kPa | %s",
                     flow, residual, level, press, "SUPPLYING" if supply else "STORING")
        except (OSError, IndexError) as e:
            log.warning("poll error (%s) - reconnecting", e)
            for c in clients.values():
                c.close()
            connect_all()
        time.sleep(1)


if __name__ == "__main__":
    main()
