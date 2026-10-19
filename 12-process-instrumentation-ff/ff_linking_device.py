"""Foundation Fieldbus HSE linking device / DCS - PID flow controller (TCP/1091).

Reads the transmitter AI.OUT, runs a PID function block against a flow setpoint,
and writes the result to the valve AO.SP each macrocycle, closing the loop.
"""
import logging
import socket
import time

import ff_lib as f

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("ff-dcs")

XMTR = ("172.30.12.10", 1089)
VALVE = ("172.30.12.11", 1090)
SETPOINT = 90.0        # m3/h flow setpoint


def fda_read(addr, block_param, invoke):
    s = socket.create_connection(addr, timeout=3)
    s.sendall(f.frame(f.msg(f.READ_REQ, invoke, *block_param)))
    val = f.parse(f.read_frame(s))["value"]
    s.close()
    return val


def fda_write(addr, block_param, value, invoke):
    s = socket.create_connection(addr, timeout=3)
    s.sendall(f.frame(f.msg(f.WRITE_REQ, invoke, *block_param, value=value)))
    f.read_frame(s)
    s.close()


def main():
    log.info("FF HSE linking device online - PID flow loop, SP=%.0f m3/h", SETPOINT)
    integral = 0.0
    out = 50.0
    invoke = 0
    while True:
        invoke = (invoke + 1) & 0xFF
        try:
            flow = fda_read(XMTR, f.AI_OUT, invoke)
            err = SETPOINT - flow
            integral = max(-50, min(50, integral + err * 0.1))
            out = max(0.0, min(100.0, out + err * 0.3 + integral * 0.1))
            fda_write(VALVE, f.AO_SP, out, invoke)
            log.info("PID: flow=%.1f m3/h  err=%+.1f  -> valve SP=%.1f%%", flow, err, out)
        except OSError:
            log.warning("field device unreachable - retrying")
        time.sleep(2)


if __name__ == "__main__":
    main()
