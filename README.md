# OT Protocol Simulation Lab

A collection of **14 self-contained OT network simulations** that together
implement every network-addressable industrial protocol in the SANS ICS
*Industrial Protocols Cheat Sheet* at least once. Each simulation models a
realistic industrial process, speaks the real protocol wire framing, and runs
independently with a single `docker compose up`.

Every service runs on the stock `python:3.12-slim` image with the folder
volume-mounted — **pure Python standard library, no build step, no third-party
packages**. Protocol framing (MBAP, DNP3 link + CRC, IEC-104 APCI, DLMS wrapper,
HART-IP, BVLC, KNXnet/IP cEMI, EtherNet/IP encapsulation, OPC UA-TCP, PTP, NTP,
DoIP, TPKT/MMS, etc.) is implemented from scratch so captures look like the real
thing while the lab stays dependency-free and reproducible.


## Simulations

| # | Simulation | Industrial process | Protocols |
|---|-----------|--------------------|-----------|
| 01 | [water-treatment-modbus](01-water-treatment-modbus/) | Potable water treatment | Modbus/TCP, Modbus/TLS |
| 02 | [electrical-substation-iec61850](02-electrical-substation-iec61850/) | Digital substation bay | IEC 61850 GOOSE / GSSE / SV / MMS, IEEE C37.118 |
| 03 | [grid-rtu-dnp3-iec104](03-grid-rtu-dnp3-iec104/) | Power-grid telemetry | DNP3/TCP, IEC 60870-5-104 |
| 04 | [smart-metering-dlms](04-smart-metering-dlms/) | AMI smart metering | DLMS/COSEM |
| 05 | [oil-gas-wellsite-wits-hart](05-oil-gas-wellsite-wits-hart/) | Drilling wellsite | WITS Level 0, HART-IP |
| 06 | [building-automation](06-building-automation/) | Commercial building BMS | BACnet/IP, KNXnet/IP, LonTalk, Fox (Niagara) |
| 07 | [discrete-mfg-ethernetip-profinet](07-discrete-mfg-ethernetip-profinet/) | Robotic assembly cell | EtherNet/IP (CIP), PROFINET |
| 08 | [motion-control-fieldbus](08-motion-control-fieldbus/) | Multi-axis motion/CNC | EtherCAT, Sercos III, Ethernet Powerlink, MECHATROLINK-III |
| 09 | [opc-aggregation-gateway](09-opc-aggregation-gateway/) | Plant historian gateway | OPC UA Binary, OPC XML-DA, classic OPC DA |
| 10 | [time-sync-infrastructure](10-time-sync-infrastructure/) | Plant/substation timing | PTP (IEEE 1588), NTP, PTP-over-UDP |
| 11 | [iccp-tase2-control-center](11-iccp-tase2-control-center/) | Inter-control-center exchange | ICCP / TASE.2 (MMS) |
| 12 | [process-instrumentation-ff](12-process-instrumentation-ff/) | Flow control loop | Foundation Fieldbus HSE |
| 13 | [vehicle-diagnostics-doip](13-vehicle-diagnostics-doip/) | Automotive diagnostics bench | DoIP, UDS |
| 14 | [plant-realtime-controllers](14-plant-realtime-controllers/) | DCS real-time network | FL-net, Vnet/IP, TCnet, EPA |

## Running a simulation

Each directory is independent:

```bash
cd 01-water-treatment-modbus
docker compose up
docker compose down
```

Each simulation uses its own `172.30.<n>.0/24` subnet, so several can run at
once. Watch the SCADA/master/client container's logs for the live process state.
