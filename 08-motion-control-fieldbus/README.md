# 08 — Multi-Axis Motion Control (EtherCAT + Sercos III + Powerlink + MECHATROLINK)

A coordinated 4-axis CNC / motion platform where each servo axis runs a
different real-time motion fieldbus. The managing node (motion controller) runs
a cyclic loop and exchanges the servo PDO (target/actual position, velocity,
torque) with each drive using that drive's protocol framing:

- **EtherCAT** (ethertype 0x88A4) — LRW datagram + working counter
- **Sercos III** (ethertype 0x88CD) — MDT (master) / AT (drive) telegrams
- **Ethernet Powerlink** (ethertype 0x88AB) — PReq / PRes poll cycle
- **MECHATROLINK-III** — POSING (0x34) command / status response

Each cyclic exchange is carried over UDP (EtherCAT on its registered UDP port
34980); the frames carry the real ethertype and command identifiers.

## Process

The controller generates a coordinated sinusoidal motion profile (axes offset by
90°, as in interpolated contouring) and streams each axis its position setpoint
every cycle. Each **servo drive** follows its target with a bounded per-cycle
step (velocity limit), reporting actual position, velocity and torque back.

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `drive-ethercat` | 172.30.8.10:34980/udp | EtherCAT | Axis X servo; LRW PDO exchange |
| `drive-sercos` | 172.30.8.11:35021/udp | Sercos III | Axis Y servo; MDT/AT telegrams |
| `drive-powerlink` | 172.30.8.12:3819/udp | Ethernet Powerlink | Axis Z servo; PReq/PRes |
| `drive-mechatrolink` | 172.30.8.13:35100/udp | MECHATROLINK-III | Axis W servo; POSING command |
| `motion-controller` | 172.30.8.20 | all four (master) | Managing node; coordinated cyclic motion profile |

## Run

```bash
docker compose up
docker compose down
```

Follow `s08_motion_controller` for the coordinated axis positions.
