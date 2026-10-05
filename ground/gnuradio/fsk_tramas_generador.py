"""
Generador de tramas: emite, bit a bit (valores 0/1), tramas reales construidas
con ground/scripts/trama.py, cada una precedida de 4 bytes de preámbulo 0xAA.
Los datos simulan un vuelo: el contador sube y la altitud y la presión cambian.
"""
import math
import os
import sys

import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    def __init__(self, ruta_scripts='../scripts'):
        gr.sync_block.__init__(self, name='Generador de tramas', in_sig=None, out_sig=[np.uint8])
        self.ruta_scripts = ruta_scripts
        self.trama = None
        self.contador = 0
        self.bits = np.zeros(0, dtype=np.uint8)

    def start(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base = os.getcwd()
        sys.path.insert(0, os.path.normpath(os.path.join(base, self.ruta_scripts)))
        import trama
        self.trama = trama
        return True

    def nueva_trama(self):
        n = self.contador
        t = self.trama.Telemetria(
            contador=n, tiempo_gps=453_215 + n, latitud=38.1795 + n * 1e-5,
            longitud=-0.9725, altitud_m=12.5 + 5 * n % 3000, presion_pa=101_325 - 6 * n % 30000,
            temperatura_c=23.41, humedad=55.2, acel_mg=(12, -8, 1002),
            giro_dps=(0.5, -1.2, round(10 * math.sin(n / 10), 1)),
            bateria_mv=5000, satelites=9, fix=3)
        self.contador = (n + 1) & 0xFFFF
        datos = bytes([0xAA] * 4) + self.trama.construir_trama(t)
        return np.unpackbits(np.frombuffer(datos, dtype=np.uint8))

    def work(self, input_items, output_items):
        out = output_items[0]
        while len(self.bits) < len(out):
            self.bits = np.concatenate([self.bits, self.nueva_trama()])
        out[:] = self.bits[:len(out)]
        self.bits = self.bits[len(out):]
        return len(out)
