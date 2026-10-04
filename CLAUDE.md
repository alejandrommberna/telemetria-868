# Contexto del proyecto para Claude

Proyecto personal de Alejandro Berna Mogica (Máster en Sistemas Espaciales): enlace de telemetría a 868 MHz
con estación de tierra y seguimiento, que imita el trabajo de un ingeniero de RF de aviónica. Posible TFM.
Responde y documenta siempre en **español**.

## Arquitectura
- **Transmisor:** Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262), GPS NEO-M8N (UART), MPU6050 (I2C 0x68),
  BME280 (I2C 0x76), LiPo 3,7 V, monopolo λ/4 por pigtail IPX→SMA.
- **Tierra:** Yagi 7 dBi 868 MHz → adaptador N-SMA → cable 1 m → RTL-SDR V4 → PC con GNU Radio (radioconda).
- **Seguimiento:** ESP32 DevKit + 2 servos MG996R (pan-tilt), recibe `AZ=xxx.x EL=yy.y\n` por USB serie a 115200.

## Parámetros fijados (ver docs/01_requisitos.md y docs/02_ICD.md)
- 869,525 MHz (sub-banda P: ERP ≤ 500 mW, ciclo de trabajo ≤ 10 %).
- 2-GFSK, 9,6 kbit/s, potencia nominal +20 dBm.
- Trama big-endian: preámbulo + ASM 0x1ACFFC1D + 44 B de datos + CRC-16-CCITT (0x1021, init 0xFFFF)
  + Reed-Solomon RS(255,223) acortado a (78,46). 86 B totales, 72 ms en el aire, 1 Hz.

## Heltec V3: pines conocidos
- OLED e I2C interno: SDA 17, SCL 18, RST 21. Vext (GPIO36) a nivel bajo alimenta la OLED.
- Pines del GPS y bus I2C externo: **por definir** (consultar el pinout oficial de Heltec antes de asignarlos).

## Estructura del repositorio
- `docs/` requisitos (IDs REQ-xxx-nnn, métodos de verificación ECSS T/A/I/R), ICD, informe.
- `analysis/` balance de enlace en Python (`link_budget.py`).
- `firmware/transmisor/` proyecto PlatformIO (env `heltec_v3`).
- `firmware/seguimiento/`, `ground/gnuradio/`, `ground/scripts/`, `tests/`, `data/`.

## Reglas
- Seguridad RF: nunca transmitir sin antena o carga de 50 Ω; ensayos por cable con ≥ 30 dB de atenuación
  (protege la entrada del RTL-SDR).
- Cada cambio relevante debe poder trazarse a un requisito (REQ-…) y mantener el ciclo de trabajo ≤ 10 %.
- Explicar los conceptos de RF de forma didáctica: Alejandro está aprendiendo para entrevistas técnicas.
- Commits con prefijo de fase: `F1: …`, `F2: …`.
