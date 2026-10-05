#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: 02 - Medida de BER FSK (telemetria 868)
# Author: Alejandro Berna Mogica
# Description: Medida de BER de 2-FSK 9,6 kbit/s frente a Eb/N0
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
import math
from gnuradio import blocks
import numpy
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
import sip
import threading



class fsk_ber(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "02 - Medida de BER FSK (telemetria 868)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("02 - Medida de BER FSK (telemetria 868)")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "fsk_ber")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 96000
        self.ruido = ruido = 0.5
        self.baud = baud = 9600
        self.taps_lpf = taps_lpf = firdes.low_pass(1, samp_rate, 12000, 4000, window.WIN_HAMMING, 6.76)
        self.ebn0_db = ebn0_db = (10*math.log10(samp_rate/baud/max(ruido,1e-3)**2))
        self.sps = sps = int(samp_rate/baud)
        self.retardo = retardo = (len(taps_lpf)-1)//2
        self.desviacion = desviacion = 4800
        self.ber_teorica = ber_teorica = "%.2e" % (0.5*math.exp(-10**(ebn0_db/10)/2))

        ##################################################
        # Blocks
        ##################################################

        self.throttle = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self._ruido_range = qtgui.Range(0, 1.5, 0.01, 0.5, 200)
        self._ruido_win = qtgui.RangeWidget(self._ruido_range, self.set_ruido, "Amplitud de ruido", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._ruido_win, 0, 0, 1, 2)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.throttle_ref = blocks.throttle( gr.sizeof_float*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.suma = blocks.add_vcc(1)
        self.retardo_ref = blocks.delay(gr.sizeof_float*1, retardo)
        self.repetir = blocks.repeat(gr.sizeof_float*1, sps)
        self.por_dos = blocks.multiply_const_ff(2)
        self.osciloscopio = qtgui.time_sink_f(
            400, #size
            samp_rate, #samp_rate
            "Enviado vs integrado", #name
            2, #number of inputs
            None # parent
        )
        self.osciloscopio.set_update_time(0.10)
        self.osciloscopio.set_y_axis(-2, 2)

        self.osciloscopio.set_y_label('Amplitud', "")

        self.osciloscopio.enable_tags(True)
        self.osciloscopio.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.osciloscopio.enable_autoscale(False)
        self.osciloscopio.enable_grid(False)
        self.osciloscopio.enable_axis_labels(True)
        self.osciloscopio.enable_control_panel(False)
        self.osciloscopio.enable_stem_plot(False)


        labels = ['Bits enviados', 'Salida del integrador', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                self.osciloscopio.set_line_label(i, "Data {0}".format(i))
            else:
                self.osciloscopio.set_line_label(i, labels[i])
            self.osciloscopio.set_line_width(i, widths[i])
            self.osciloscopio.set_line_color(i, colors[i])
            self.osciloscopio.set_line_style(i, styles[i])
            self.osciloscopio.set_line_marker(i, markers[i])
            self.osciloscopio.set_line_alpha(i, alphas[i])

        self._osciloscopio_win = sip.wrapinstance(self.osciloscopio.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._osciloscopio_win, 3, 1, 1, 1)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.muestreo_rx = blocks.keep_m_in_n(gr.sizeof_float, 1, sps, (sps-1))
        self.muestreo_ref = blocks.keep_m_in_n(gr.sizeof_float, 1, sps, (sps//2))
        self.modulador_fsk = analog.frequency_modulator_fc((2*math.pi*desviacion/samp_rate))
        self.menos_uno = blocks.add_const_ff((-1))
        self.media_ber = blocks.moving_average_ff(100000, (1e-5), 4000, 1)
        self.integrador = blocks.moving_average_ff(sps, (1.0/sps), 4000, 1)
        self.fuente_ruido = analog.noise_source_c(analog.GR_GAUSSIAN, ruido, 0)
        self.filtro_paso_bajo = filter.fir_filter_ccf(1, taps_lpf)
        self.filtro_paso_bajo.declare_sample_delay(0)
        self.espectro = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Espectro", #name
            1,
            None # parent
        )
        self.espectro.set_update_time(0.10)
        self.espectro.set_y_axis((-100), 10)
        self.espectro.set_y_label('Relative Gain', 'dB')
        self.espectro.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.espectro.enable_autoscale(False)
        self.espectro.enable_grid(True)
        self.espectro.set_fft_average(0.2)
        self.espectro.enable_axis_labels(True)
        self.espectro.enable_control_panel(False)
        self.espectro.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.espectro.set_line_label(i, "Data {0}".format(i))
            else:
                self.espectro.set_line_label(i, labels[i])
            self.espectro.set_line_width(i, widths[i])
            self.espectro.set_line_color(i, colors[i])
            self.espectro.set_line_alpha(i, alphas[i])

        self._espectro_win = sip.wrapinstance(self.espectro.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._espectro_win, 3, 0, 1, 1)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.errores_float = blocks.char_to_float(1, 1)
        self._ebn0_db_tool_bar = Qt.QToolBar(self)

        if None:
            self._ebn0_db_formatter = None
        else:
            self._ebn0_db_formatter = lambda x: eng_notation.num_to_str(x)

        self._ebn0_db_tool_bar.addWidget(Qt.QLabel("Eb/N0 (dB)"))
        self._ebn0_db_label = Qt.QLabel(str(self._ebn0_db_formatter(self.ebn0_db)))
        self._ebn0_db_tool_bar.addWidget(self._ebn0_db_label)
        self.top_grid_layout.addWidget(self._ebn0_db_tool_bar, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.demodulador_fsk = analog.quadrature_demod_cf((samp_rate/(2*math.pi*desviacion)))
        self.decisor_rx = digital.binary_slicer_fb()
        self.decisor_ref = digital.binary_slicer_fb()
        self.comparador = blocks.xor_bb()
        self.bits = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 2, 100000))), True)
        self._ber_teorica_tool_bar = Qt.QToolBar(self)

        if None:
            self._ber_teorica_formatter = None
        else:
            self._ber_teorica_formatter = lambda x: str(x)

        self._ber_teorica_tool_bar.addWidget(Qt.QLabel("BER teorica (2-FSK no coherente)"))
        self._ber_teorica_label = Qt.QLabel(str(self._ber_teorica_formatter(self.ber_teorica)))
        self._ber_teorica_tool_bar.addWidget(self._ber_teorica_label)
        self.top_grid_layout.addWidget(self._ber_teorica_tool_bar, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.ber_medida = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.ber_medida.set_update_time(0.5)
        self.ber_medida.set_title("BER medida (ultimos 100 000 bits)")

        labels = ['BER', '', '', '', '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.ber_medida.set_min(i, 0)
            self.ber_medida.set_max(i, 0.01)
            self.ber_medida.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.ber_medida.set_label(i, "Data {0}".format(i))
            else:
                self.ber_medida.set_label(i, labels[i])
            self.ber_medida.set_unit(i, units[i])
            self.ber_medida.set_factor(i, factor[i])

        self.ber_medida.enable_autoscale(False)
        self._ber_medida_win = sip.wrapinstance(self.ber_medida.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._ber_medida_win, 2, 0, 1, 2)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.a_float = blocks.char_to_float(1, 1)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.a_float, 0), (self.por_dos, 0))
        self.connect((self.bits, 0), (self.a_float, 0))
        self.connect((self.comparador, 0), (self.errores_float, 0))
        self.connect((self.decisor_ref, 0), (self.comparador, 0))
        self.connect((self.decisor_rx, 0), (self.comparador, 1))
        self.connect((self.demodulador_fsk, 0), (self.integrador, 0))
        self.connect((self.errores_float, 0), (self.media_ber, 0))
        self.connect((self.filtro_paso_bajo, 0), (self.demodulador_fsk, 0))
        self.connect((self.fuente_ruido, 0), (self.suma, 1))
        self.connect((self.integrador, 0), (self.muestreo_rx, 0))
        self.connect((self.integrador, 0), (self.osciloscopio, 1))
        self.connect((self.media_ber, 0), (self.ber_medida, 0))
        self.connect((self.menos_uno, 0), (self.repetir, 0))
        self.connect((self.modulador_fsk, 0), (self.suma, 0))
        self.connect((self.muestreo_ref, 0), (self.decisor_ref, 0))
        self.connect((self.muestreo_rx, 0), (self.decisor_rx, 0))
        self.connect((self.por_dos, 0), (self.menos_uno, 0))
        self.connect((self.repetir, 0), (self.modulador_fsk, 0))
        self.connect((self.repetir, 0), (self.throttle_ref, 0))
        self.connect((self.retardo_ref, 0), (self.muestreo_ref, 0))
        self.connect((self.retardo_ref, 0), (self.osciloscopio, 0))
        self.connect((self.suma, 0), (self.throttle, 0))
        self.connect((self.throttle, 0), (self.espectro, 0))
        self.connect((self.throttle, 0), (self.filtro_paso_bajo, 0))
        self.connect((self.throttle_ref, 0), (self.retardo_ref, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "fsk_ber")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_sps(int(self.samp_rate/self.baud))
        self.set_taps_lpf(firdes.low_pass(1, self.samp_rate, 12000, 4000, window.WIN_HAMMING, 6.76))
        self.set_ebn0_db((10*math.log10(self.samp_rate/self.baud/max(self.ruido,1e-3)**2)))
        self.modulador_fsk.set_sensitivity((2*math.pi*self.desviacion/self.samp_rate))
        self.throttle.set_sample_rate(self.samp_rate)
        self.demodulador_fsk.set_gain((self.samp_rate/(2*math.pi*self.desviacion)))
        self.throttle_ref.set_sample_rate(self.samp_rate)
        self.espectro.set_frequency_range(0, self.samp_rate)
        self.osciloscopio.set_samp_rate(self.samp_rate)

    def get_ruido(self):
        return self.ruido

    def set_ruido(self, ruido):
        self.ruido = ruido
        self.set_ebn0_db((10*math.log10(self.samp_rate/self.baud/max(self.ruido,1e-3)**2)))
        self.fuente_ruido.set_amplitude(self.ruido)

    def get_baud(self):
        return self.baud

    def set_baud(self, baud):
        self.baud = baud
        self.set_sps(int(self.samp_rate/self.baud))
        self.set_ebn0_db((10*math.log10(self.samp_rate/self.baud/max(self.ruido,1e-3)**2)))

    def get_taps_lpf(self):
        return self.taps_lpf

    def set_taps_lpf(self, taps_lpf):
        self.taps_lpf = taps_lpf
        self.set_retardo((len(self.taps_lpf)-1)//2)
        self.filtro_paso_bajo.set_taps(self.taps_lpf)

    def get_ebn0_db(self):
        return self.ebn0_db

    def set_ebn0_db(self, ebn0_db):
        self.ebn0_db = ebn0_db
        Qt.QMetaObject.invokeMethod(self._ebn0_db_label, "setText", Qt.Q_ARG("QString", str(self._ebn0_db_formatter(self.ebn0_db))))
        self.set_ber_teorica("%.2e" % (0.5*math.exp(-10**(self.ebn0_db/10)/2)))

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.repetir.set_interpolation(self.sps)
        self.integrador.set_length_and_scale(self.sps, (1.0/self.sps))
        self.muestreo_rx.set_offset((self.sps-1))
        self.muestreo_rx.set_n(self.sps)
        self.muestreo_ref.set_offset((self.sps//2))
        self.muestreo_ref.set_n(self.sps)

    def get_retardo(self):
        return self.retardo

    def set_retardo(self, retardo):
        self.retardo = retardo
        self.retardo_ref.set_dly(int(self.retardo))

    def get_desviacion(self):
        return self.desviacion

    def set_desviacion(self, desviacion):
        self.desviacion = desviacion
        self.modulador_fsk.set_sensitivity((2*math.pi*self.desviacion/self.samp_rate))
        self.demodulador_fsk.set_gain((self.samp_rate/(2*math.pi*self.desviacion)))

    def get_ber_teorica(self):
        return self.ber_teorica

    def set_ber_teorica(self, ber_teorica):
        self.ber_teorica = ber_teorica
        Qt.QMetaObject.invokeMethod(self._ber_teorica_label, "setText", Qt.Q_ARG("QString", str(self._ber_teorica_formatter(self.ber_teorica))))




def main(top_block_cls=fsk_ber, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
