"""
gen_gabinete.py - Disposicion mecanica del gabinete industrial y calculo
                  termico de la envolvente.

Genera:
  mech/out/gabinete_frontal.png   vista frontal con todo el equipo montado
  mech/out/gabinete_lateral.png   vista lateral (profundidad, flujo de aire)
  y el calculo de ventilacion forzada necesaria.

    python mech/gen_gabinete.py
"""

import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Rectangle, FancyArrow  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'sim'))
import b2b_params as P                               # noqa: E402

OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({'figure.facecolor': '#ffffff', 'font.size': 8})

# ------------------------------------------------------------- gabinete
# Rittal AE 1180.500 - chapa de acero, 800 x 600 x 300 mm, IP66
W, H, D = 800.0, 600.0, 300.0
MARGIN = 40.0          # margen interior a placa de montaje

# Equipos: (x, y, ancho, alto, etiqueta, color)
EQUIPOS = [
    # --- fila superior: entrada de red y proteccion ---
    (40, 470, 150, 90, 'SECCIONADOR\n+ FUSIBLES\n3x 25 A aR', '#f39c12'),
    (200, 470, 120, 90, 'FILTRO EMC\nSchaffner\nFN3258-30', '#e67e22'),
    (330, 470, 110, 90, 'CONTACTOR K1\nSchneider\nLC1D25', '#e67e22'),
    (450, 470, 110, 90, 'PRECARGA\nR 68 ohm\n+ K2', '#e67e22'),
    (570, 470, 190, 90, 'BORNERAS DE POTENCIA\nPhoenix UK 10 N\nL1 L2 L3 PE', '#95a5a6'),
    # --- fila media: reactancias del LCL ---
    (40, 300, 200, 150, 'REACTANCIA L1 (conv)\n3x 1.5 mH / 30 A\nBlock DPU', '#3498db'),
    (250, 300, 180, 150, 'REACTANCIA L2 (red)\n3x 0.6 mH / 30 A', '#3498db'),
    (440, 300, 150, 150, 'BANCO Cf + Rd\n3x 10 uF 500 VAC\n3x 6.8 ohm 10 W', '#5dade2'),
    # La resistencia de frenado (1.5 kW) va FUERA: dentro de una envolvente
    # IP66 cerrada dispararia la temperatura interna. Aqui solo su bornera.
    (600, 300, 160, 150, 'ESPACIO LIBRE\n(reserva de cableado\ny disipacion)',
     '#bdc3c7'),
    # --- fila inferior: la PCB sobre el disipador ---
    (40, 90, 480, 190, 'PCB CONVERTIDOR 340 x 240 mm\nsobre DISIPADOR '
     'Fischer SK 92\ncon ventilador axial', '#27ae60'),
    (540, 170, 100, 110, 'FUENTE 24 V\nMean Well\nDR-60-24', '#8e44ad'),
    (540, 90, 100, 70, 'PLC / IO\n(opcional)', '#7f8c8d'),
    (660, 90, 100, 190, 'BORNERAS DE\nCONTROL\nPhoenix UT 2,5\n+ carril DIN',
     '#95a5a6'),
    # --- prensaestopas ---
    (40, 30, 120, 40, 'PRENSAESTOPAS\nRED  M32', '#34495e'),
    (200, 30, 120, 40, 'PRENSAESTOPAS\nMOTOR  M32', '#34495e'),
    (360, 30, 120, 40, 'PRENSA. FRENO\nM25', '#34495e'),
    (520, 30, 120, 40, 'PRENSA. SENAL\nM20 x2', '#34495e'),
    (660, 30, 100, 40, 'TIERRA PE\nM8', '#16a085'),
]


def frontal():
    fig, ax = plt.subplots(figsize=(11, 8.6))
    # envolvente
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=3, ec='#2c3e50'))
    ax.add_patch(Rectangle((20, 20), W - 40, H - 40, fill=False, lw=1,
                           ec='#7f8c8d', ls='--'))
    ax.text(W / 2, H + 18,
            'GABINETE  800 x 600 x 300 mm  -  Rittal AE 1180.500  -  IP66',
            ha='center', fontsize=11, weight='bold')
    ax.text(20, H + 5, 'placa de montaje (linea discontinua)', fontsize=7,
            color='#7f8c8d')

    for (x, y, w, h, lbl, c) in EQUIPOS:
        ax.add_patch(Rectangle((x, y), w, h, fc=c, ec='#2c3e50', lw=1,
                               alpha=0.75))
        ax.text(x + w / 2, y + h / 2, lbl, ha='center', va='center',
                fontsize=7, weight='bold', color='white')

    # ventilacion
    ax.add_patch(Rectangle((W - 150, H - 60), 120, 40, fc='#ecf0f1',
                           ec='#2c3e50', lw=1.5))
    ax.text(W - 90, H - 40, 'SALIDA DE AIRE\nfiltro Rittal 3243',
            ha='center', va='center', fontsize=6.5)
    ax.add_patch(Rectangle((30, 20), 120, 40, fc='#ecf0f1', ec='#2c3e50',
                           lw=1.5))
    ax.text(90, 40, 'VENTILADOR CON FILTRO\nRittal SK 3241.100',
            ha='center', va='center', fontsize=6.5)
    ax.add_patch(FancyArrow(120, 75, 0, 180, width=8, color='#3498db',
                            alpha=0.35, length_includes_head=True,
                            head_width=26, head_length=30))
    ax.add_patch(FancyArrow(W - 90, 300, 0, 180, width=8, color='#e74c3c',
                            alpha=0.35, length_includes_head=True,
                            head_width=26, head_length=30))
    ax.text(150, 170, 'aire frio', fontsize=7, color='#2980b9', rotation=90)
    ax.text(W - 60, 380, 'aire caliente', fontsize=7, color='#c0392b',
            rotation=90)

    ax.set_xlim(-40, W + 40)
    ax.set_ylim(-30, H + 45)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'gabinete_frontal.png'), dpi=140)
    plt.close(fig)


def lateral():
    fig, ax = plt.subplots(figsize=(5.5, 8.0))
    ax.add_patch(Rectangle((0, 0), D, H, fill=False, lw=3, ec='#2c3e50'))
    ax.text(D / 2, H + 18, 'CORTE LATERAL  (profundidad 300 mm)',
            ha='center', fontsize=10, weight='bold')
    # placa de montaje
    ax.add_patch(Rectangle((25, 20), 6, H - 40, fc='#7f8c8d', ec='#2c3e50'))
    ax.text(14, H / 2, 'placa de montaje', rotation=90, va='center',
            fontsize=7, color='#7f8c8d')
    piezas = [
        (31, 90, 60, 190, 'DISIPADOR\naletas verticales', '#bdc3c7'),
        (91, 120, 18, 130, 'PCB', '#27ae60'),
        (109, 130, 40, 110, 'condensadores\nde bus', '#2980b9'),
        (31, 300, 120, 150, 'REACTANCIAS LCL', '#3498db'),
        (31, 470, 90, 90, 'PROTECCION\nY MANIOBRA', '#e67e22'),
    ]
    for (x, y, w, h, lbl, c) in piezas:
        ax.add_patch(Rectangle((x, y), w, h, fc=c, ec='#2c3e50', lw=1,
                               alpha=0.8))
        ax.text(x + w / 2, y + h / 2, lbl, ha='center', va='center',
                fontsize=6.5, weight='bold', color='white')
    ax.add_patch(FancyArrow(200, 60, 0, 420, width=14, color='#3498db',
                            alpha=0.28, length_includes_head=True,
                            head_width=40, head_length=40))
    ax.text(230, 260, 'flujo de aire forzado', rotation=90, va='center',
            fontsize=8, color='#2980b9')
    ax.annotate('', xy=(31, 75), xytext=(151, 75),
                arrowprops=dict(arrowstyle='<->', color='#c0392b'))
    ax.text(91, 62, 'aletas + PCB: 120 mm', ha='center', fontsize=7,
            color='#c0392b')
    ax.set_xlim(-30, D + 30)
    ax.set_ylim(-30, H + 45)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'gabinete_lateral.png'), dpi=140)
    plt.close(fig)


def termico():
    """Ventilacion forzada necesaria para el gabinete."""
    # perdidas dentro del gabinete (la resistencia de frenado va fuera)
    p_semi = 210.0        # con C3M0040120K, de sim/run_all.py
    p_mag = 55.0          # reactancias LCL + choke de modo comun
    p_cap = 8.0
    p_aux = 25.0          # fuente 24 V, drivers, control
    p_pre = 0.0           # solo en el arranque
    q = p_semi + p_mag + p_cap + p_aux

    area = 2 * (W * H + W * D + H * D) / 1e6      # m2
    k = 5.5                                        # W/m2K chapa pintada
    dt_nat = q / (area * k)

    t_amb_ext = 35.0
    dt_obj = P.T_A - t_amb_ext                     # 45 - 35 = 10 K
    caudal = 3.1 * q / dt_obj                      # m3/h  (regla IEC)

    print('CALCULO TERMICO DEL GABINETE')
    print('  Perdidas internas:')
    print('    semiconductores (C3M0040120K) .. %6.1f W' % p_semi)
    print('    reactancias LCL + choke CM ..... %6.1f W' % p_mag)
    print('    condensadores .................. %6.1f W' % p_cap)
    print('    auxiliares y control ........... %6.1f W' % p_aux)
    print('    TOTAL .......................... %6.1f W' % q)
    print('  Superficie de la envolvente ...... %6.2f m2' % area)
    print('  Salto termico solo por conveccion  %6.1f K  -> interior %.0f C'
          % (dt_nat, t_amb_ext + dt_nat))
    print('  => INSUFICIENTE: se exige ventilacion forzada')
    print('  Caudal necesario (dT = %.0f K) ..... %6.0f m3/h'
          % (dt_obj, caudal))
    print('  Ventilador elegido: Rittal SK 3241.100 (180 m3/h) -> margen '
          '%.0f %%' % (100 * (180 / caudal - 1)))
    print()
    print('  Disipador de los SiC:')
    print('    Rth_s-a requerida .............. %6.2f C/W' % 0.306)
    print('    Fischer SK 92 / 200 mm + ventilador axial 24 V')
    print('    (con conveccion natural NO se llega: es obligatorio el aire)')
    return q, caudal


if __name__ == '__main__':
    frontal()
    lateral()
    termico()
    print('Figuras en %s' % os.path.relpath(OUT, ROOT))
