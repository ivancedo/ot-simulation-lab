# 11 — Inter-Control-Center Data Exchange (ICCP / TASE.2)

Two electric-utility control centers exchanging real-time grid data over
**ICCP / TASE.2 (IEC 60870-6)**, which runs on **MMS over the ISO-on-TCP stack
(tcp/102)**. The lab uses genuine TPKT framing and simplified MMS service PDUs:
confirmed Read / ReadResponse for bilateral-table points and Information-Report
for the DSTransferSet stream.

## Process

Control Center A publishes its area's operating data — total generation,
tie-line flow, system frequency and Area Control Error (ACE) — to a peer control
center through a bilateral agreement. Center A runs a **DSTransferSet** that
periodically reports the points; Center B also issues **on-demand reads**. This
is exactly how neighbouring ISOs/TSOs share state for interchange scheduling and
AGC.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `control-center-a` | 172.30.11.10:102 | ICCP/TASE.2 server | Owns VCC_A points; DSTransferSet + Read responses |
| `control-center-b` | 172.30.11.11 | ICCP/TASE.2 client | Peer center; receives reports + on-demand reads |

## Run

```bash
docker compose up
docker compose down
```

Follow `s11_iccp_client` for the transfer-set reports and on-demand reads.
