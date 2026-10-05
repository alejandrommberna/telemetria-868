"""
Trama de telemetría del proyecto (ver docs/02_ICD.md, §3).

Implementación de referencia en Python: construye y descodifica la trama.
El firmware de la Heltec hará exactamente lo mismo en C++, y el receptor de
GNU Radio usará esta misma función de descodificación.

Estructura (big-endian):
    ASM (4 B) | datos (44 B) | CRC-16 (2 B) | paridad Reed-Solomon (32 B)
    El preámbulo (0xAA...) lo añade el SX1262 y no forma parte de la trama.

Uso:
    pip install reedsolo
    python trama.py          -> demostración: construir, corromper y recuperar
"""
import random
import struct
from dataclasses import dataclass, astuple

from reedsolo import RSCodec, ReedSolomonError

ASM = bytes.fromhex("1ACFFC1D")      # Attached Sync Marker (CCSDS 131.0-B)
VERSION = 0x01
ID_VEHICULO = 0x42
RS = RSCodec(32)                     # 32 B de paridad -> corrige hasta 16 bytes erróneos

# Formato de los 44 bytes de datos (">": big-endian)
#   B B H I  i i i  I h H  hhh  hhh  H B B
FORMATO = ">BBHIiiiIhHhhhhhhHBB"
assert struct.calcsize(FORMATO) == 44


@dataclass
class Telemetria:
    contador: int          # uint16, +1 por trama
    tiempo_gps: int        # uint32, s desde 00:00 UTC x 10
    latitud: float         # grados
    longitud: float        # grados
    altitud_m: float       # metros
    presion_pa: int        # Pa
    temperatura_c: float   # °C
    humedad: float         # %
    acel_mg: tuple         # (x, y, z) en mg
    giro_dps: tuple        # (x, y, z) en °/s
    bateria_mv: int        # mV
    satelites: int
    fix: int               # 0 sin fix, 2 = 2D, 3 = 3D


def crc16_ccitt(datos: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16-CCITT (polinomio 0x1021, valor inicial 0xFFFF), bit a bit."""
    for byte in datos:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def empaquetar(t: Telemetria) -> bytes:
    """Telemetría -> 44 bytes de datos."""
    return struct.pack(
        FORMATO, VERSION, ID_VEHICULO, t.contador & 0xFFFF, t.tiempo_gps,
        round(t.latitud * 1e7), round(t.longitud * 1e7), round(t.altitud_m * 100),
        t.presion_pa, round(t.temperatura_c * 100), round(t.humedad * 100),
        *t.acel_mg, *(round(g * 10) for g in t.giro_dps),
        t.bateria_mv, t.satelites, t.fix,
    )


def desempaquetar(datos: bytes) -> Telemetria:
    """44 bytes de datos -> telemetría."""
    v = struct.unpack(FORMATO, datos)
    if v[0] != VERSION or v[1] != ID_VEHICULO:
        raise ValueError(f"versión/ID inesperados: {v[0]:#04x}/{v[1]:#04x}")
    return Telemetria(
        contador=v[2], tiempo_gps=v[3], latitud=v[4] / 1e7, longitud=v[5] / 1e7,
        altitud_m=v[6] / 100, presion_pa=v[7], temperatura_c=v[8] / 100, humedad=v[9] / 100,
        acel_mg=v[10:13], giro_dps=tuple(g / 10 for g in v[13:16]),
        bateria_mv=v[16], satelites=v[17], fix=v[18],
    )


def construir_trama(t: Telemetria) -> bytes:
    """Telemetría -> trama completa de 82 bytes (ASM + datos + CRC + RS)."""
    datos = empaquetar(t)
    protegido = datos + struct.pack(">H", crc16_ccitt(datos))   # 46 B
    return ASM + bytes(RS.encode(protegido))                      # 4 + 78 = 82 B


def descodificar_trama(trama: bytes):
    """Trama (sin preámbulo) -> (Telemetria, nº de bytes corregidos).
    Lanza ValueError si el sincronismo, el Reed-Solomon o el CRC fallan."""
    if trama[:4] != ASM:
        raise ValueError("sin palabra de sincronismo")
    try:
        protegido, _, errores = RS.decode(trama[4:])
    except ReedSolomonError:
        raise ValueError("Reed-Solomon: demasiados errores para corregir")
    datos, crc_rx = bytes(protegido[:44]), struct.unpack(">H", protegido[44:46])[0]
    if crc16_ccitt(datos) != crc_rx:
        raise ValueError("CRC incorrecto")
    return desempaquetar(datos), len(errores)


# ------------------------------------------------------------------ demo
if __name__ == "__main__":
    ejemplo = Telemetria(
        contador=1234, tiempo_gps=453_215, latitud=38.1795, longitud=-0.9725,
        altitud_m=12.5, presion_pa=101_325, temperatura_c=23.41, humedad=55.2,
        acel_mg=(12, -8, 1002), giro_dps=(0.5, -1.2, 0.0),
        bateria_mv=4012, satelites=9, fix=3,
    )
    trama = construir_trama(ejemplo)
    print(f"Trama de {len(trama)} bytes ({len(trama) * 8} bits) + 4 B de preámbulo:")
    for i in range(0, len(trama), 16):
        print("  " + trama[i:i + 16].hex(" ").upper())
    tiempo_aire = (len(trama) + 4) * 8 / 9600
    print(f"Tiempo en el aire a 9,6 kbit/s: {tiempo_aire * 1000:.0f} ms "
          f"-> ciclo de trabajo a 1 Hz: {tiempo_aire * 100:.1f} %\n")

    random.seed(1)
    for n_errores in (0, 5, 16, 17):
        corrupta = bytearray(trama)
        for pos in random.sample(range(4, len(trama)), n_errores):   # no tocamos el ASM
            corrupta[pos] ^= random.randint(1, 255)
        try:
            t, corregidos = descodificar_trama(bytes(corrupta))
            ok = "idéntica" if t == ejemplo else "DIFERENTE"
            print(f"{n_errores:2d} bytes corrompidos -> OK, {corregidos} corregidos por RS, telemetría {ok}")
        except ValueError as e:
            print(f"{n_errores:2d} bytes corrompidos -> trama descartada: {e}")
