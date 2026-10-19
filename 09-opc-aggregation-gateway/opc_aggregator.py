"""OPC aggregation gateway / plant historian client.

Reads three plant areas over three OPC flavours and logs one consolidated view:
  * OPC UA binary (tcp/4840)  - production line
  * OPC XML-DA SOAP (tcp/80)  - tank farm
  * classic OPC DA (tcp/7766) - legacy motor MMI
"""
import logging
import socket
import time

import opc_lib as o

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | %(name)-11s | %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("opc-aggr")

UA_BIN = "172.30.9.10"
UA_XML = "172.30.9.11"
OPC_DA = "172.30.9.12"

SOAP = ('<?xml version="1.0"?><soap:Envelope '
        'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
        '<Read xmlns="http://opcfoundation.org/webservices/XMLDA/1.0/">'
        '<Items><Item ItemName="%s"/></Items></Read></soap:Body></soap:Envelope>')


def ua_connect():
    s = socket.create_connection((UA_BIN, o.UA_PORT), timeout=3)
    s.sendall(o.hello("opc.tcp://%s:4840" % UA_BIN))
    o.read_ua(s)                                     # ACK
    return s


def ua_read(sock, node):
    sock.sendall(o.read_request(node))
    return o.parse_msg(o.read_ua(sock)["body"])["value"]


def xml_read(item):
    body = (SOAP % item).encode()
    s = socket.create_connection((UA_XML, 80), timeout=3)
    s.sendall(b"POST / HTTP/1.1\r\nHost: tankfarm\r\nContent-Type: application/soap+xml\r\n"
              b"Content-Length: %d\r\n\r\n%s" % (len(body), body))
    resp = b""
    while b"</soap:Envelope>" not in resp:
        chunk = s.recv(2048)
        if not chunk:
            break
        resp += chunk
    s.close()
    txt = resp.decode(errors="ignore")
    return float(txt.split("<Value>")[1].split("</Value>")[0])


def da_read(sock, item):
    sock.sendall(("GET %s\n" % item).encode())
    return float(sock.recv(128).split()[-1])


def main():
    ua = ua_connect()
    da = socket.create_connection((OPC_DA, 7766), timeout=3)
    log.info("aggregator connected to UA-binary, XML-DA and classic-DA sources")
    while True:
        try:
            rate = ua_read(ua, 1)
            speed = ua_read(ua, 2)
            level = xml_read("TankLevel")
            flow = xml_read("FlowRate")
            motor = da_read(da, "Motor.Status")
            current = da_read(da, "Motor.Current")
            log.info("UA: rate=%.0f/min speed=%.0f | XML: tank=%.1f%% flow=%.0f | "
                     "DA: motor=%s current=%.1fA", rate, speed, level, flow,
                     "RUN" if motor else "STOP", current)
        except (OSError, IndexError, ValueError) as e:
            log.warning("read error (%s) - reconnecting", e)
            try:
                ua = ua_connect()
                da = socket.create_connection((OPC_DA, 7766), timeout=3)
            except OSError:
                pass
        time.sleep(3)


if __name__ == "__main__":
    main()
