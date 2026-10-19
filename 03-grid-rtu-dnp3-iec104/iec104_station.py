"""IEC 60870-5-104 controlled station - remote substation (TCP/2404).

Answers STARTDT, general interrogation (C_IC_NA_1) and single commands
(C_SC_NA_1), and sends spontaneous measured-value updates (M_ME_NC_1, COT 3).

Information objects:
  IOA 1001 busbar voltage (kV)   IOA 1002 transformer load (MW)
  IOA 1003 OLTC tap position     IOA 2001 feeder breaker (single point / command)
"""
import logging
import socket
import struct
import threading
import time

import iec104_lib as i

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("iec104-stn")

CA = 12
state = dict(v=33.1, mw=8.5, tap=9, breaker=True)
lock = threading.Lock()


def physics():
    import math
    t = 0
    while True:
        with lock:
            if state["breaker"]:
                state["mw"] = max(0.1, 8.5 + 2.0 * math.sin(t / 11.0))
                state["v"] = 33.0 + (state["tap"] - 9) * 0.3 - state["mw"] * 0.02
            else:
                state["mw"], state["v"] = 0.0, 33.6
        t += 1
        time.sleep(1)


def measured_objects():
    with lock:
        return [(1001, i.meas_float(state["v"])),
                (1002, i.meas_float(state["mw"])),
                (1003, i.meas_float(float(state["tap"])))]


def handle(conn):
    ns = [0]
    nr = [0]
    slock = threading.Lock()

    def send_i(asdu):
        with slock:
            conn.sendall(i.i_frame(ns[0], nr[0], asdu))
            ns[0] = (ns[0] + 1) & 0x7FFF

    def spontaneous():
        while True:
            time.sleep(4)
            try:
                send_i(i.asdu(13, 3, CA, measured_objects()))      # COT 3 spontaneous
            except OSError:
                return

    threading.Thread(target=spontaneous, daemon=True).start()
    with conn:
        while True:
            msg = i.parse(conn)
            if not msg:
                return
            if msg["kind"] == "U":
                code = msg["code"]
                if code == i.STARTDT_ACT:
                    log.info("STARTDT act -> con"); conn.sendall(i.u_frame(i.STARTDT_CON))
                elif code == i.STOPDT_ACT:
                    conn.sendall(i.u_frame(i.STOPDT_CON))
                elif code == i.TESTFR_ACT:
                    conn.sendall(i.u_frame(i.TESTFR_CON))
            elif msg["kind"] == "I":
                nr[0] = (msg["ns"] + 1) & 0x7FFF
                if msg["type_id"] == 100:                           # interrogation
                    log.info("general interrogation received")
                    send_i(i.asdu(100, 7, CA, [(0, i.interrogation())]))    # act con
                    send_i(i.asdu(13, 20, CA, measured_objects()))          # COT 20
                    with lock:
                        send_i(i.asdu(1, 20, CA, [(2001, i.single_point(state["breaker"]))]))
                    send_i(i.asdu(100, 10, CA, [(0, i.interrogation())]))   # act term
                elif msg["type_id"] == 45:                          # single command
                    for ioa, payload in i.iter_objects(msg):
                        if ioa == 2001:
                            on = bool(payload[0] & 0x01)
                            with lock:
                                state["breaker"] = on
                            log.warning("single command: breaker -> %s",
                                        "CLOSE" if on else "OPEN")
                            send_i(i.asdu(45, 7, CA, [(2001, i.single_cmd(on))]))


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 2404))
    srv.listen(5)
    threading.Thread(target=physics, daemon=True).start()
    log.info("IEC-104 controlled station CA=%d listening on tcp/2404", CA)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
