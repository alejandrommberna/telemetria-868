#include "trama.h"
#include <math.h>
#include <string.h>

namespace trama {

static const uint8_t ASM[BYTES_ASM] = {0x1A, 0xCF, 0xFC, 0x1D};
static const uint8_t VERSION = 0x01;
static const uint8_t ID_VEHICULO = 0x42;

// ---------------------------------------------------------------- CRC-16
uint16_t crc16_ccitt(const uint8_t* datos, size_t n, uint16_t crc) {
  for (size_t i = 0; i < n; i++) {
    crc ^= (uint16_t)datos[i] << 8;
    for (int b = 0; b < 8; b++)
      crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

// ---------------------------------------------------------- Reed-Solomon
static uint8_t gf_exp[512];
static uint8_t gf_log[256];
static uint8_t generador[BYTES_PARIDAD + 1];
static bool tablas_listas = false;

static uint8_t gf_mul(uint8_t a, uint8_t b) {
  if (a == 0 || b == 0) return 0;
  return gf_exp[gf_log[a] + gf_log[b]];
}

static void preparar_tablas() {
  // Tablas de exponentes y logaritmos de GF(256) con polinomio primitivo 0x11D
  uint16_t x = 1;
  for (int i = 0; i < 255; i++) {
    gf_exp[i] = (uint8_t)x;
    gf_log[x] = (uint8_t)i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11D;
  }
  for (int i = 255; i < 512; i++) gf_exp[i] = gf_exp[i - 255];

  // Polinomio generador g(x) = (x - a^0)(x - a^1)...(x - a^31)
  uint8_t g[BYTES_PARIDAD + 1] = {1};
  size_t grado = 0;
  for (size_t i = 0; i < BYTES_PARIDAD; i++) {
    uint8_t raiz = gf_exp[i];
    uint8_t nuevo[BYTES_PARIDAD + 1] = {0};
    for (size_t j = 0; j <= grado; j++) {
      nuevo[j] ^= g[j];                     // g * x
      nuevo[j + 1] ^= gf_mul(g[j], raiz);   // g * raiz
    }
    grado++;
    memcpy(g, nuevo, sizeof(g));
  }
  memcpy(generador, g, sizeof(generador));
  tablas_listas = true;
}

void rs_codificar(const uint8_t* mensaje, size_t n, uint8_t* paridad) {
  if (!tablas_listas) preparar_tablas();
  // División polinómica (registro de desplazamiento): resto = paridad
  uint8_t resto[BYTES_PARIDAD] = {0};
  for (size_t i = 0; i < n; i++) {
    uint8_t coef = mensaje[i] ^ resto[0];
    memmove(resto, resto + 1, BYTES_PARIDAD - 1);
    resto[BYTES_PARIDAD - 1] = 0;
    if (coef != 0)
      for (size_t j = 0; j < BYTES_PARIDAD; j++)
        resto[j] ^= gf_mul(generador[j + 1], coef);
  }
  memcpy(paridad, resto, BYTES_PARIDAD);
}

// --------------------------------------------------------- empaquetado
static uint8_t* poner8(uint8_t* p, uint8_t v) { *p++ = v; return p; }
static uint8_t* poner16(uint8_t* p, uint16_t v) { *p++ = v >> 8; *p++ = v; return p; }
static uint8_t* poner32(uint8_t* p, uint32_t v) {
  *p++ = v >> 24; *p++ = v >> 16; *p++ = v >> 8; *p++ = v; return p;
}
// Redondeo igual que Python (round half to even) para que los bytes coincidan
static int32_t redondear(double x) { return (int32_t)nearbyint(x); }

void construir(const Telemetria& t, uint8_t salida[BYTES_TRAMA]) {
  uint8_t* p = salida;
  memcpy(p, ASM, BYTES_ASM);
  p += BYTES_ASM;
  uint8_t* datos = p;

  p = poner8(p, VERSION);
  p = poner8(p, ID_VEHICULO);
  p = poner16(p, t.contador);
  p = poner32(p, t.tiempo_gps);
  p = poner32(p, (uint32_t)redondear(t.latitud * 1e7));
  p = poner32(p, (uint32_t)redondear(t.longitud * 1e7));
  p = poner32(p, (uint32_t)redondear(t.altitud_m * 100));
  p = poner32(p, t.presion_pa);
  p = poner16(p, (uint16_t)(int16_t)redondear(t.temperatura_c * 100));
  p = poner16(p, (uint16_t)redondear(t.humedad * 100));
  for (int i = 0; i < 3; i++) p = poner16(p, (uint16_t)t.acel_mg[i]);
  for (int i = 0; i < 3; i++) p = poner16(p, (uint16_t)(int16_t)redondear(t.giro_dps[i] * 10));
  p = poner16(p, t.bateria_mv);
  p = poner8(p, t.satelites);
  p = poner8(p, t.fix);                      // 44 bytes de datos

  p = poner16(p, crc16_ccitt(datos, BYTES_DATOS));           // + CRC = 46
  rs_codificar(datos, BYTES_DATOS + BYTES_CRC, p);           // + 32 de paridad = 78
}

}  // namespace trama
