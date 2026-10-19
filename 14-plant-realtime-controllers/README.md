# 14 — Plant Real-Time Control Network (FL-net + Vnet/IP + TCnet + EPA)

A process-plant / DCS real-time network tying together four vendor control buses
under one integrated controller:

- **FL-net** (OPCN-2, UDP 55000–55004) — token-passing common-memory cyclic broadcast
- **TCnet** (Toshiba, ethertype 0x888B) — cyclic data-block broadcast
- **EPA** (Ethernet for Plant Automation, ethertype 0x88BC) — cyclic channel broadcast
- **Vnet/IP** (Yokogawa, TCP/UDP 5313) — DCS station tag read/response

The ethertype/token/common-memory identifiers are carried in the frames; the
cyclic buses are emulated as UDP broadcast and Vnet/IP as a TCP request/response.

## Process

An integrated plant: a **Vnet/IP DCS station** controls a reactor (temperature),
an **FL-net batch sequencer** publishes batch-step progress on common memory, a
**TCnet** node monitors a utility header pressure, and an **EPA** analyser reports
product concentration. The **plant controller / console** subscribes to the three
cyclic buses and polls the Vnet/IP station, producing one integrated plant view.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `flnet-node` | 172.30.14.10:55000/udp | FL-net | Batch sequencer; token + common-memory broadcast |
| `tcnet-node` | 172.30.14.11:55010/udp | TCnet | Utility monitoring; cyclic block broadcast |
| `epa-device` | 172.30.14.12:55020/udp | EPA | Product analyser; cyclic channel broadcast |
| `vnet-station` | 172.30.14.13:5313 | Vnet/IP | Yokogawa DCS station; reactor-temp tag read |
| `plant-controller` | 172.30.14.20 | all four (client) | Integrated console; subscribes + polls, one plant view |

## Run

```bash
docker compose up
docker compose down
```

Follow `s14_plant_controller` for the integrated four-protocol plant view.
