# 04 — Smart Metering / AMI (DLMS/COSEM)

An Advanced Metering Infrastructure segment: two **DLMS/COSEM** smart electricity
meters (IEC 62056) and a **Head-End System** that reads them over TCP/4059.

The transport is the real DLMS *wrapper* header (version 0x0001, source/
destination wPort, length). On top of it the lab runs a simplified but faithful
xDLMS exchange: AARQ/AARE application association, GET-Request-Normal addressing
COSEM objects by class-id + OBIS + attribute, and the ACTION service on the
disconnect-control object.

## Process

The HES (data concentrator) associates with each meter, reads the billing
register `1.0.1.8.0.255` (+A active energy) plus instantaneous power, voltage and
breaker state on a 5 s schedule, and periodically issues a **remote disconnect /
reconnect** to meter-2's internal breaker — the same capability that makes AMI a
sensitive attack surface. Each meter integrates energy from its live load.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `meter-1` | 172.30.4.10:4059 | DLMS/COSEM server | Residential meter (2.2 kW base); energy/power/voltage/current registers |
| `meter-2` | 172.30.4.11:4059 | DLMS/COSEM server | Larger meter (3.6 kW base); same registers + remotely operated breaker |
| `head-end` | 172.30.4.20 | DLMS/COSEM client | HES/DC: association, scheduled GET reads, remote disconnect ACTION |

## Run

```bash
docker compose up
docker compose down
```

Watch `s04_head_end` for the meter readings and the periodic disconnect drill on
meter-2.
