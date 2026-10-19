# 01 — Potable Water Treatment (Modbus/TCP + Modbus/TLS)

A small drinking-water treatment plant supervised over **Modbus/TCP (502)**, with
the high-lift distribution pump exposed over **Modbus/TLS (802)** — the same PDUs
wrapped in a TLS session using a self-signed device certificate.

The Modbus stack is implemented from scratch in `modbus_lib.py` (real MBAP header
and function codes 1/2/3/4/5/6/16), so the wire traffic is genuine Modbus while
the lab stays pure standard-library and buildless.

## Process

Raw water is lifted by the **intake pump** through travelling screens into the
treatment train. After filtration it is disinfected by the **chlorine dosing**
skid and stored in the **clearwell**. High-lift **distribution pumps** push
treated water into the city network. The SCADA master holds the clearwell level
inside a 45–80 % band, keeps the free-chlorine residual near 0.8 ppm (regulatory
band 0.5–1.0 ppm), and supplies the city whenever storage allows.

```
intake → screens → filters → [Cl2 dosing] → clearwell → distribution → city
```

## Assets

| Asset | Host / IP | Protocol | Role & functions |
|-------|-----------|----------|------------------|
| `intake-pump` | 172.30.1.10:502 | Modbus/TCP slave | Raw-water intake pump. `CO0` START; `IR0` flow (L/s); `IR1` screen differential |
| `chlorine-dosing` | 172.30.1.11:502 | Modbus/TCP slave | Disinfection metering pump. `CO0` DOSE; `IR0` chlorine residual (ppm); `IR1` day-tank level |
| `clearwell` | 172.30.1.12:502 | Modbus/TCP slave | Treated-water reservoir. `CO0` FILL; `CO1` DRAW; `IR0` level (%) |
| `distribution-pump` | 172.30.1.13:**802** | Modbus/**TLS** slave | High-lift pump to city. `CO0` RUN; `IR0` discharge pressure (kPa) |
| `scada` | 172.30.1.20 | Modbus master | HMI/SCADA poller; runs the supervisory control loop |

## Run

```bash
docker compose up
docker compose down
```

Watch the `s01_scada` container log for the live plant state. The distribution
pump certificate (`modbus_tls.crt` / `modbus_tls.key`) is a throwaway self-signed
pair generated for the lab only.
