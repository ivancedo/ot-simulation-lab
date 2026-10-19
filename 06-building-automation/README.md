# 06 — Commercial Building Automation (BACnet/IP + KNXnet/IP + LonTalk + Fox)

A commercial building management network running four of the main BAS protocols
side by side under one supervisory workstation.

- **BACnet/IP** (UDP/47808) — AHU controller, confirmed ReadProperty (BVLC+NPDU+APDU)
- **KNXnet/IP** (UDP/3671) — lighting & blinds gateway, cEMI group writes
- **LonTalk / EIA-709** (TCP/1628) — VAV terminal box, network-variable polls
- **Fox** (TCP/1911) — Tridium Niagara station, text hello + point stream

## Process

The BMS workstation runs the building. It reads the **AHU** supply/return air
temperatures and damper position over BACnet, polls the **VAV box** SNVTs over
LonTalk, drives **office/corridor lighting and blinds** over KNX group writes on
an occupancy schedule, and subscribes to the **Niagara JACE** for the chilled
water temperature and occupancy status over Fox.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `bacnet-ahu` | 172.30.6.10:47808/udp | BACnet/IP | AHU; AI1 supply temp, AI2 return temp, AO1 damper |
| `knx-gateway` | 172.30.6.11:3671/udp | KNXnet/IP | Lighting/blinds gateway; connect + group-write telegrams |
| `lon-node` | 172.30.6.12:1628 | LonTalk | VAV box; nvoSpaceTemp / nvoFlowVolume / nvoDamperPos |
| `fox-supervisor` | 172.30.6.13:1911 | Fox (Niagara) | JACE station; hello handshake + point event stream |
| `bms-client` | 172.30.6.20 | all four (client) | BMS workstation; polls/commands every subsystem |

## Run

```bash
docker compose up
docker compose down
```

Follow `s06_bms_client` for the cross-protocol supervision and `s06_knx_gateway`
for the lighting/blind group writes.
