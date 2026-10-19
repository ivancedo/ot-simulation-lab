# 13 — Vehicle Diagnostics Test Bench (DoIP + UDS)

An automotive end-of-line / workshop diagnostics setup over **DoIP (ISO 13400,
TCP/UDP 13400)** carrying **UDS (ISO 14229)** services. The DoIP gateway fronts
the in-vehicle network (the "CAN" side) and routes diagnostic messages to the
ECUs by logical address.

- **DoIP** — real generic header (version 0x02 + inverse, payload type, length),
  vehicle identification (UDP), routing activation (TCP), diagnostic message/ack.
- **UDS** — DiagnosticSessionControl (0x10), ReadDataByIdentifier (0x22),
  ReadDTCInformation (0x19), TesterPresent (0x3E).

## Process

The **tester** (scan tool) broadcasts a vehicle-identification request, activates
a routing session with the **DoIP gateway**, then runs a UDS scan: read VIN, open
an extended session, read live engine data (RPM, coolant) and read stored DTCs.
The gateway forwards each UDS request to the addressed **ECU** (engine or body)
over the internal vehicle bus and wraps the response back into DoIP.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `doip-gateway` | 172.30.13.10:13400 | DoIP | Vehicle gateway; identification, routing activation, UDS routing |
| `ecu-engine` | 172.30.13.11 (addr 0x1001) | UDS | Engine ECU; VIN, live RPM/coolant, DTC P0171 |
| `ecu-body` | 172.30.13.12 (addr 0x1002) | UDS | Body ECU; sessions, data identifiers |
| `tester` | 172.30.13.20 | DoIP + UDS | Scan tool; identification + UDS diagnostic sequence |

## Run

```bash
docker compose up
docker compose down
```

Follow `s13_tester` for the UDS scan results and `s13_doip_gateway` for the
routing.
