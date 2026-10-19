"""Merging Unit (IEC 61850-9-2 Sampled Values publisher).

Digitises the CT/VT secondaries of one feeder bay and multicasts the samples
as an SV stream. Also subscribes to the relay's GOOSE so the primary current
collapses when the breaker opens, and injects a periodic overcurrent fault to
exercise the protection scheme.

SV dataset channels: [Ia Ib Ic In Va Vb Vc Vn]
"""
import logging
import threading
import time

import station_lib as s

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("merging-unit")

SV_ID = "MU01/feeder1"
breaker_closed = True


def watch_goose():
    global breaker_closed
    rx = s.listener(s.GOOSE_PORT)
    while True:
        data, _ = rx.recvfrom(2048)
        try:
            g = s.goose_unpack(data)
            if len(g["bools"]) >= 2:
                breaker_closed = g["bools"][1]
        except Exception:
            pass


def main():
    threading.Thread(target=watch_goose, daemon=True).start()
    tx = s.sender()
    smpcnt = 0
    fault_until = 0
    next_fault = time.time() + 20
    log.info("publishing SV stream '%s' (0x88BA)", SV_ID)

    while True:
        now = time.time()
        if breaker_closed and now > next_fault:
            fault_until = now + 2.0
            next_fault = now + 25
            log.warning("primary fault on feeder 1 - overcurrent injected")
        faulted = now < fault_until and breaker_closed

        if not breaker_closed:
            ia = ib = ic = 0
        elif faulted:
            ia, ib, ic = 3600, 3550, 3580
        else:
            ia, ib, ic = 205, 198, 202
        vn = 0
        va, vb, vc = (63300, 63350, 63280) if breaker_closed else (63500, 63500, 63500)
        inn = (ia + ib + ic) // 50

        payload = s.sv_pack(SV_ID, smpcnt, [ia, ib, ic, inn, va, vb, vc, vn])
        s.publish(tx, s.SV_PORT, payload)
        smpcnt = (smpcnt + 1) % 4000

        if smpcnt % 20 == 0:
            log.info("Ia=%4dA Va=%5dV breaker=%s%s", ia, va,
                     "CLOSED" if breaker_closed else "OPEN",
                     " FAULT" if faulted else "")
        time.sleep(0.05)   # 20 samples/s (scaled down for the lab)


if __name__ == "__main__":
    main()
