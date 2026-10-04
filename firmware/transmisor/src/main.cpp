// Prueba de placa: escáner del bus I2C interno de la Heltec V3.
// Al principio solo debe aparecer la OLED (0x3C). Con sensores: MPU6050 (0x68), BME280 (0x76).
#include <Arduino.h>
#include <Wire.h>

#define VEXT     36   // a nivel bajo alimenta la OLED y periféricos
#define OLED_RST 21
#define I2C_SDA  17
#define I2C_SCL  18

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Telemetria 868 · prueba de placa ===");

  pinMode(VEXT, OUTPUT);
  digitalWrite(VEXT, LOW);
  pinMode(OLED_RST, OUTPUT);
  digitalWrite(OLED_RST, LOW);
  delay(20);
  digitalWrite(OLED_RST, HIGH);

  Wire.begin(I2C_SDA, I2C_SCL);
}

void loop() {
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
  delay(3000);
}
