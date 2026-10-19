# 09 — OPC Aggregation Gateway (OPC UA Binary + OPC XML-DA + Classic OPC DA)

A plant data-aggregation gateway / historian that normalises three OPC flavours
from three plant areas into one view:

- **OPC UA Binary** (UA-TCP, tcp/4840) — production line. Real UA-TCP transport
  framing (HEL/ACK/MSG message headers) with a simplified Read service.
- **OPC XML-DA** (SOAP over HTTP, tcp/80) — tank farm. SOAP Read envelopes.
- **Classic OPC DA** — legacy motor MMI. Classic DA runs over DCOM/RPC (no fixed
  port); it is emulated here with an item read/write over TCP.

## Process

Three production areas expose their tags through different-generation OPC servers
— a modern UA binary server (line rate/speed/rejects), a web-services XML-DA
server (tank level/flow/temperature) and a legacy classic-DA server (motor
status/current/speed). The **aggregation gateway** polls all three and produces a
single consolidated plant view, as an OPC historian or SCADA gateway would.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `opcua-binary` | 172.30.9.10:4840 | OPC UA Binary | Production-line server; HEL/ACK + Read |
| `opcua-xml` | 172.30.9.11:80 | OPC XML-DA (SOAP) | Tank-farm server; SOAP Read responses |
| `opc-da` | 172.30.9.12:7766 | Classic OPC DA (emulated) | Legacy motor MMI; item reads |
| `opc-aggregator` | 172.30.9.20 | all three (client) | Gateway/historian; consolidated polling |

## Run

```bash
docker compose up
docker compose down
```

Follow `s09_opc_aggregator` for the consolidated three-source plant view.
