"""
Balance de enlace del sistema de telemetría a 869,525 MHz.

Calcula, frente a la distancia:
  - potencia recibida (dBm)
  - Eb/N0 disponible (dB)
  - margen frente al Eb/N0 requerido (sin y con FEC)
con dos modelos de propagación (espacio libre y tierra plana de 2 rayos),
y además el horizonte radioeléctrico y el radio de la 1.ª zona de Fresnel.

Uso:
    python link_budget.py            -> imprime tabla y guarda link_budget.png
Todos los parámetros están en PARAMS: cámbialos y vuelve a ejecutar.
"""
from dataclasses import dataclass, asdict
import math

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import erfc  # noqa: F401  (por si quieres BER coherente)

C = 299_792_458.0  # m/s
K_DBM_HZ = -174.0  # kT a 290 K en dBm/Hz


@dataclass
class Params:
    # --- Frecuencia y modulación ---
    f_hz: float = 869.525e6        # sub-banda P (869,40–869,65 MHz): 500 mW ERP, 10 % ciclo
    bitrate_bps: float = 9600      # 2-GFSK
    # --- Transmisor (Heltec V3, SX1262) ---
    p_tx_dbm: float = 20.0         # potencia de salida configurada
    l_tx_cable_db: float = 0.5     # pigtail IPX->SMA + conector de panel
    g_tx_dbi: float = 2.0          # monopolo λ/4 (aprox.)
    # --- Receptor (Yagi + RTL-SDR V4) ---
    g_rx_dbi: float = 7.0          # Yagi 868 MHz según fabricante
    l_rx_cable_db: float = 1.2     # 1 m RG316 (~0,9 dB) + adaptador N-SMA (~0,3 dB)
    nf_rx_db: float = 6.0          # figura de ruido estimada del RTL-SDR V4
    # --- Requisitos de demodulación ---
    ebn0_req_nofec_db: float = 13.4  # 2-FSK no coherente, BER = 1e-5 (teórico)
    fec_gain_db: float = 4.0         # ganancia estimada de RS(255,223) acortado
    implementation_loss_db: float = 3.0  # pérdidas reales del demodulador SDR
    fade_margin_target_db: float = 10.0  # margen exigido (REQ-COM-022)
    # --- Geometría ---
    h_tx_m: float = 1.5            # altura del transmisor
    h_rx_m: float = 3.0            # altura de la estación (trípode/terraza)

    @property
    def eirp_dbm(self) -> float:
        return self.p_tx_dbm - self.l_tx_cable_db + self.g_tx_dbi

    @property
    def erp_mw(self) -> float:
        # ERP = EIRP - 2,15 dB
        return 10 ** ((self.eirp_dbm - 2.15) / 10)


def fspl_db(d_m, f_hz):
    """Pérdida en espacio libre (Friis)."""
    return 20 * np.log10(4 * np.pi * d_m * f_hz / C)


def two_ray_db(d_m, f_hz, h_tx_m, h_rx_m):
    """Modelo de tierra plana (2 rayos): a partir de la distancia de ruptura
    la pérdida crece 40 dB/década. Por debajo se usa espacio libre."""
    lam = C / f_hz
    d_break = 4 * h_tx_m * h_rx_m / lam
    pl_2ray = 40 * np.log10(d_m) - 20 * np.log10(h_tx_m * h_rx_m)
    return np.where(d_m < d_break, fspl_db(d_m, f_hz), np.maximum(pl_2ray, fspl_db(d_m, f_hz)))


def radio_horizon_km(h_tx_m, h_rx_m):
    """Horizonte radioeléctrico con k = 4/3."""
    return 4.12 * (math.sqrt(h_tx_m) + math.sqrt(h_rx_m))


def fresnel1_m(d_m, f_hz):
    """Radio de la 1.ª zona de Fresnel en el punto medio."""
    lam = C / f_hz
    return 0.5 * np.sqrt(lam * d_m)


def budget(p: Params, d_m, model="fspl"):
    pl = fspl_db(d_m, p.f_hz) if model == "fspl" else two_ray_db(d_m, p.f_hz, p.h_tx_m, p.h_rx_m)
    pr_dbm = p.eirp_dbm - pl + p.g_rx_dbi - p.l_rx_cable_db
    n0_dbm_hz = K_DBM_HZ + p.nf_rx_db
    ebn0_db = pr_dbm - n0_dbm_hz - 10 * np.log10(p.bitrate_bps)
    req_nofec = p.ebn0_req_nofec_db + p.implementation_loss_db
    req_fec = req_nofec - p.fec_gain_db
    return {
        "pr_dbm": pr_dbm,
        "ebn0_db": ebn0_db,
        "margin_nofec_db": ebn0_db - req_nofec,
        "margin_fec_db": ebn0_db - req_fec,
        "sensitivity_dbm": n0_dbm_hz + 10 * np.log10(p.bitrate_bps) + req_fec,
    }


def main():
    p = Params()
    print("Parámetros:")
    for k, v in asdict(p).items():
        print(f"  {k:28s} {v}")
    print(f"  {'EIRP (dBm)':28s} {p.eirp_dbm:.1f}")
    print(f"  {'ERP (mW)':28s} {p.erp_mw:.0f}  (límite sub-banda P: 500 mW)")

    d = np.logspace(1, np.log10(100e3), 400)  # 10 m – 100 km
    r = budget(p, d)
    r2 = budget(p, d, model="2ray")
    print(f"\nSensibilidad estimada con FEC: {r['sensitivity_dbm']:.1f} dBm")
    print(f"Horizonte radioeléctrico: {radio_horizon_km(p.h_tx_m, p.h_rx_m):.1f} km\n")

    print(f"{'d (km)':>8} {'Pr libre':>9} {'Pr 2 rayos':>11} {'Margen FEC libre':>17} {'Margen FEC 2 rayos':>19} {'Fresnel (m)':>12}")
    for dk in [0.1, 0.5, 1, 2, 5, 10]:
        x = np.array([dk * 1e3])
        a, b = budget(p, x), budget(p, x, model="2ray")
        print(f"{dk:8.1f} {a['pr_dbm'][0]:9.1f} {b['pr_dbm'][0]:11.1f} "
              f"{a['margin_fec_db'][0]:17.1f} {b['margin_fec_db'][0]:19.1f} "
              f"{fresnel1_m(dk * 1e3, p.f_hz):12.1f}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    ax1.semilogx(d / 1e3, r["pr_dbm"], label="Pr – espacio libre")
    ax1.semilogx(d / 1e3, r2["pr_dbm"], label="Pr – tierra plana (2 rayos)")
    ax1.axhline(r["sensitivity_dbm"], ls="--", color="gray", label="Sensibilidad (con FEC)")
    ax1.set_ylabel("dBm")
    ax1.legend()
    ax1.grid(True, which="both", alpha=0.3)

    ax2.semilogx(d / 1e3, r["margin_fec_db"], label="Margen con FEC – espacio libre")
    ax2.semilogx(d / 1e3, r2["margin_fec_db"], label="Margen con FEC – 2 rayos")
    ax2.semilogx(d / 1e3, r2["margin_nofec_db"], label="Margen sin FEC – 2 rayos")
    ax2.axhline(p.fade_margin_target_db, ls="--", color="red", label="Margen exigido (REQ-COM-022)")
    ax2.axvline(radio_horizon_km(p.h_tx_m, p.h_rx_m), ls=":", color="k", label="Horizonte radio")
    ax2.set_xlabel("Distancia (km)")
    ax2.set_ylabel("dB")
    ax2.legend()
    ax2.grid(True, which="both", alpha=0.3)
    fig.suptitle("Balance de enlace – 869,525 MHz, 2-GFSK 9,6 kbps ")
    fig.tight_layout()
    fig.savefig("link_budget.png", dpi=150)
    print("\nGráfica guardada en link_budget.png")


if __name__ == "__main__":
    main()
