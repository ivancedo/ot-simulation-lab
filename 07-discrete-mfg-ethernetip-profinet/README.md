# 07 — Discrete Manufacturing Cell (EtherNet/IP + PROFINET)

A robotic assembly cell running the two dominant industrial-Ethernet stacks:

- **EtherNet/IP (CIP)** — TCP/44818 explicit messaging (RegisterSession,
  GetAttributeSingle on the assembly object, Identity) plus UDP/2222 implicit I/O,
  with the real 24-byte encapsulation header and CPF item list.
- **PROFINET** — RT cyclic frames (ethertype 0x8892, frame ID, cyclic I/O, cycle
  counter, data status) and a DCP Identify exchange, over UDP broadcast.

## Process

The **EtherNet/IP scanner (PLC)** drives a remote-I/O block running a conveyor
and a press: a part is conveyed in, the press cycles, then it retracts. In
parallel, the **PROFINET IO-controller** commands a **pick-and-place robot**
(IO-device) through a pick → place → home choreography using cyclic RT I/O, after
discovering it with DCP Identify.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `enip-adapter` | 172.30.7.10:44818 / 2222 | EtherNet/IP adapter | Conveyor+press remote I/O; assembly + Identity objects |
| `enip-scanner` | 172.30.7.11 | EtherNet/IP scanner | Cell PLC; session, assembly reads, implicit output I/O |
| `profinet-device` | 172.30.7.12:34962/udp | PROFINET IO-device | Pick & place robot; DCP + cyclic input/output |
| `profinet-controller` | 172.30.7.13 | PROFINET IO-controller | Cell PLC; DCP Identify + cyclic robot choreography |

## Run

```bash
docker compose up
docker compose down
```

Follow `s07_enip_scanner` and `s07_profinet_controller` for the two cell cycles.
