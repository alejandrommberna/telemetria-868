// Trama de telemetría (ver docs/02_ICD.md §3 y ground/scripts/trama.py).
// Debe generar exactamente los mismos bytes que trama.py.
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace trama {

constexpr size_t BYTES_ASM     = 4;
constexpr size_t BYTES_DATOS   = 44;
constexpr size_t BYTES_CRC     = 2;
constexpr size_t BYTES_PARIDAD = 32;   // Reed-Solomon: corrige hasta 16 bytes
constexpr size_t BYTES_TRAMA   = BYTES_ASM + BYTES_DATOS + BYTES_CRC + BYTES_PARIDAD;  // 82

struct Telemetria {
  uint16_t contador;
  uint32_t tiempo_gps;     // s desde 00:00 UTC x 10
  double   latitud;        // grados
  double   longitud;       // grados
  double   altitud_m;
  uint32_t presion_pa;
  double   temperatura_c;
  double   humedad;        // %
  int16_t  acel_mg[3];
  double   giro_dps[3];
  uint16_t bateria_mv;
  uint8_t  satelites;
  uint8_t  fix;            // 0 sin fix, 2 = 2D, 3 = 3D
};

// CRC-16-CCITT (polinomio 0x1021, valor inicial 0xFFFF)
uint16_t crc16_ccitt(const uint8_t* datos, size_t n, uint16_t crc = 0xFFFF);

// Codificación Reed-Solomon sistemática sobre GF(256) (polinomio 0x11D,
// generador 2, primera raíz 0), compatible con reedsolo.RSCodec(32).
// Escribe BYTES_PARIDAD bytes de paridad en 'paridad'.
void rs_codificar(const uint8_t* mensaje, size_t n, uint8_t* paridad);

// Construye la trama completa (ASM + datos + CRC + RS) en 'salida' (82 bytes).
void construir(const Telemetria& t, uint8_t salida[BYTES_TRAMA]);

}  // namespace trama
