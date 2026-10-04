# Especificación de requisitos (borrador v0.1)

Formato inspirado en ECSS-E-ST-10-06 (especificación técnica). Cada requisito es **único, medible y verificable**.

Métodos de verificación (ECSS-E-ST-10-02): **T** = ensayo, **A** = análisis, **I** = inspección, **R** = revisión de diseño.

| ID | Requisito | Verif. | Justificación |
|---|---|---|---|
| **Sistema** ||||
| REQ-SYS-001 | El enlace operará en la sub-banda 869,400–869,650 MHz con ERP ≤ 500 mW y ciclo de trabajo ≤ 10 %. | I, A | Normativa SRD (CNAF / ERC 70-03, sub-banda "P"). |
| REQ-SYS-002 | El sistema estará formado por un segmento de vuelo (transmisor) y un segmento de tierra (receptor + seguimiento). | R | Arquitectura. |
| **Transmisor** ||||
| REQ-TX-010 | El transmisor enviará una trama de telemetría a una frecuencia ≥ 1 Hz. | T | Resolución temporal suficiente para trayectoria. |
| REQ-TX-011 | Cada trama incluirá: contador, tiempo GPS, latitud, longitud, altitud, presión, temperatura, aceleración (3 ejes), velocidad angular (3 ejes), tensión de batería y nº de satélites. | I, T | Ver ICD §3. |
| REQ-TX-012 | Modulación 2-GFSK a 9,6 kbit/s. | T | Compromiso alcance / ciclo de trabajo (ver balance de enlace). |
| REQ-TX-013 | Potencia de salida configurable entre −9 y +22 dBm; valor nominal +20 dBm. | T | Permite ensayos conducidos y cumplir REQ-SYS-001. |
| REQ-TX-014 | Autonomía ≥ 2 h con la batería LiPo a 1 Hz. | T | Duración de una prueba de campo. |
| REQ-TX-015 | Masa total del transmisor ≤ 150 g. | I | Simula carga útil ligera. |
| **Comunicaciones** ||||
| REQ-COM-020 | Cada trama llevará palabra de sincronismo de 32 bits (0x1ACFFC1D), CRC-16-CCITT y código Reed-Solomon RS(255,223) acortado. | I, T | Estilo CCSDS 131.0-B. |
| REQ-COM-021 | La tasa de tramas erróneas (FER) será ≤ 1 % con Eb/N0 ≥ 14 dB en ensayo conducido. | T | Curvas de BER (F4). |
| REQ-COM-022 | El margen del enlace será ≥ 10 dB a 2 km con visión directa. | A, T | `analysis/link_budget.py` (≈ 24 dB con modelo de 2 rayos). |
| REQ-COM-023 | La FEC reducirá la BER al menos un orden de magnitud respecto a sin FEC, al mismo Eb/N0. | T | Demostrar ganancia de codificación. |
| **Segmento de tierra** ||||
| REQ-GS-030 | La estación descodificará cada trama y la guardará en CSV con hora UTC de recepción, RSSI y SNR estimados. | T | Trazabilidad de datos. |
| REQ-GS-031 | La estación mostrará en tiempo real la última trama y el estado del enlace. | T | Operación. |
| REQ-GS-032 | Error de apuntamiento de la Yagi ≤ 15° en acimut y elevación. | T | Ancho de haz −3 dB de la Yagi ≈ 60–70°. |
| REQ-GS-033 | El sistema de seguimiento actualizará el apuntamiento con frecuencia ≥ 1 Hz. | T | Coherente con REQ-TX-010. |
| **Antenas** ||||
| REQ-ANT-040 | Las antenas de TX y RX tendrán ROE ≤ 2:1 a 869,525 MHz. | T | Medida con NanoVNA (F5). |
| **Entorno y seguridad** ||||
| REQ-ENV-050 | El transmisor funcionará tras 1 h a −18 °C (congelador). | T | Ensayo térmico simplificado. |
| REQ-SAF-060 | El transmisor nunca emitirá sin antena o carga de 50 Ω; los ensayos conducidos usarán ≥ 30 dB de atenuación. | I | Protege el SX1262 y el RTL-SDR. |

## Pendiente de revisar (TBD)
- REQ-TX-014 y REQ-TX-015 dependen de la batería elegida.
- REQ-COM-021: el umbral de 14 dB se fijará tras la primera medida conducida.
