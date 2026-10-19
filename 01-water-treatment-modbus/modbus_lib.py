"""Minimal, dependency-free Modbus/TCP implementation (MBAP + common FCs).

Implements the real wire format so the traffic is indistinguishable from a
genuine Modbus device at the protocol level, while staying pure stdlib so the
lab runs with `docker compose up` and no build step.

Supported function codes: 1 (read coils), 2 (read discrete inputs),
3 (read holding regs), 4 (read input regs), 5 (write single coil),
6 (write single reg), 16 (write multiple regs).
"""
import logging
import socket
import ssl
import struct
import threading

log = logging.getLogger("modbus")


class DataStore:
    """4 Modbus tables, each 0..9999. Thread-safe enough for this lab."""

    def __init__(self, size=512):
        self.co = [0] * size   # coils            (RW bits)
        self.di = [0] * size   # discrete inputs  (RO bits)
        self.hr = [0] * size   # holding regs     (RW 16-bit)
        self.ir = [0] * size   # input regs       (RO 16-bit)
        self.lock = threading.Lock()


def _bits_to_bytes(bits):
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def _handle_pdu(store, pdu):
    fc = pdu[0]
    try:
        if fc in (1, 2):
            addr, qty = struct.unpack(">HH", pdu[1:5])
            table = store.co if fc == 1 else store.di
            with store.lock:
                bits = table[addr:addr + qty]
            body = _bits_to_bytes(bits)
            return bytes([fc, len(body)]) + body
        if fc in (3, 4):
            addr, qty = struct.unpack(">HH", pdu[1:5])
            table = store.hr if fc == 3 else store.ir
            with store.lock:
                regs = table[addr:addr + qty]
            return bytes([fc, qty * 2]) + struct.pack(">%dH" % qty, *regs)
        if fc == 5:
            addr, val = struct.unpack(">HH", pdu[1:5])
            with store.lock:
                store.co[addr] = 1 if val == 0xFF00 else 0
            return pdu[:5]
        if fc == 6:
            addr, val = struct.unpack(">HH", pdu[1:5])
            with store.lock:
                store.hr[addr] = val
            return pdu[:5]
        if fc == 16:
            addr, qty = struct.unpack(">HH", pdu[1:5])
            vals = struct.unpack(">%dH" % qty, pdu[6:6 + qty * 2])
            with store.lock:
                store.hr[addr:addr + qty] = list(vals)
            return bytes([fc]) + pdu[1:5]
    except Exception:
        pass
    return bytes([fc | 0x80, 0x02])  # illegal data address


def serve(store, host="0.0.0.0", port=502, tls=None):
    """Blocking Modbus/TCP server. `tls` = (certfile, keyfile) for Modbus/TLS."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(8)
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=tls[0], keyfile=tls[1])
        srv = ctx.wrap_socket(srv, server_side=True)
        log.info("Modbus/TLS listening on %s:%d", host, port)
    else:
        log.info("Modbus/TCP listening on %s:%d", host, port)

    while True:
        try:
            conn, addr = srv.accept()
        except ssl.SSLError:
            continue
        threading.Thread(target=_client, args=(conn, store), daemon=True).start()


def _client(conn, store):
    with conn:
        while True:
            hdr = _recvn(conn, 7)
            if not hdr:
                return
            tid, pid, length, unit = struct.unpack(">HHHB", hdr)
            pdu = _recvn(conn, length - 1)
            if not pdu:
                return
            resp = _handle_pdu(store, pdu)
            conn.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)


def _recvn(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


class Client:
    """Tiny Modbus/TCP (or TLS) master client used by the SCADA poller."""

    def __init__(self, host, port=502, unit=1, tls=False):
        self.host, self.port, self.unit, self.tls = host, port, unit, tls
        self.sock = None
        self.tid = 0

    def connect(self):
        s = socket.create_connection((self.host, self.port), timeout=3)
        if self.tls:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(s, server_hostname=self.host)
        self.sock = s

    def _txn(self, pdu):
        if self.sock is None:
            self.connect()
        self.tid = (self.tid + 1) & 0xFFFF
        self.sock.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu)
        hdr = _recvn(self.sock, 7)
        _, _, length, _ = struct.unpack(">HHHB", hdr)
        return _recvn(self.sock, length - 1)

    def read_input_regs(self, addr, qty):
        r = self._txn(struct.pack(">BHH", 4, addr, qty))
        return list(struct.unpack(">%dH" % qty, r[2:2 + qty * 2]))

    def read_holding_regs(self, addr, qty):
        r = self._txn(struct.pack(">BHH", 3, addr, qty))
        return list(struct.unpack(">%dH" % qty, r[2:2 + qty * 2]))

    def write_coil(self, addr, on):
        self._txn(struct.pack(">BHH", 5, addr, 0xFF00 if on else 0x0000))

    def write_reg(self, addr, val):
        self._txn(struct.pack(">BHH", 6, addr, val & 0xFFFF))

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
