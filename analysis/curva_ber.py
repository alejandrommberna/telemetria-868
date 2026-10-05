"""
Curva de BER frente a Eb/N0 de la simulación 2-FSK (ground/gnuradio/02_fsk_ber.grc).

Compara la teoría de 2-FSK no coherente con las medidas del receptor simulado
con y sin integrador (filtro adaptado), y calcula las pérdidas de implementación.
Uso:  python curva_ber.py   -> imprime la tabla y guarda curva_ber.png
"""
import math
import numpy as np
import matplotlib.pyplot as plt

FS, RB = 96_000, 9_600            # muestreo y velocidad binaria de la simulación

def ebn0_db(ruido):                # potencia de señal 1, potencia de ruido = amplitud^2
    return 10 * math.log10((FS / RB) / ruido**2)

def ber_teorica(ebn0):             # 2-FSK no coherente: Pb = 1/2 exp(-Eb/N0 / 2)
    return 0.5 * np.exp(-10 ** (np.asarray(ebn0) / 10) / 2)

def ebn0_necesario(ber):           # inversa de la fórmula anterior
    return 10 * math.log10(2 * math.log(1 / (2 * ber)))

# Medidas (100 000 bits por punto). 0 = ningún error en la ventana de medida.
con_integrador = {0.50: 0.0, 0.65: 2.0e-5, 0.80: 6.5e-4, 1.00: 7.4e-3}   # Alejandro, 5 oct 2026
sin_integrador = {0.50: 6.7e-6, 0.65: 7.6e-4, 0.80: 5.9e-3}             # flujo 01 (muestra única)

def tabla(nombre, datos):
    print(f"\n{nombre}")
    print(f"{'ruido':>6} {'Eb/N0':>7} {'BER medida':>11} {'BER teórica':>12} {'pérdida':>8}")
    perdidas = []
    for r, ber in datos.items():
        e = ebn0_db(r)
        if ber > 0:
            p = e - ebn0_necesario(ber)
            perdidas.append(p)
            print(f"{r:6.2f} {e:7.1f} {ber:11.1e} {ber_teorica(e):12.1e} {p:7.1f} dB")
        else:
            print(f"{r:6.2f} {e:7.1f} {'< 1e-5':>11} {ber_teorica(e):12.1e} {'–':>8}")
    print(f"Pérdida de implementación media: {np.mean(perdidas):.1f} dB")

tabla("Con integrador (filtro adaptado)", con_integrador)
tabla("Sin integrador (una muestra por bit)", sin_integrador)

# ---- gráfica ----
AZUL, NARANJA, VERDE = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, REJILLA = "#1f1f1e", "#5f5e58", "#e4e3dc"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": TINTA2,
                     "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2})
fig, ax = plt.subplots(figsize=(7.5, 5))
x = np.linspace(8, 17, 300)
ax.semilogy(x, ber_teorica(x), color=AZUL, lw=2, label="Teoría 2-FSK no coherente", zorder=2)

def puntos(datos, color, marcador, etiqueta):
    xs = [ebn0_db(r) for r, b in datos.items() if b > 0]
    ys = [b for b in datos.values() if b > 0]
    ax.semilogy(xs, ys, marcador, color=color, ms=9, lw=2, label=etiqueta,
                markeredgecolor="white", markeredgewidth=2, zorder=3)

puntos(sin_integrador, NARANJA, "s--", "Medida sin integrador")
puntos(con_integrador, VERDE, "o-", "Medida con integrador")
# punto sin errores: cota superior
e0 = ebn0_db(0.50)
ax.annotate("", xy=(e0, 4e-7), xytext=(e0, 2.5e-6),
            arrowprops=dict(arrowstyle="->", color=VERDE, lw=2))
ax.text(e0 + 0.15, 9e-7, "con integrador:\n0 errores en 10⁵ bits", color=TINTA2, fontsize=9)

ax.axhline(1e-5, color=TINTA2, lw=1.2, ls=(0, (4, 3)), zorder=1)
ax.text(8.1, 1.25e-5, "BER objetivo 10⁻⁵", color=TINTA2, fontsize=9)
ax.set_xlim(8, 17); ax.set_ylim(1e-7, 1e-1)
ax.set_xlabel("Eb/N0 (dB)"); ax.set_ylabel("BER")
ax.set_title("BER frente a Eb/N0 · 2-FSK 9,6 kbit/s (simulación GNU Radio)", color=TINTA, fontsize=11, loc="left")
ax.grid(True, which="major", color=REJILLA, lw=1); ax.grid(True, which="minor", color=REJILLA, lw=0.5, alpha=0.6)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.legend(frameon=False, loc="lower left")
fig.tight_layout(); fig.savefig("curva_ber.png", dpi=150)
print("\nGráfica guardada en curva_ber.png")
