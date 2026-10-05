// Transmisor de telemetría – Heltec WiFi LoRa 32 V3
// Construye la trama (igual que ground/scripts/trama.py) y la transmite una vez
// por segundo con el SX1262 en 2-GFSK a 869,525 MHz y 9,6 kbit/s.
//
// ¡SEGURIDAD! (REQ-SAF-060) No encender nunca sin antena o carga de 50 Ω en el
// conector SMA. Para ensayos por cable con el RTL-SDR: atenuador de 30 dB.
#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <RadioLib.h>
#include "trama.h"

// ---------------------------------------------------------------- parámetros
static const float    FRECUENCIA_MHZ = 869.525;   // sub-banda P (REQ-SYS-001)
static const float    BITRATE_KBPS   = 9.6;       // REQ-TX-012
static const float    DESVIACION_KHZ = 4.8;       // igual que la simulación de GNU Radio
static const float    RX_BW_KHZ      = 39.0;      // solo afecta a recepción
static const int8_t   POTENCIA_DBM   = 2;         // BAJA para pruebas de mesa. Nominal: 20 (REQ-TX-013)
static const uint16_t PREAMBULO_BITS = 32;        // 4 bytes 0xAA
static const float    TCXO_V         = 1.8;       // la Heltec V3 lleva TCXO a 1,8 V
static const uint32_t PERIODO_MS     = 1000;      // 1 trama por segundo (REQ-TX-010)

// --------------------------------------------------------- pines Heltec V3
#define VEXT     36   // a nivel bajo alimenta la OLED y periféricos
#define OLED_RST 21
#define I2C_SDA  17
#define I2C_SCL  18
#define LORA_NSS   8
#define LORA_SCK   9
#define LORA_MOSI 10
#define LORA_MISO 11
#define LORA_RST  12
#define LORA_BUSY 13
#define LORA_DIO1 14

SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
static uint16_t contador = 0;

static void escanear_i2c() {
  Serial.println("Buscando dispositivos I2C...");
  int n = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  Encontrado en 0x%02X\n", addr);
      n++;
    }
  }
  Serial.printf("Total: %d\n\n", n);
}

// Comprueba el código que devuelven las funciones de RadioLib (0 = correcto)
static void comprobar(int16_t estado, const char* que) {
  if (estado == RADIOLIB_ERR_NONE) {
    Serial.printf("  %-28s OK\n", que);
    return;
  }
  Serial.printf("  %-28s ERROR %d\n", que, estado);
  Serial.println("Radio detenida. Revisa el código de error en la documentación de RadioLib.");
  while (true) delay(1000);
}

static void configurar_radio() {
  Serial.println("Configurando SX1262 en modo FSK:");
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  comprobar(radio.beginFSK(FRECUENCIA_MHZ, BITRATE_KBPS, DESVIACION_KHZ, RX_BW_KHZ,
                           POTENCIA_DBM, PREAMBULO_BITS, TCXO_V), "beginFSK");
  comprobar(radio.setDataShaping(RADIOLIB_SHAPING_0_5), "filtro gaussiano BT=0,5");

  // El SX1262 envía: preámbulo + palabra de sincronismo + carga útil.
  // Usamos el ASM 1A CF FC 1D como palabra de sincronismo, y como carga los 78 bytes
  // restantes de la trama. En el aire queda exactamente la trama del ICD.
  uint8_t asm_[] = {0x1A, 0xCF, 0xFC, 0x1D};
  comprobar(radio.setSyncWord(asm_, sizeof(asm_)), "sincronismo 1A CF FC 1D");
  comprobar(radio.fixedPacketLengthMode(trama::BYTES_TRAMA - trama::BYTES_ASM), "longitud fija 78 B");
  comprobar(radio.setCRC(0), "CRC del chip desactivado");      // ya llevamos CRC-16 + RS
  comprobar(radio.setWhitening(false), "blanqueo desactivado");
  Serial.printf("  %.3f MHz · %.1f kbit/s · desviación %.1f kHz · %d dBm\n\n",
                FRECUENCIA_MHZ, BITRATE_KBPS, DESVIACION_KHZ, POTENCIA_DBM);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Telemetria 868 · transmisor ===");

  pinMode(VEXT, OUTPUT);
  digitalWrite(VEXT, LOW);
  pinMode(OLED_RST, OUTPUT);
  digitalWrite(OLED_RST, LOW);
  delay(20);
  digitalWrite(OLED_RST, HIGH);
  Wire.begin(I2C_SDA, I2C_SCL);
  escanear_i2c();

  Serial.println("AVISO: comprueba que hay antena o carga de 50 ohm. Transmite en 5 s...");
  delay(5000);
  configurar_radio();
}

void loop() {
  uint32_t inicio = millis();

  // Datos simulados hasta conectar el GPS y los sensores
  trama::Telemetria t = {};
  t.contador      = contador;
  t.tiempo_gps    = millis() / 100;
  t.latitud       = 38.1795;
  t.longitud      = -0.9725;
  t.altitud_m     = 12.5;
  t.presion_pa    = 101325;
  t.temperatura_c = 23.41;
  t.humedad       = 55.2;
  t.acel_mg[2]    = 1000;
  t.bateria_mv    = 5000;                    // alimentado por USB

  uint8_t buf[trama::BYTES_TRAMA];
  trama::construir(t, buf);

  uint32_t t0 = micros();
  int16_t estado = radio.transmit(buf + trama::BYTES_ASM, trama::BYTES_TRAMA - trama::BYTES_ASM);
  uint32_t aire_us = micros() - t0;

  if (estado == RADIOLIB_ERR_NONE) {
    Serial.printf("TX #%u  %u ms en el aire  | ", contador, (unsigned)(aire_us / 1000));
    for (size_t i = 0; i < 12; i++) Serial.printf("%02X ", buf[i]);
    Serial.println("...");
  } else {
    Serial.printf("TX #%u ERROR %d\n", contador, estado);
  }

  contador++;
  uint32_t transcurrido = millis() - inicio;
  if (transcurrido < PERIODO_MS) delay(PERIODO_MS - transcurrido);
}
