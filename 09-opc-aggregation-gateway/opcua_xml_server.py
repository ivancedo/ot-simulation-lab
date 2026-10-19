"""OPC UA / OPC XML-DA server - SOAP over HTTP (port 80). Tank-farm area.

Answers a SOAP Read POST for the tank-farm tags:
  TankLevel (%)   FlowRate (m3/h)   Temperature (degC)
"""
import logging
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("opcua-xml")

tags = {"TankLevel": 62.0, "FlowRate": 140.0, "Temperature": 48.0}
lock = threading.Lock()


def physics():
    t = 0
    while True:
        with lock:
            tags["TankLevel"] = 62 + 8 * math.sin(t / 20.0)
            tags["FlowRate"] = 140 + 20 * math.sin(t / 8.0)
            tags["Temperature"] = 48 + 3 * math.sin(t / 25.0)
        t += 1
        time.sleep(1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="ignore")
        item = next((k for k in tags if k in body), "TankLevel")
        with lock:
            val = tags[item]
        soap = ('<?xml version="1.0"?>'
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
                '<soap:Body><ReadResponse xmlns="http://opcfoundation.org/webservices/XMLDA/1.0/">'
                '<Items><Item ItemName="%s"><Value>%.2f</Value></Item></Items>'
                '</ReadResponse></soap:Body></soap:Envelope>' % (item, val))
        data = soap.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/soap+xml")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    threading.Thread(target=physics, daemon=True).start()
    log.info("OPC XML-DA (SOAP/HTTP) server online on tcp/80")
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()


if __name__ == "__main__":
    main()
