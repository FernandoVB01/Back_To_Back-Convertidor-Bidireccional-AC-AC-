"""
sim_svpwm.py - Diagrama de sectores y vectores del SVPWM.

Lo importante: el hexagono, el lugar geometrico y los ciclos de trabajo NO
se dibujan con una formula de libro, sino llamando a la MISMA funcion
svpwm() que corre en el STM32 (fw/verify/control_ref.py, transliteracion
literal de fw/Core/Inc/b2b_control.h). Si la implementacion del firmware
estuviera mal, el dibujo saldria deformado.

  26  Hexagono: 6 vectores activos + 2 nulos, 6 sectores, circulo inscrito
      (limite lineal) y lugar geometrico que genera el codigo real.
  27  Ciclos de trabajo vs angulo (la "silla" de la inyeccion de secuencia
      cero) y el patron de conmutacion de 7 segmentos en un periodo.
"""

import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt              # noqa: E402
from matplotlib.patches import Polygon, Circle, FancyArrow   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'fw', 'verify'))

import b2b_params as P                       # noqa: E402
import control_ref as CR                     # noqa: E402

OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({'figure.facecolor': '#ffffff', 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})

AZUL, VERDE, ROJO, NARANJA, MORADO, GRIS = (
    '#1f6feb', '#16a34a', '#c0392b', '#e67e22', '#8e44ad', '#7f8c8d')

VDC = P.V_DC
R_HEX = 2.0 / 3.0 * VDC          # radio del hexagono (vector activo)
R_INS = VDC / math.sqrt(3.0)     # circulo inscrito = limite lineal

# Los 8 estados del inversor. 1 = rama al bus +, 0 = rama al bus -.
ESTADOS = [('V0', (0, 0, 0)), ('V1', (1, 0, 0)), ('V2', (1, 1, 0)),
           ('V3', (0, 1, 0)), ('V4', (0, 1, 1)), ('V5', (0, 0, 1)),
           ('V6', (1, 0, 1)), ('V7', (1, 1, 1))]


def vector_de_estado(sw):
    """alpha-beta que produce un estado de conmutacion (Clarke invariante
    en amplitud)."""
    va, vb, vc = [(s - 0.5) * VDC for s in sw]
    al = (2.0 * va - vb - vc) / 3.0
    be = (vb - vc) / math.sqrt(3.0)
    return al, be


def salida_real(vref_mag, ang):
    """Pasa la consigna por el svpwm() DEL FIRMWARE y reconstruye el vector
    que realmente sale. Sirve para comprobar la implementacion."""
    al = vref_mag * math.cos(ang)
    be = vref_mag * math.sin(ang)
    da, db, dc = CR.svpwm(al, be, VDC)
    va, vb, vc = [(d - 0.5) * VDC for d in (da, db, dc)]
    ral = (2.0 * va - vb - vc) / 3.0
    rbe = (vb - vc) / math.sqrt(3.0)
    return ral, rbe


# =====================================================================
# 26  Hexagono, sectores y vectores
# =====================================================================
def hexagono():
    fig, ax = plt.subplots(figsize=(7.6, 7.6))

    # hexagono
    act = [vector_de_estado(sw) for _n, sw in ESTADOS[1:7]]
    orden = [0, 1, 2, 3, 4, 5]
    verts = [act[i] for i in orden]
    ax.add_patch(Polygon(verts, closed=True, fill=False, lw=2.0,
                         edgecolor=AZUL))

    # sectores
    for k in range(6):
        a0 = math.radians(60 * k)
        a1 = math.radians(60 * (k + 1))
        ax.add_patch(Polygon([(0, 0),
                              (R_HEX * math.cos(a0), R_HEX * math.sin(a0)),
                              (R_HEX * math.cos(a1), R_HEX * math.sin(a1))],
                             closed=True, alpha=0.06,
                             facecolor=[AZUL, VERDE, NARANJA, ROJO, MORADO,
                                        GRIS][k]))
        am = math.radians(60 * k + 30)
        ax.text(R_HEX * 0.55 * math.cos(am), R_HEX * 0.55 * math.sin(am),
                'S%d' % (k + 1), ha='center', va='center', fontsize=13,
                color=GRIS, weight='bold', alpha=0.8)

    # vectores activos
    for i, (nombre, sw) in enumerate(ESTADOS[1:7]):
        x, y = vector_de_estado(sw)
        ax.add_patch(FancyArrow(0, 0, x, y, width=3.5, color=AZUL,
                                length_includes_head=True, head_width=22,
                                head_length=28, alpha=0.85))
        r = 1.14
        ax.text(x * r, y * r, '$%s$\n(%d%d%d)' % (nombre, *sw),
                ha='center', va='center', fontsize=9.5, color=AZUL,
                weight='bold')

    # vectores nulos
    ax.plot(0, 0, 'o', ms=11, color=ROJO, zorder=5)
    ax.text(0, -92, '$V_0$(000) / $V_7$(111)\nvectores nulos', ha='center',
            fontsize=8.5, color=ROJO, weight='bold')

    # circulos
    ax.add_patch(Circle((0, 0), R_INS, fill=False, lw=1.8, ls='--',
                        edgecolor=VERDE))
    ax.add_patch(Circle((0, 0), R_HEX, fill=False, lw=1.0, ls=':',
                        edgecolor=GRIS))

    # lugar geometrico que produce el CODIGO REAL, en el limite lineal
    ang = np.linspace(0, 2 * np.pi, 720)
    sal = np.array([salida_real(R_INS, a) for a in ang])
    ax.plot(sal[:, 0], sal[:, 1], lw=3.2, color=VERDE, alpha=0.35,
            label='salida real de svpwm() a $V_{dc}/\\sqrt{3}$')

    # sobremodulacion: la consigna se recorta contra el hexagono
    sal2 = np.array([salida_real(R_HEX * 0.98, a) for a in ang])
    ax.plot(sal2[:, 0], sal2[:, 1], lw=1.4, color=ROJO, ls='-',
            label='sobremodulacion: se recorta al hexagono')

    # ejemplo de descomposicion en un sector
    ang_ej = math.radians(28)
    vref = R_INS * 0.82
    vx, vy = vref * math.cos(ang_ej), vref * math.sin(ang_ej)
    ax.add_patch(FancyArrow(0, 0, vx, vy, width=4.5, color=MORADO,
                            length_includes_head=True, head_width=26,
                            head_length=30, zorder=6))
    # T1*V1 y T2*V2
    t1 = vref * math.sin(math.radians(60) - ang_ej) / \
        (R_HEX * math.sin(math.radians(60)))
    t2 = vref * math.sin(ang_ej) / (R_HEX * math.sin(math.radians(60)))
    v1 = np.array(vector_de_estado((1, 0, 0)))
    v2 = np.array(vector_de_estado((1, 1, 0)))
    ax.plot([0, t1 * v1[0]], [0, t1 * v1[1]], lw=2.0, color=MORADO, ls='--')
    ax.plot([t1 * v1[0], t1 * v1[0] + t2 * v2[0]],
            [t1 * v1[1], t1 * v1[1] + t2 * v2[1]], lw=2.0, color=MORADO,
            ls='--')
    ax.text(vx * 1.06, vy * 1.06, '$V_{ref}$', fontsize=11, color=MORADO,
            weight='bold')
    ax.text(t1 * v1[0] * 0.55, t1 * v1[1] + 22, '$T_1 V_1$', fontsize=9.5,
            color=MORADO, weight='bold')
    ax.text(t1 * v1[0] + t2 * v2[0] * 0.45,
            t1 * v1[1] + t2 * v2[1] * 0.5 + 8, '$T_2 V_2$', fontsize=9,
            color=MORADO)

    ax.annotate('circulo inscrito  $V_{dc}/\\sqrt{3}$ = %.0f V\n'
                'LIMITE DE MODULACION LINEAL' % R_INS,
                (R_INS * math.cos(math.radians(250)),
                 R_INS * math.sin(math.radians(250))),
                xytext=(-600, -560), fontsize=9, color=VERDE,
                arrowprops=dict(arrowstyle='->', color=VERDE, lw=1.2))
    ax.annotate('vector activo  $2V_{dc}/3$ = %.0f V' % R_HEX,
                (R_HEX * math.cos(math.radians(200)),
                 R_HEX * math.sin(math.radians(200))),
                xytext=(-640, -330), fontsize=9, color=GRIS,
                arrowprops=dict(arrowstyle='->', color=GRIS, lw=1.0))

    lim = R_HEX * 1.42
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect('equal')
    ax.set_xlabel(r'$V_\alpha$ [V]')
    ax.set_ylabel(r'$V_\beta$ [V]')
    ax.set_title('SVPWM: hexagono, 6 sectores y 8 estados de conmutacion\n'
                 '$V_{dc}$ = %.0f V.  El lugar verde lo genera la funcion '
                 'svpwm() del firmware.' % VDC, fontsize=10)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '26_svpwm_hexagono.png'), dpi=135)
    plt.close(fig)

    # comprobacion: el lugar en el limite lineal debe ser un circulo exacto
    r = np.hypot(sal[:, 0], sal[:, 1])
    err = float(np.max(np.abs(r - R_INS)) / R_INS * 100)
    return [dict(name='SVPWM: error del lugar geometrico en el limite lineal',
                 value=err, limit=1.0, ok=err < 1.0, unit='%',
                 note='debe ser un circulo de radio Vdc/sqrt(3)')]


# =====================================================================
# 27  Ciclos de trabajo y patron de conmutacion
# =====================================================================
def patron():
    ang = np.linspace(0, 2 * np.pi, 1000)
    m = R_INS * 0.9
    duty = np.array([CR.svpwm(m * math.cos(a), m * math.sin(a), VDC)
                     for a in ang])
    # secuencia cero inyectada = lo que separa el SVPWM del SPWM senoidal
    sen = np.array([[0.5 + m * math.cos(a - k * 2 * math.pi / 3) / VDC
                     for k in range(3)] for a in ang])
    cero = duty[:, 0] - sen[:, 0]

    fig = plt.figure(figsize=(12, 7.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1])

    ax0 = fig.add_subplot(gs[0, :])
    for k, (c, lbl) in enumerate(((AZUL, 'fase A'), (VERDE, 'fase B'),
                                  (ROJO, 'fase C'))):
        ax0.plot(np.degrees(ang), duty[:, k], lw=1.9, color=c, label=lbl)
        ax0.plot(np.degrees(ang), sen[:, k], lw=0.9, ls=':', color=c,
                 alpha=0.6)
    for k in range(7):
        ax0.axvline(60 * k, lw=0.8, color=GRIS, alpha=0.5)
        if k < 6:
            ax0.text(60 * k + 30, 1.04, 'S%d' % (k + 1), ha='center',
                     fontsize=9, color=GRIS, weight='bold')
    ax0.set_ylim(-0.05, 1.12)
    ax0.set_xlim(0, 360)
    ax0.set_xlabel('angulo del vector de referencia [grados]')
    ax0.set_ylabel('ciclo de trabajo')
    ax0.set_title('Ciclos de trabajo que calcula svpwm() (linea gruesa) '
                  'frente al SPWM senoidal puro (punteada).\n'
                  'La forma de "silla" es la inyeccion de secuencia cero: es '
                  'lo que da un 15.5 %% mas de tension de salida.', fontsize=10)
    ax0.legend(fontsize=8, ncol=3, loc='lower right')

    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(np.degrees(ang), cero * VDC, lw=1.8, color=MORADO)
    ax1.set_xlim(0, 360)
    ax1.set_xlabel('angulo [grados]')
    ax1.set_ylabel('$V_{cm}$ [V]')
    ax1.set_title('Secuencia cero inyectada (3.er armonico)', fontsize=9.5)

    # patron de 7 segmentos en un periodo, sector 1
    ax2 = fig.add_subplot(gs[1, 1])
    a_ej = math.radians(25)
    da, db, dc = CR.svpwm(m * math.cos(a_ej), m * math.sin(a_ej), VDC)
    ts = 1.0 / P.F_SW * 1e6                      # us
    dt_ns = P.DEADTIME * 1e6                     # us
    for k, (d, c, lbl) in enumerate(((da, AZUL, 'A'), (db, VERDE, 'B'),
                                     (dc, ROJO, 'C'))):
        ton = d * ts
        t0 = (ts - ton) / 2.0
        y = 2 - k
        ax2.add_patch(plt.Rectangle((t0, y - 0.32), ton, 0.64,
                                    color=c, alpha=0.75))
        ax2.text(-0.9, y, lbl, ha='right', va='center', fontsize=10,
                 color=c, weight='bold')
        ax2.text(t0 + ton / 2, y, 'd=%.3f' % d, ha='center', va='center',
                 fontsize=8, color='white', weight='bold')
    for xv in (0, ts / 2, ts):
        ax2.axvline(xv, lw=0.9, ls=':', color=GRIS)
    ax2.text(ts / 2, 3.15, 'centro del periodo\n(aqui muestrea el ADC)',
             ha='center', fontsize=8, color=NARANJA)
    seq = ['$V_0$', '$V_1$', '$V_2$', '$V_7$', '$V_2$', '$V_1$', '$V_0$']
    bordes = sorted({0, ts} | {(ts - d * ts) / 2 for d in (da, db, dc)}
                    | {(ts + d * ts) / 2 for d in (da, db, dc)})
    for i in range(len(bordes) - 1):
        xm = (bordes[i] + bordes[i + 1]) / 2
        if i < len(seq):
            ax2.text(xm, 0.2, seq[i], ha='center', fontsize=8.5, color=GRIS)
    ax2.set_xlim(-1.2, ts + 0.6)
    ax2.set_ylim(-0.1, 3.5)
    ax2.set_yticks([])
    ax2.set_xlabel('t dentro de un periodo PWM [us]')
    ax2.set_title('Patron simetrico de 7 segmentos en el sector 1\n'
                  '$T_s$ = %.1f us,  dead-time %.0f ns' % (ts, dt_ns * 1000),
                  fontsize=9.5)
    ax2.grid(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '27_svpwm_patron.png'), dpi=135)
    plt.close(fig)

    # el maximo de la suma max+min debe ser 1 (uso completo del bus)
    ganancia = (R_INS / (VDC / 2.0) - 1.0) * 100
    return [dict(name='SVPWM: ganancia sobre SPWM senoidal', value=ganancia,
                 limit=15.0, ok=ganancia > 15.0, unit='%',
                 note='teorico 15.47 %')]


def todas():
    return hexagono() + patron()


if __name__ == '__main__':
    for c in todas():
        print('  [%-5s] %-46s %10.4g %s'
              % ('OK' if c['ok'] else 'FALLA', c['name'], c['value'],
                 c['unit']))
