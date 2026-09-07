"""
sim_design.py - Validacion analitica del diseno.

  1. Filtro LCL      : respuesta en frecuencia, resonancia, atenuacion a f_sw,
                       amortiguamiento y THD estimada de la corriente de red.
  2. Lazos de control: planta + retardo de calculo/PWM, sintonia PI por optimo
                       de modulo, margenes de fase y ganancia (Bode).
  3. Termico         : desglose de perdidas y disipador necesario.
  4. Precarga        : inrush, constante de tiempo y energia en la resistencia.

Cada bloque devuelve una lista de comprobaciones (nombre, valor, limite, ok).
"""

import math
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402

import b2b_params as P                   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)

PLT_BG = '#ffffff'
plt.rcParams.update({'figure.facecolor': PLT_BG, 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})


def _chk(name, value, limit, ok, unit='', note=''):
    return dict(name=name, value=value, limit=limit, ok=bool(ok),
                unit=unit, note=note)


# =====================================================================
# 1. FILTRO LCL
# =====================================================================
def lcl_tf(w, L1, L2, Cf, Rd):
    """I_red(jw) / V_convertidor(jw) del filtro LCL con amortiguamiento serie."""
    s = 1j * w
    num = 1.0 + s * Rd * Cf
    den = (s ** 3) * L1 * L2 * Cf + (s ** 2) * Rd * Cf * (L1 + L2) \
        + s * (L1 + L2)
    return num / den


def analiza_lcl():
    L1, L2, Cf, Rd = P.L1, P.L2, P.CF, P.RD
    checks = []

    f_res = math.sqrt((L1 + L2) / (L1 * L2 * Cf)) / (2 * math.pi)
    checks.append(_chk('Resonancia LCL', f_res, (10 * P.F_G, 0.5 * P.F_SW),
                       10 * P.F_G < f_res < 0.5 * P.F_SW, 'Hz',
                       'debe estar entre 10*fg y fsw/2'))

    # atenuacion: |G(f_sw)| respecto a un inductor unico equivalente L1+L2
    w_sw = 2 * math.pi * P.F_SW
    g_lcl = abs(lcl_tf(w_sw, L1, L2, Cf, Rd))
    g_l = 1.0 / (w_sw * (L1 + L2))
    aten_db = 20 * math.log10(g_lcl / g_l)
    checks.append(_chk('Atenuacion extra a f_sw vs L unica', aten_db, -12.0,
                       aten_db < -12.0, 'dB',
                       'compromiso con el amortiguamiento; el criterio '
                       'normativo real es la THD'))

    # rizado de corriente en el inductor del convertidor
    d_i_pp = P.V_DC / (8 * L1 * P.F_SW)
    pct = 100 * d_i_pp / P.I_PK
    checks.append(_chk('Rizado en L1 (pico-pico)', pct, 25.0, pct < 25.0, '%',
                       f'{d_i_pp:.2f} A sobre {P.I_PK:.1f} A pico'))

    # potencia reactiva del banco Cf
    q_cf = 3 * (P.V_PH ** 2) * P.W_G * Cf
    pct_q = 100 * q_cf / P.S_N
    checks.append(_chk('Reactiva del banco Cf', pct_q, 5.0, pct_q < 5.0, '%',
                       f'{q_cf:.0f} var'))

    # amortiguamiento: pico de la respuesta en resonancia
    w = 2 * np.pi * np.logspace(0, math.log10(P.F_SW * 6), 4000)
    mag = np.abs(lcl_tf(w, L1, L2, Cf, Rd))
    mag_und = np.abs(lcl_tf(w, L1, L2, Cf, 0.0))
    i_res = int(np.argmin(np.abs(w - 2 * np.pi * f_res)))
    pico_db = 20 * math.log10(mag[i_res] / g_l)
    checks.append(_chk('Pico en resonancia (amortiguado)', pico_db, 20.0,
                       pico_db < 20.0, 'dB',
                       'sin Rd seria %.0f dB'
                       % (20 * math.log10(mag_und[i_res] / g_l))))

    p_rd = 3 * (0.3 * d_i_pp / math.sqrt(2)) ** 2 * Rd   # estimacion
    checks.append(_chk('Disipacion en las 3 Rd', p_rd, 30.0, p_rd < 30.0, 'W',
                       'usar 10 W por resistencia'))

    # THD estimada: armonicos de PWM alrededor de f_sw y 2 f_sw
    #   amplitudes tipicas de un puente de 2 niveles con SVPWM, m ~ 0.87
    fam = [(P.F_SW - 2 * P.F_G, 0.22), (P.F_SW + 2 * P.F_G, 0.22),
           (P.F_SW - 4 * P.F_G, 0.05), (P.F_SW + 4 * P.F_G, 0.05),
           (2 * P.F_SW - P.F_G, 0.12), (2 * P.F_SW + P.F_G, 0.12),
           (2 * P.F_SW - 5 * P.F_G, 0.04), (2 * P.F_SW + 5 * P.F_G, 0.04)]
    v1 = P.V_DC * 0.87 / 2.0
    i_h2 = 0.0
    for fh, kh in fam:
        vh = kh * v1
        ih = vh * abs(lcl_tf(2 * math.pi * fh, L1, L2, Cf, Rd))
        i_h2 += ih ** 2
    thd = 100 * math.sqrt(i_h2) / (P.I_N * math.sqrt(2))
    checks.append(_chk('THD de corriente de red (estimada)', thd,
                       P.THD_LIMIT, thd < P.THD_LIMIT, '%',
                       'IEEE 519 / IEC 61000-3-12'))

    # ---- grafico ----
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    f = w / (2 * np.pi)
    ax[0].semilogx(f, 20 * np.log10(mag_und), lw=1.0, ls='--', color='#c0392b',
                   label='LCL sin amortiguar (Rd = 0)')
    ax[0].semilogx(f, 20 * np.log10(mag), lw=1.8, color='#1f6feb',
                   label=f'LCL con Rd = {Rd} $\\Omega$')
    ax[0].semilogx(f, 20 * np.log10(1.0 / (w * (L1 + L2))), lw=1.0,
                   color='#7f8c8d', label='Inductor unico L1+L2')
    ax[0].axvline(f_res, color='#e67e22', lw=1.0)
    ax[0].axvline(P.F_SW, color='#2c3e50', lw=1.0, ls=':')
    ax[0].annotate(f'$f_{{res}}$ = {f_res:.0f} Hz', (f_res, 20),
                   xytext=(f_res * 1.15, 30), color='#e67e22')
    ax[0].annotate(f'$f_{{sw}}$ = {P.F_SW/1000:.0f} kHz', (P.F_SW, -60),
                   xytext=(P.F_SW * 0.35, -50), color='#2c3e50')
    ax[0].set_ylabel('$|I_{red}/V_{conv}|$  [dB]')
    ax[0].set_title('Filtro LCL: L1 = %.2f mH, Cf = %.0f uF, Rd = %.1f ohm, '
                    'L2 = %.2f mH' % (L1 * 1e3, Cf * 1e6, Rd, L2 * 1e3))
    ax[0].legend(fontsize=8)
    ax[0].set_ylim(-140, 60)
    ax[1].semilogx(f, np.degrees(np.angle(lcl_tf(w, L1, L2, Cf, Rd))),
                   lw=1.6, color='#1f6feb')
    ax[1].axvline(f_res, color='#e67e22', lw=1.0)
    ax[1].set_ylabel('Fase [grados]')
    ax[1].set_xlabel('Frecuencia [Hz]')
    ax[1].set_xlim(10, P.F_SW * 6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '01_lcl_bode.png'), dpi=130)
    plt.close(fig)
    return checks


# =====================================================================
# 2. LAZOS DE CONTROL
# =====================================================================
def analiza_lazos():
    checks = []
    L = P.L1 + P.L2
    R = P.R_L
    Td = 1.5 * P.T_S                      # retardo calculo + PWM

    # --- lazo de corriente: optimo de modulo ---
    Kp = L / (2.0 * Td)
    Ti = L / R
    Ki = Kp / Ti

    w = 2 * np.pi * np.logspace(0, math.log10(P.F_SW / 2), 6000)
    s = 1j * w
    Gp = 1.0 / (R + s * L)
    Gc = Kp + Ki / s
    Gd = np.exp(-s * Td)
    Lo = Gc * Gp * Gd

    mag = np.abs(Lo)
    ph = np.unwrap(np.angle(Lo))
    i_c = int(np.argmin(np.abs(mag - 1.0)))
    f_bw = w[i_c] / (2 * np.pi)
    pm = 180.0 + math.degrees(ph[i_c])
    idx = np.where(np.diff(np.sign(ph + np.pi)))[0]
    gm = 20 * math.log10(1.0 / mag[idx[0]]) if len(idx) else float('inf')

    checks.append(_chk('Lazo de corriente: ancho de banda', f_bw,
                       (P.F_SW / 20, P.F_SW / 6),
                       P.F_SW / 20 < f_bw < P.F_SW / 6, 'Hz',
                       f'Kp = {Kp:.3f}  Ki = {Ki:.1f}'))
    checks.append(_chk('Lazo de corriente: margen de fase', pm, P.PM_MIN,
                       pm > P.PM_MIN, 'grados'))
    checks.append(_chk('Lazo de corriente: margen de ganancia', gm, P.GM_MIN,
                       gm > P.GM_MIN, 'dB'))

    # --- lazo de bus DC (optimo simetrico) ---
    # planta: id -> Vdc  ~  (3/2)(Vd / (C Vdc)) * 1/s , tras el lazo interno
    Kpl = 1.5 * (P.V_PH * math.sqrt(2)) / (P.C_BUS * P.V_DC)
    Tsum = 2 * Td + 1.0 / (2 * math.pi * f_bw)
    a = 3.0
    Kp_v = 1.0 / (Kpl * a * Tsum)
    Ti_v = (a ** 2) * Tsum
    Ki_v = Kp_v / Ti_v
    wv = 2 * np.pi * np.logspace(-1, 4, 6000)
    sv = 1j * wv
    Lv = (Kp_v + Ki_v / sv) * (Kpl / sv) / (1 + sv * Tsum)
    magv = np.abs(Lv)
    phv = np.unwrap(np.angle(Lv))
    iv = int(np.argmin(np.abs(magv - 1.0)))
    f_bwv = wv[iv] / (2 * np.pi)
    pmv = 180.0 + math.degrees(phv[iv])

    checks.append(_chk('Lazo de bus DC: ancho de banda', f_bwv,
                       (P.F_G / 6, f_bw / 5),
                       P.F_G / 6 < f_bwv < f_bw / 5, 'Hz',
                       f'Kp = {Kp_v:.4f}  Ki = {Ki_v:.3f}'))
    checks.append(_chk('Lazo de bus DC: margen de fase', pmv, P.PM_MIN,
                       pmv > P.PM_MIN, 'grados'))

    # ---- grafico ----
    fig, ax = plt.subplots(2, 2, figsize=(11, 7))
    for col, (ww, LL, ttl, fb, pmv_) in enumerate(
            [(w, Lo, 'Lazo de CORRIENTE (16 kHz)', f_bw, pm),
             (wv, Lv, 'Lazo de BUS DC', f_bwv, pmv)]):
        ff = ww / (2 * np.pi)
        ax[0][col].semilogx(ff, 20 * np.log10(np.abs(LL)), lw=1.7,
                            color='#1f6feb')
        ax[0][col].axhline(0, color='#7f8c8d', lw=0.8)
        ax[0][col].axvline(fb, color='#e67e22', lw=1.0, ls='--')
        ax[0][col].set_title('%s\nBW = %.0f Hz   PM = %.1f grados'
                             % (ttl, fb, pmv_))
        ax[0][col].set_ylabel('Ganancia [dB]')
        ax[0][col].set_ylim(-60, 80)
        pp = np.degrees(np.unwrap(np.angle(LL)))
        ax[1][col].semilogx(ff, pp, lw=1.7, color='#16a34a')
        ax[1][col].axhline(-180, color='#c0392b', lw=0.8, ls=':')
        ax[1][col].axvline(fb, color='#e67e22', lw=1.0, ls='--')
        ax[1][col].set_ylabel('Fase [grados]')
        ax[1][col].set_xlabel('Frecuencia [Hz]')
        ax[1][col].set_ylim(-360, 0)
    fig.suptitle('Estabilidad de los lazos (planta + retardo de 1.5 Ts)',
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '02_lazos_bode.png'), dpi=130)
    plt.close(fig)

    return checks, dict(Kp_i=Kp, Ki_i=Ki, Kp_v=Kp_v, Ki_v=Ki_v, f_bw=f_bw)


# =====================================================================
# 3. TERMICO
# =====================================================================
def analiza_termico(rdson25=None, nombre=None):
    rdson25 = P.RDSON_25 if rdson25 is None else rdson25
    nombre = P.SIC_NAME if nombre is None else nombre
    checks = []
    m = 0.90
    cosphi = 0.95
    rdson = rdson25 * P.RDSON_K

    # corriente RMS por dispositivo (medio puente, modulacion senoidal)
    i_dev = P.I_PK * math.sqrt(1.0 / 8.0 + m * cosphi / (3 * math.pi))
    p_cond = (i_dev ** 2) * rdson
    # conmutacion escalada desde el punto de datasheet
    i_sw = P.I_PK * 2 / math.pi
    e_sw = P.E_SW_REF * (P.V_DC / P.E_SW_V_REF) * (i_sw / P.E_SW_I_REF)
    p_sw = e_sw * P.F_SW
    p_diode = 0.02 * P.V_F_BODY * i_sw     # conduccion breve del diodo cuerpo
    p_dev = p_cond + p_sw + p_diode
    p_tot = p_dev * P.N_SW_TOTAL

    t_rise_dev = p_dev * (P.RTH_JC + P.RTH_CS)
    t_sink_max = P.T_J_MAX - t_rise_dev
    rth_sa = (t_sink_max - P.T_A) / p_tot

    eta = 100 * P.S_N / (P.S_N + p_tot + 60)   # +60 W magneticos/aux

    checks.append(_chk(f'Perdidas por dispositivo ({nombre})', p_dev, 40.0,
                       p_dev < 40.0, 'W',
                       f'cond {p_cond:.1f} + conm {p_sw:.1f} + diodo '
                       f'{p_diode:.1f}'))
    checks.append(_chk('Perdidas totales de semiconductores', p_tot, 400.0,
                       p_tot < 400.0, 'W', f'{P.N_SW_TOTAL} dispositivos'))
    checks.append(_chk('Rth disipador-ambiente requerida', rth_sa, 0.15,
                       rth_sa > 0.15, 'C/W',
                       'por debajo de 0.15 C/W ya no es viable con aire'))
    checks.append(_chk('Rendimiento estimado', eta, 96.0, eta > 96.0, '%'))
    return checks, dict(p_dev=p_dev, p_tot=p_tot, rth_sa=rth_sa, eta=eta,
                        p_cond=p_cond, p_sw=p_sw)


# =====================================================================
# 4. PRECARGA
# =====================================================================
def analiza_precarga():
    checks = []
    i_pk = P.V_PK_RECT / P.R_PC
    tau = P.R_PC * P.C_BUS
    t95 = 3 * tau
    e_res = 0.5 * P.C_BUS * P.V_PK_RECT ** 2
    p_pk = P.V_PK_RECT ** 2 / P.R_PC

    checks.append(_chk('Corriente de inrush', i_pk, P.I_INRUSH_MAX,
                       i_pk < P.I_INRUSH_MAX, 'A'))
    checks.append(_chk('Constante de tiempo de precarga', tau * 1e3, 200.0,
                       tau * 1e3 < 200.0, 'ms',
                       f'95 % en {t95*1e3:.0f} ms'))
    checks.append(_chk('Energia en Rpc por carga', e_res, 400.0,
                       e_res < 400.0, 'J',
                       f'pico instantaneo {p_pk/1000:.1f} kW'))

    # transitorio
    t = np.linspace(0, 5 * tau, 2000)
    v = P.V_PK_RECT * (1 - np.exp(-t / tau))
    i = (P.V_PK_RECT / P.R_PC) * np.exp(-t / tau)
    t_close = -tau * math.log(1 - 0.9)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    ax[0].plot(t * 1e3, v, lw=1.8, color='#1f6feb')
    ax[0].axhline(0.9 * P.V_PK_RECT, ls='--', lw=1.0, color='#e67e22')
    ax[0].axvline(t_close * 1e3, ls=':', lw=1.2, color='#16a34a')
    ax[0].annotate('cierra K2\n%.0f ms' % (t_close * 1e3),
                   (t_close * 1e3, 0.5 * P.V_PK_RECT),
                   xytext=(t_close * 1e3 * 1.15, 0.35 * P.V_PK_RECT),
                   color='#16a34a', fontsize=8)
    ax[0].set_xlabel('t [ms]'); ax[0].set_ylabel('$V_{dc}$ [V]')
    ax[0].set_title('Precarga del bus (R = %.0f $\\Omega$, C = %.0f uF)'
                    % (P.R_PC, P.C_BUS * 1e6))
    ax[1].plot(t * 1e3, i, lw=1.8, color='#c0392b')
    ax[1].axhline(P.I_INRUSH_MAX, ls='--', lw=1.0, color='#7f8c8d')
    ax[1].annotate('limite %.0f A' % P.I_INRUSH_MAX,
                   (t[-1] * 1e3 * 0.45, P.I_INRUSH_MAX * 1.05), fontsize=8)
    ax[1].set_xlabel('t [ms]'); ax[1].set_ylabel('$I_{inrush}$ [A]')
    ax[1].set_title('Inrush: pico %.1f A, energia %.0f J' % (i_pk, e_res))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '03_precarga.png'), dpi=130)
    plt.close(fig)
    return checks
