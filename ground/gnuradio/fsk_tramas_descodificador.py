"""
Descodificador de tramas: recibe los bits demodulados (0/1) y las marcas que pone
'Correlate Access Code' al encontrar 1A CF FC 1D. Recorta los 78 bytes siguientes,
corrige con Reed-Solomon, comprueba el CRC (trama.py) y muestra la telemetría.
Salida: porcentaje de tramas perdidas en las últimas 100 (según huecos del contador).
"""
import os
import sys
from collections import deque

import numpy as np
import pmt
from gnuradio import gr

BITS_TRAMA = 78 * 8   # datos + CRC + Reed-Solomon (el ASM ya se ha detectado)


class blk(gr.sync_block):
    def __init__(self, ruta_scripts='../scripts', mostrar_cada=10):
        gr.sync_block.__init__(self, name='Descodificador de tramas', in_sig=[np.uint8], out_sig=[np.float32])
        self.ruta_scripts = ruta_scripts
        self.mostrar_cada = int(mostrar_cada)
        self.trama = None
        self.buffer = np.zeros(0, dtype=np.uint8)
        self.inicio_buffer = 0          # posición absoluta del primer bit del buffer
        self.pendientes = []            # posiciones absolutas donde empiezan tramas
        self.fin_ultima = -1
        self.ultimo_contador = None
        self.historial = deque(maxlen=100)   # 1 = trama recibida, 0 = perdida
        self.ok = self.corregidas = self.descartadas = 0
        self.perdidas_pct = 0.0

    def start(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base = os.getcwd()
        sys.path.insert(0, os.path.normpath(os.path.join(base, self.ruta_scripts)))
        import trama
        self.trama = trama
        return True

    def procesar(self, bits):
        datos = self.trama.ASM + np.packbits(bits).tobytes()
        try:
            t, n_corr = self.trama.descodificar_trama(datos)
        except ValueError as e:
            self.descartadas += 1
            print(f"[RX] trama descartada: {e}")
            return False
        self.ok += 1
        if n_corr:
            self.corregidas += 1
        if self.ultimo_contador is not None:
            hueco = (t.contador - self.ultimo_contador - 1) & 0xFFFF
            if hueco < 1000:
                self.historial.extend([0] * hueco)
        self.historial.append(1)
        self.ultimo_contador = t.contador
        self.perdidas_pct = 100.0 * (1 - sum(self.historial) / len(self.historial))
        if n_corr or t.contador % self.mostrar_cada == 0:
            print(f"[RX] #{t.contador:5d}  lat {t.latitud:.5f}  lon {t.longitud:.5f}  alt {t.altitud_m:7.1f} m  "
                  f"P {t.presion_pa} Pa  T {t.temperatura_c:.2f} C  | RS corrigió {n_corr:2d} B  "
                  f"| OK {self.ok}  con correcciones {self.corregidas}  descartadas {self.descartadas}  "
                  f"perdidas {self.perdidas_pct:.0f} %")
        return True

    def work(self, input_items, output_items):
        entrada = input_items[0]
        n = len(entrada)
        pos0 = self.nitems_read(0)
        for tag in self.get_tags_in_window(0, 0, n):
            if pmt.symbol_to_string(tag.key) == 'trama' and tag.offset > self.fin_ultima:
                self.pendientes.append(tag.offset)
        self.buffer = np.concatenate([self.buffer, entrada])
        while self.pendientes:
            ini = self.pendientes[0]
            fin = ini + BITS_TRAMA
            if fin > self.inicio_buffer + len(self.buffer):
                break
            self.pendientes.pop(0)
            if ini <= self.fin_ultima:
                continue
            a = ini - self.inicio_buffer
            if a >= 0 and self.procesar(self.buffer[a:a + BITS_TRAMA]):
                self.fin_ultima = fin - 1
        conservar = 2 * BITS_TRAMA
        if len(self.buffer) > conservar:
            quitar = len(self.buffer) - conservar
            self.buffer = self.buffer[quitar:]
            self.inicio_buffer += quitar
        output_items[0][:] = self.perdidas_pct
        return n
