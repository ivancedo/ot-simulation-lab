# 03 — Power-Grid Telemetry (DNP3 + IEC 60870-5-104)

Two independent telecontrol links from an electricity-utility control center:

- **DNP3 / IEEE 1815 over TCP (20000)** — a distribution feeder RTU, with real
  data-link framing (0x0564 start octets, CRC-DNP blocks), transport and
  application headers (READ / RESPONSE / DIRECT OPERATE), analog & binary objects.
- **IEC 60870-5-104 (2404)** — a remote substation, with real APCI framing
  (0x68, I/S/U formats, N(S)/N(R) sequence numbers) and ASDUs for measured
  values, single-point status, interrogation and single commands.

## Process

Each remote site reports electrical telemetry to the control center and accepts
supervisory controls. The **DNP3 feeder RTU** measures bus voltage, feeder
current and load, and drives a breaker; the DNP3 master runs a 5 s integrity
poll and periodically trips/closes the breaker. The **IEC-104 substation**
reports busbar voltage, transformer MW and OLTC tap, streams spontaneous
updates, answers general interrogations and accepts single commands to its
feeder breaker.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `dnp3-rtu` | 172.30.3.10:20000 | DNP3 outstation | Feeder telemetry (V/I/MW), breaker & earth status, DIRECT OPERATE control |
| `dnp3-master` | 172.30.3.11 | DNP3 master | Control-center FEP; integrity polls + breaker control |
| `iec104-station` | 172.30.3.12:2404 | IEC-104 controlled station | Substation V/MW/tap + breaker; GI, spontaneous updates, commands |
| `iec104-master` | 172.30.3.13 | IEC-104 controlling station | Control-center SCADA; STARTDT, GI, S-frame acks, single commands |

## Run

```bash
docker compose up
docker compose down
```

Follow `s03_dnp3_master` and `s03_iec104_master` for the decoded telemetry and
the control actions they issue.
