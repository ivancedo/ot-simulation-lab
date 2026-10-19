# 10 — Time Synchronization Infrastructure (PTP + NTP)

The timing backbone of a substation / plant: a PTP grandmaster disciplining an
ordinary clock, and an NTP stratum-1 server serving an NTP client.

- **IEEE 1588 PTP** — real PTPv2 headers and Sync / Follow_Up / Delay_Req /
  Delay_Resp messages, as **PTP-over-UDP** (event messages udp/319, general
  messages udp/320).
- **NTP** — 48-byte NTP packets, mode-3 request / mode-4 response, stratum 1.

## Process

Accurate time is critical for sequence-of-events, synchrophasors and protection.
The **grandmaster** broadcasts Sync + Follow_Up every second and answers
Delay_Req; the **slave** runs the two-step offset/delay calculation and
disciplines its clock. In parallel an **NTP server** (GPS-referenced, stratum 1)
answers an **NTP client**, which computes its own offset and round-trip delay.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `ptp-grandmaster` | 172.30.10.10:319/320 udp | PTP (1588) | Stratum-1 master; Sync/Follow_Up + Delay_Resp |
| `ptp-slave` | 172.30.10.11 | PTP (1588) | Ordinary clock; offset/delay calc + discipline |
| `ntp-server` | 172.30.10.12:123 udp | NTP | Stratum-1 server (GPS refid) |
| `ntp-client` | 172.30.10.13 | NTP | Client; offset/delay calculation |

## Run

```bash
docker compose up
docker compose down
```

Follow `s10_ptp_slave` and `s10_ntp_client` for the computed clock offsets.
