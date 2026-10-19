# 12 — Process Instrumentation (Foundation Fieldbus HSE)

A single-loop process control system built on **Foundation Fieldbus HSE**
(High Speed Ethernet, TCP/UDP 1089–1091). The lab uses a simplified Field Device
Access (FDA) message to read and write **function-block parameters** (AI OUT,
AO SP/OUT) across devices, so a real AI → PID → AO control loop runs over the bus.

## Process

A flow control loop: the **flow transmitter** (AI block) measures line flow, the
**linking device / DCS** runs a PID block against a 90 m³/h setpoint, and the
**control valve** (AO block) moves its travel to the commanded setpoint. The
transmitter's measured flow depends on the valve travel, so the loop physically
closes and the PID settles the flow at setpoint.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `ff-transmitter` | 172.30.12.10:1089 | FF HSE (AI block) | Flow transmitter; serves AI.OUT |
| `ff-valve` | 172.30.12.11:1090 | FF HSE (AO block) | Control valve; AO.SP write, AO.OUT readback |
| `ff-linking-device` | 172.30.12.12 | FF HSE (PID block) | DCS/linking device; PID flow loop |

## Run

```bash
docker compose up
docker compose down
```

Follow `s12_ff_linking_device` to watch the PID drive the flow to setpoint.
