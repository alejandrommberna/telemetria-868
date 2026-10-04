# Documento de control de interfaces (ICD) – borrador v0.1

## 1. Diagrama de bloques

```
SEGMENTO DE VUELO                                   SEGMENTO DE TIERRA
┌──────────────────────────────┐                  ┌─────────────────────────────────────┐
│ GPS NEO-M8N ──UART──┐        │                  │ Yagi 7 dBi (N-H)                     │
│ MPU6050 ────I2C────┤ Heltec  │   869,525 MHz    │   │ adaptador N-M → SMA-H            │
│ BME280 ─────I2C────┤ V3      │ ))))  2-GFSK  (((│   │ cable SMA M-M 1 m (RG316)        │
│ LiPo 3,7 V ─JST────┘ SX1262  │                  │ RTL-SDR V4 ──USB──▶ PC (GNU Radio)   │
│        IPX → pigtail → SMA-H panel → monopolo   │                      │ Python        │
└──────────────────────────────┘                  │ ESP32 ◀──USB serie──┘ (az/el)         │
                                                  │   └─PWM─▶ 2× MG996R (pan-tilt)        │
                                                  │ Alimentación servos: 5 V ≥ 3 A        │
                                                  └─────────────────────────────────────┘
```

## 2. Interfaces físicas

| ID | Desde | Hasta | Tipo | Parámetros |
|---|---|---|---|---|
| IF-01 | SX1262 (Heltec) | Monopolo | RF, 50 Ω | IPX (U.FL) → pigtail RF1.13 15 cm → SMA-H de panel; pérdida ≈ 0,5 dB |
| IF-02 | GPS NEO-M8N | Heltec | UART 3,3 V | 9600 baudios 8N1 (por defecto), NMEA; pines TBD |
| IF-03 | MPU6050 | Heltec | I2C 3,3 V | dirección 0x68, 400 kHz |
| IF-04 | BME280 | Heltec | I2C 3,3 V | dirección 0x76 (0x77 si SDO a VCC) |
| IF-05 | LiPo | Heltec | Conector JST 1,25 mm | 3,7 V nominal; ¡comprobar polaridad antes de conectar! |
| IF-10 | Yagi | RTL-SDR | RF, 50 Ω | N-H → adaptador N-M/SMA-H → cable SMA M-M 1 m → SMA-H del RTL-SDR; pérdida ≈ 1,2 dB |
| IF-11 | RTL-SDR | PC | USB 2.0 | 2,048 Msps |
| IF-12 | PC | ESP32 | USB serie | 115200 baudios, comando `AZ=xxx.x EL=yy.y\n` |
| IF-13 | ESP32 | Servos | PWM 50 Hz | 500–2500 µs; GPIO TBD |
| IF-14 | Fuente 5 V | Servos | DC | ≥ 3 A; **GND común con el ESP32** |

> Nota: el bus I2C de la Heltec V3 ya lo usa la pantalla OLED (0x3C). Se puede compartir el mismo bus o usar un segundo bus I2C; decidir en F2 consultando el pinout oficial de Heltec.

## 3. Formato de la trama

Orden de bytes: **big-endian** (como CCSDS).

| Campo | Bytes | Tipo | Unidad / escala |
|---|---|---|---|
| Preámbulo | 4 | 0xAA… | lo genera el SX1262 |
| ASM (sincronismo) | 4 | 0x1ACFFC1D | – |
| Versión | 1 | uint8 | 0x01 |
| ID del vehículo | 1 | uint8 | 0x42 |
| Contador | 2 | uint16 | +1 por trama |
| Tiempo GPS | 4 | uint32 | s desde 00:00 UTC × 10 |
| Latitud | 4 | int32 | grados × 1e7 |
| Longitud | 4 | int32 | grados × 1e7 |
| Altitud | 4 | int32 | cm |
| Presión | 4 | uint32 | Pa |
| Temperatura | 2 | int16 | °C × 100 |
| Humedad | 2 | uint16 | % × 100 |
| Aceleración X, Y, Z | 6 | 3× int16 | mg |
| Giro X, Y, Z | 6 | 3× int16 | °/s × 10 |
| Batería | 2 | uint16 | mV |
| Satélites | 1 | uint8 | nº |
| Fix GPS | 1 | uint8 | 0 = sin fix, 2 = 2D, 3 = 3D |
| CRC-16-CCITT | 2 | uint16 | polinomio 0x1021, inicial 0xFFFF, sobre versión…fix |
| Paridad RS | 32 | – | RS(255,223) acortado a (78,46) |

**Tamaño:** 44 B de datos + 2 B de CRC = 46 B protegidos → con RS = 78 B → + ASM y preámbulo = **86 B = 688 bits**.

**Tiempo en el aire a 9,6 kbit/s:** 688 / 9600 ≈ **72 ms** → a 1 Hz el ciclo de trabajo es **7,2 %** (cumple el 10 % de REQ-SYS-001).
