# 05 — Oil & Gas Wellsite (WITS Level 0 + HART-IP)

An upstream drilling / wellhead site combining two field protocols:

- **WITS Level 0** over TCP/20000 — the classic ASCII drilling-data feed
  (records bracketed by `&&` / `!!`, 4-digit record/item codes).
- **HART-IP** over TCP/5094 — digital HART over Ethernet, with the real 8-byte
  HART-IP header wrapping token-passing PDUs for command 0 (unique identifier)
  and command 3 (dynamic variables PV/SV/TV/QV).

## Process

The **WITS server** on the rig aggregates surface sensors and streams record 01
(bit depth, hookload, weight-on-bit, RPM, standpipe pressure, flow-in) to the
mudlogging / geology **WITS client**. Separately, a **HART-IP multivariable
transmitter** at the wellhead publishes pressure, temperature, flow and valve
position, polled by a **HART-IP host / asset-management gateway**.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `wits-server` | 172.30.5.10:20000 | WITS0 server | Rig data aggregator; streams record 01 drilling parameters |
| `wits-client` | 172.30.5.11 | WITS0 client | Mudlogging/geology monitor; decodes record/item codes |
| `hart-device` | 172.30.5.12:5094 | HART-IP server | Wellhead transmitter; HART cmd 0 / cmd 3 responses |
| `hart-host` | 172.30.5.13 | HART-IP client | Asset-mgmt gateway; session init + dynamic-variable polling |

## Run

```bash
docker compose up
docker compose down
```

Watch `s05_wits_client` for the drilling feed and `s05_hart_host` for the HART
dynamic variables.
