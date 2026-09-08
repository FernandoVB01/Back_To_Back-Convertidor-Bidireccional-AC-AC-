"""
sim_respuesta.py - Graficas de respuesta que faltaban:

  20  Respuesta al escalon en lazo cerrado (corriente y bus)
  21  Escalon de CARGA sobre el bus DC: caida y recuperacion
  22  Nyquist con los margenes marcados
  23  Rendimiento vs carga y desglose de perdidas
  24  Curva termica y derating por temperatura ambiente
  25  Espectro armonico de la corriente de red contra IEEE 519

Todo sale de sim/b2b_params.py.
"""

import math
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt              # noqa: E402
from scipy import signal                     # noqa: E402

import b2b_params as P                       # noqa: E402
import sim_design as D                       # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({'figure.facecolor': '#ffffff', 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})

AZUL, VERDE, ROJO, NARANJA, GRIS = ('#1f6feb', '#16a34a', '#c0392b',
                                    '#e67e22', '#7f8c8d')


def _metricas(t, y, ref=1.0):
    """Sobreimpulso, tiempo de subida 10-90 % y de establecimiento al 2 %."""
    over = (y.max() - ref) / ref * 100.0
    try:
        i10 = int(np.where(y >= 0.1 * ref)[0][0])
        i90 = int(np.where(y >= 0.9 * ref)[0][0])
        tr = t[i90] - t[i10]
    except IndexError:
        tr = float('nan')
    fuera = np.where(np.abs(y - ref) > 0.02 * ref)[0]
    ts = t[fuera[-1]] if len(fuera) else 0.0
    return over, tr, ts


# =====================================================================
# 20  Respuesta al escalon en lazo cerrado
# =====================================================================
def escalon_lazos():
    L = P.L1 + P.L2
    R = P.R_L
    Td = 1.5 * P.T_S
    Kp = L / (2 * Td)
    Ki = Kp * R / L

    # El retardo puro e^(-Td*s) no es racional: se aproxima con Pade [2/2].
    # (scipy.signal.pade no existe; se escribe explicito.)
    #   e^-x ~ (1 - x/2 + x^2/12) / (1 + x/2 + x^2/12)   con x = Td*s
    npd = [Td ** 2 / 12.0, -Td / 2.0, 1.0]
    dpd = [Td ** 2 / 12.0, Td / 2.0, 1.0]
    delay = signal.TransferFunction(npd, dpd)
    planta = signal.TransferFunction([1.0], [L, R])
    pi = signal.TransferFunction([Kp, Ki], [1.0, 0.0])

    def mul(a, b):
        return signal.TransferFunction(np.polymul(a.num, b.num),
                                       np.polymul(a.den, b.den))

    lazo = mul(mul(pi, planta), delay)
    cerr = signal.TransferFunction(
        np.polymul(lazo.num, [1.0]),
        np.polyadd(np.polymul(lazo.den, [1.0]), lazo.num))
    t1 = np.linspace(0, 6e-3, 4000)
    _, y1 = signal.step(cerr, T=t1)
    o1, tr1, ts1 = _metricas(t1, y1)

    # lazo de bus
    kpl = 1.5 * (P.V_PH * math.sqrt(2)) / (P.C_BUS * P.V_DC)
    Tsum = 2 * Td + P.T_S * 3
    a = 3.0
    Kpv = 1.0 / (kpl * a * Tsum)
    Kiv = Kpv / ((a ** 2) * Tsum)
    piv = signal.TransferFunction([Kpv, Kiv], [1.0, 0.0])
    plv = signal.TransferFunction([kpl], [1.0, 0.0])
    inner = signal.TransferFunction([1.0], [Tsum, 1.0])
    lv = mul(mul(piv, plv), inner)
    cv = signal.TransferFunction(
        lv.num, np.polyadd(lv.den, np.polymul(lv.num, [1.0])))
    t2 = np.linspace(0, 0.08, 4000)
    _, y2 = signal.step(cv, T=t2)
    o2, tr2, ts2 = _metricas(t2, y2)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for k, (t, y, ttl, o, tr, ts, esc) in enumerate([
            (t1 * 1e3, y1, 'Lazo de CORRIENTE (16 kHz)', o1, tr1, ts1, 1e3),
            (t2 * 1e3, y2, 'Lazo de TENSION DE BUS', o2, tr2, ts2, 1e3)]):
        ax[k].plot(t, y, lw=1.8, color=AZUL)
        ax[k].axhline(1.0, ls='--', lw=1.0, color=VERDE)
        ax[k].axhline(1.02, ls=':', lw=0.8, color=GRIS)
        ax[k].axhline(0.98, ls=':', lw=0.8, color=GRIS)
        ax[k].axvline(ts * esc, ls='-.', lw=1.0, color=NARANJA)
        ax[k].set_title('%s\nsobreimpulso %.1f %%   t_subida %.0f us   '
                        't_establec. %.0f us'
                        % (ttl, o, tr * 1e6, ts * 1e6))
        ax[k].set_xlabel('t [ms]')
        ax[k].set_ylabel('salida / consigna')
        ax[k].set_ylim(0, max(1.35, y.max() * 1.1))
    fig.suptitle('Respuesta al escalon en lazo cerrado', fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '20_respuesta_escalon.png'), dpi=130)
    plt.close(fig)
    return [dict(name='Sobreimpulso del lazo de corriente', value=o1,
                 limit=20.0, ok=o1 < 20.0, unit='%', note=''),
            dict(name='Tiempo de establecimiento del bus', value=ts2 * 1e3,
                 limit=50.0, ok=ts2 * 1e3 < 50.0, unit='ms', note='al 2 %')]


# =====================================================================
# 21  Escalon de CARGA sobre el bus DC
# =====================================================================
def escalon_carga():
    """El inversor pasa de 20 % a 100 % de carga de golpe. Se compara el
    lazo de bus con y sin feedforward de potencia."""
    dt = P.T_S
    t = np.arange(0, 0.12, dt)
    P_load = np.where(t < 0.03, 0.2 * P.S_N, P.S_N)
    P_load = np.where(t > 0.075, 0.2 * P.S_N, P_load)

    Td = 1.5 * P.T_S
    kpl = 1.5 * (P.V_PH * math.sqrt(2)) / (P.C_BUS * P.V_DC)
    Tsum = 2 * Td + P.T_S * 3
    Kpv = 1.0 / (kpl * 3.0 * Tsum)
    Kiv = Kpv / (9.0 * Tsum)
    Vg = P.V_PH * math.sqrt(2)
    ILIM = 1.6 * P.I_PK

    curvas = {}
    for ff_on in (False, True):
        vdc = P.V_DC
        integ = 0.0
        idq = 0.0
        v = np.zeros_like(t)
        for k, pl in enumerate(P_load):
            err = P.V_DC - vdc
            ff = (pl / (1.5 * Vg)) if ff_on else 0.0
            u = Kpv * err + integ + ff
            if -ILIM < u < ILIM:
                integ += Kiv * err * dt
            idref = min(max(u, -ILIM), ILIM)
            # lazo interno de corriente: primer orden equivalente
            idq += (idref - idq) * dt / Tsum
            p_in = 1.5 * Vg * idq
            vdc += (p_in - pl) / (P.C_BUS * max(vdc, 1.0)) * dt
            v[k] = vdc
        curvas[ff_on] = v

    caida_sin = P.V_DC - curvas[False][(t > 0.03) & (t < 0.06)].min()
    caida_con = P.V_DC - curvas[True][(t > 0.03) & (t < 0.06)].min()

    fig, ax = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True,
                           gridspec_kw={'height_ratios': [1, 2]})
    ax[0].plot(t * 1e3, P_load / 1000, lw=1.6, color=GRIS)
    ax[0].fill_between(t * 1e3, 0, P_load / 1000, color=GRIS, alpha=0.15)
    ax[0].set_ylabel('carga [kW]')
    ax[0].set_title('Escalon de carga: 20 % -> 100 % -> 20 % del inversor')
    ax[1].plot(t * 1e3, curvas[False], lw=1.6, color=ROJO,
               label='solo PI  (caida %.1f V)' % caida_sin)
    ax[1].plot(t * 1e3, curvas[True], lw=1.8, color=VERDE,
               label='PI + feedforward de potencia  (caida %.1f V)'
               % caida_con)
    ax[1].axhline(P.V_DC, ls='--', lw=1.0, color=GRIS)
    ax[1].axhline(P.V_DC * 0.98, ls=':', lw=0.9, color=NARANJA)
    ax[1].annotate('-2 %', (2, P.V_DC * 0.98 + 1), fontsize=8, color=NARANJA)
    ax[1].set_xlabel('t [ms]')
    ax[1].set_ylabel('$V_{dc}$ [V]')
    ax[1].legend(fontsize=8, loc='lower right')
    ax[1].set_title('Respuesta del bus DC. El feedforward divide la caida '
                    'por %.1f' % (caida_sin / max(caida_con, 0.1)))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '21_escalon_carga.png'), dpi=130)
    plt.close(fig)
    return [dict(name='Caida del bus ante escalon de carga (con FF)',
                 value=caida_con, limit=0.02 * P.V_DC,
                 ok=caida_con < 0.02 * P.V_DC, unit='V',
                 note='limite 2 %% = %.0f V' % (0.02 * P.V_DC))]


# =====================================================================
# 22  Nyquist con margenes
# =====================================================================
def nyquist():
    L = P.L1 + P.L2
    R = P.R_L
    Td = 1.5 * P.T_S
    Kp = L / (2 * Td)
    Ki = Kp * R / L
    w = 2 * np.pi * np.logspace(0, math.log10(P.F_SW / 2), 8000)
    s = 1j * w
    Lo = (Kp + Ki / s) * (1.0 / (R + s * L)) * np.exp(-s * Td)

    mag = np.abs(Lo)
    ph = np.unwrap(np.angle(Lo))
    ic = int(np.argmin(np.abs(mag - 1.0)))
    pm = 180 + math.degrees(ph[ic])
    idx = np.where(np.diff(np.sign(ph + np.pi)))[0]
    gm = 20 * math.log10(1.0 / mag[idx[0]]) if len(idx) else float('inf')
    # distancia minima al punto -1 (margen de modulo)
    mm = float(np.min(np.abs(Lo + 1.0)))

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(Lo.real, Lo.imag, lw=1.6, color=AZUL)
    ax.plot(Lo.real, -Lo.imag, lw=0.8, ls=':', color=AZUL, alpha=0.5)
    ax.plot([-1], [0], 'x', ms=10, mew=2, color=ROJO)
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(-1 + mm * np.cos(th), mm * np.sin(th), ls='--', lw=1.0,
            color=NARANJA)
    ax.plot(np.cos(th), np.sin(th), ls=':', lw=0.8, color=GRIS)
    ax.annotate('-1', (-1.08, 0.06), color=ROJO, fontsize=9)
    ax.set_xlim(-2.2, 1.6)
    ax.set_ylim(-1.9, 1.9)
    ax.set_aspect('equal')
    ax.set_xlabel('Re'); ax.set_ylabel('Im')
    ax.set_title('Nyquist del lazo de corriente\n'
                 'MF %.1f grados   MG %.1f dB   margen de modulo %.2f'
                 % (pm, gm, mm))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '22_nyquist_margenes.png'), dpi=130)
    plt.close(fig)
    return [dict(name='Margen de modulo (distancia a -1)', value=mm,
                 limit=0.5, ok=mm > 0.5, unit='',
                 note='> 0.5 es robusto')]


# =====================================================================
# 23  Rendimiento y perdidas
# =====================================================================
def rendimiento():
    cargas = np.linspace(0.1, 1.0, 30)
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))

    for nombre, rds25, col in ((P.SIC_ALT_NAME, P.RDSON_ALT_25, VERDE),
                               (P.SIC_NAME, P.RDSON_25, NARANJA)):
        eta = []
        for c in cargas:
            ipk = P.I_PK * c
            idev = ipk * math.sqrt(1 / 8 + 0.9 * 0.95 / (3 * math.pi))
            pcond = idev ** 2 * rds25 * P.RDSON_K
            isw = ipk * 2 / math.pi
            esw = P.E_SW_REF * (P.V_DC / P.E_SW_V_REF) * (isw / P.E_SW_I_REF)
            psw = esw * P.F_SW
            pdev = pcond + psw + 0.02 * P.V_F_BODY * isw
            ptot = pdev * P.N_SW_TOTAL + 45 * c ** 2 + 25
            pout = P.S_N * c
            eta.append(100 * pout / (pout + ptot))
        ax[0].plot(cargas * 100, eta, lw=1.9, color=col, label=nombre)
    ax[0].axhline(97, ls=':', lw=1.0, color=GRIS)
    ax[0].set_xlabel('carga [%% de %g kVA]' % (P.S_N / 1000))
    ax[0].set_ylabel('rendimiento [%]')
    ax[0].set_title('Rendimiento vs carga')
    ax[0].legend(fontsize=8, loc='lower right')
    ax[0].set_ylim(90, 100)

    _, th = D.analiza_termico(P.RDSON_ALT_25, P.SIC_ALT_NAME)
    partes = [('Conduccion SiC', th['p_cond'] * P.N_SW_TOTAL),
              ('Conmutacion SiC', th['p_sw'] * P.N_SW_TOTAL),
              ('Reactancias LCL', 45.0),
              ('Condensadores', 8.0),
              ('Auxiliares y control', 25.0)]
    nom = [p[0] for p in partes]
    val = [p[1] for p in partes]
    cols = [ROJO, NARANJA, AZUL, '#8e44ad', GRIS]
    b = ax[1].barh(nom, val, color=cols, alpha=0.85)
    for r, v in zip(b, val):
        ax[1].text(v + 3, r.get_y() + r.get_height() / 2, '%.0f W' % v,
                   va='center', fontsize=8)
    ax[1].set_xlabel('perdidas [W]')
    ax[1].set_title('Desglose a plena carga con %s\ntotal %.0f W'
                    % (P.SIC_ALT_NAME, sum(val)))
    ax[1].set_xlim(0, max(val) * 1.35)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '23_rendimiento_perdidas.png'), dpi=130)
    plt.close(fig)
    return []


# =====================================================================
# 24  Termico y derating
# =====================================================================
def termico():
    _, th = D.analiza_termico(P.RDSON_ALT_25, P.SIC_ALT_NAME)
    pdev, rth_sa = th['p_dev'], 0.30
    ta = np.linspace(20, 70, 200)

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for rsa, col, lbl in ((0.20, VERDE, 'disipador 0.20 C/W'),
                          (0.30, AZUL, 'disipador 0.30 C/W (elegido)'),
                          (0.50, ROJO, 'disipador 0.50 C/W')):
        tj = ta + pdev * P.N_SW_TOTAL * rsa + pdev * (P.RTH_JC + P.RTH_CS)
        ax[0].plot(ta, tj, lw=1.8, color=col, label=lbl)
    ax[0].axhline(P.T_J_MAX, ls='--', lw=1.2, color=ROJO)
    ax[0].annotate('Tj max de diseno 125 C', (22, P.T_J_MAX + 3), fontsize=8,
                   color=ROJO)
    ax[0].axhline(175, ls=':', lw=1.0, color=GRIS)
    ax[0].annotate('limite absoluto 175 C', (22, 178), fontsize=8, color=GRIS)
    ax[0].axvline(P.T_A, ls=':', lw=1.0, color=NARANJA)
    ax[0].annotate('ambiente de diseno', (P.T_A + 1, 60), fontsize=8,
                   rotation=90, color=NARANJA)
    ax[0].set_xlabel('temperatura ambiente [C]')
    ax[0].set_ylabel('$T_j$ [C]')
    ax[0].set_title('Union vs ambiente a plena carga')
    ax[0].legend(fontsize=8, loc='upper left')

    # derating: potencia maxima que mantiene Tj <= 125
    pot = []
    for T in ta:
        lo, hi = 0.0, 1.4
        for _ in range(40):
            c = (lo + hi) / 2
            ipk = P.I_PK * c
            idev = ipk * math.sqrt(1 / 8 + 0.9 * 0.95 / (3 * math.pi))
            pc = idev ** 2 * P.RDSON_ALT_25 * P.RDSON_K
            isw = ipk * 2 / math.pi
            ps = P.E_SW_REF * (P.V_DC / P.E_SW_V_REF) * \
                (isw / P.E_SW_I_REF) * P.F_SW
            pd = pc + ps
            tj = T + pd * P.N_SW_TOTAL * 0.30 + pd * (P.RTH_JC + P.RTH_CS)
            if tj > P.T_J_MAX:
                hi = c
            else:
                lo = c
        pot.append(lo * P.S_N / 1000)
    ax[1].plot(ta, pot, lw=2.0, color=AZUL)
    ax[1].fill_between(ta, 0, pot, color=AZUL, alpha=0.12)
    ax[1].axhline(P.S_N / 1000, ls='--', lw=1.0, color=VERDE)
    ax[1].annotate('nominal %g kVA' % (P.S_N / 1000), (22, P.S_N / 1000 + 0.4),
                   fontsize=8, color=VERDE)
    ax[1].axvline(P.T_A, ls=':', lw=1.0, color=NARANJA)
    ax[1].set_xlabel('temperatura ambiente [C]')
    ax[1].set_ylabel('potencia admisible [kVA]')
    ax[1].set_title('Curva de derating (Tj <= 125 C, Rth 0.30 C/W)')
    ax[1].set_ylim(0, P.S_N / 1000 * 1.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '24_termico_derating.png'), dpi=130)
    plt.close(fig)
    return []


# =====================================================================
# 25  Espectro armonico contra IEEE 519
# =====================================================================
def espectro():
    fam = [(P.F_SW - 2 * P.F_G, 0.22), (P.F_SW + 2 * P.F_G, 0.22),
           (P.F_SW - 4 * P.F_G, 0.05), (P.F_SW + 4 * P.F_G, 0.05),
           (2 * P.F_SW - P.F_G, 0.12), (2 * P.F_SW + P.F_G, 0.12),
           (2 * P.F_SW - 5 * P.F_G, 0.04), (2 * P.F_SW + 5 * P.F_G, 0.04)]
    v1 = P.V_DC * 0.87 / 2.0
    i1 = P.I_N * math.sqrt(2)
    ordenes, pct = [], []
    for fh, kh in fam:
        ih = kh * v1 * abs(D.lcl_tf(2 * math.pi * fh, P.L1, P.L2, P.CF, P.RD))
        ordenes.append(fh / P.F_G)
        pct.append(100 * ih / i1)
    # armonicos de baja frecuencia tipicos de un AFE bien controlado
    bajos = [(5, 0.9), (7, 0.6), (11, 0.35), (13, 0.25), (17, 0.15),
             (19, 0.12), (23, 0.08), (25, 0.06)]
    thd = math.sqrt(sum(p ** 2 for p in pct) + sum(v ** 2 for _, v in bajos))

    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    for h, v in bajos:
        ax.bar(h, v, width=1.6, color=AZUL, alpha=0.85)
    for o, p in zip(ordenes, pct):
        ax.bar(o, p, width=2.5, color=NARANJA, alpha=0.9)
    # limites IEEE 519 por rango de orden (Isc/IL 20-50)
    for (h0, h1, lim) in ((2, 11, 7.0), (11, 17, 3.5), (17, 23, 2.5),
                          (23, 35, 1.0), (35, 600, 0.5)):
        ax.hlines(lim, h0, h1, color=ROJO, lw=1.6)
    ax.set_yscale('log')
    ax.set_ylim(1e-3, 12)
    ax.set_xlim(0, 600)
    ax.set_xlabel('orden del armonico (multiplo de %g Hz)' % P.F_G)
    ax.set_ylabel('% de la fundamental')
    ax.set_title('Espectro de la corriente de red vs IEEE 519 (linea roja)\n'
                 'THD estimada %.3f %%  (limite 5 %%).  Azul: armonicos de '
                 'baja frecuencia.  Naranja: residuo de conmutacion tras el '
                 'LCL' % thd)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '25_espectro_armonicos.png'), dpi=130)
    plt.close(fig)
    return [dict(name='THD con armonicos de baja frecuencia', value=thd,
                 limit=P.THD_LIMIT, ok=thd < P.THD_LIMIT, unit='%',
                 note='IEEE 519')]


def todas():
    c = []
    c += escalon_lazos()
    c += escalon_carga()
    c += nyquist()
    c += rendimiento()
    c += termico()
    c += espectro()
    return c
