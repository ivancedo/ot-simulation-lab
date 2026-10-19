# 02 — Digital Substation (IEC 61850 + IEEE C37.118)

A single feeder bay of a digital substation running the IEC 61850 process- and
station-bus protocols plus an IEEE C37.118 synchrophasor stream:

- **Sampled Values** (SV, 0x88BA) — digitised CT/VT samples from the merging unit
- **GOOSE** (0x88B8) — fast trip / breaker-position dataset from the relay
- **GSSE** (0x88B9) — legacy binary status word
- **MMS** (ISO-on-TCP, tcp/102) — client/server reads of logical-node data
- **IEEE C37.118.2** — synchrophasor data frames from the PMU to the PDC

The L2 publisher/subscriber protocols (SV/GOOSE/GSSE) are emulated as UDP
broadcast on the sim subnet; every frame carries the real ethertype, APPID and
stNum/sqNum/smpCnt counters. MMS uses a genuine TPKT (ISO-on-TCP) header.

## Process

The merging unit samples the feeder currents and voltages and publishes an SV
stream. The protection relay subscribes to it, runs a 1000 A overcurrent element
(PTOC1), and on a fault trips the breaker (XCBR1) — publishing a GOOSE burst that
the merging unit and bay controller both act on. After a dead time the relay
auto-recloses. A periodic primary fault is injected so you can watch the full
protect → trip → reclose cycle. The PMU independently streams positive-sequence
voltage, frequency and ROCOF to the station PDC.

## Assets

| Asset | Host / IP | Protocol(s) | Role & functions |
|-------|-----------|-------------|------------------|
| `merging-unit` | 172.30.2.10 | SV publisher, GOOSE sub | Digitises feeder CT/VT; publishes SV; opens primary current on breaker-open; injects test faults |
| `protection-relay` | 172.30.2.11 | SV sub, GOOSE/GSSE pub, MMS server (102) | PTOC overcurrent, XCBR control, GOOSE trip burst, MMS server for XCBR1.Pos / PTOC1.OpCnt / MMXU1.A |
| `pmu` | 172.30.2.12 | IEEE C37.118 (udp/4712) | Streams synchrophasor data frames (V, f, ROCOF) |
| `bay-controller` | 172.30.2.20 | GOOSE/GSSE sub, MMS client, PDC | Station HMI; logs GOOSE events, polls relay over MMS, concentrates C37.118 |

## Run

```bash
docker compose up
docker compose down
```

Follow `s02_relay` and `s02_bay_controller` to see the overcurrent trip propagate
over GOOSE and the MMS/C37.118 polling.
