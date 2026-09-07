"""
sim_timedomain.py - Simulacion temporal del convertidor back-to-back completo.

Cadena simulada:
    red 3~ -> LCL (equiv. L) -> AFE (PLL + control dq + lazo de bus)
           -> bus DC (condensador) -> inversor (FOC) -> PMSM + carga

Escenario:
    t = 0.00   arranque, el AFE regula el bus a 700 V con FP unitario
    t = 0.05   consigna de velocidad -> 250 rad/s (motorizando, ~12 kW)
    t = 0.30   FRENADO: consigna -> 40 rad/s. El motor devuelve energia,
               el bus sube, el AFE invierte el signo de Id y la inyecta a
               la red. Se verifica que la corriente de red cambia de fase.
    t = 0.50   fin

Modelo: promedio por periodo de conmutacion (no se simula la conmutacion
individual; para eso esta el analisis de rizado y THD de sim_design.py).
El control se ejecuta a f_sw = 16 kHz; la planta se integra a f_sw*10.
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
plt.rcParams.update({'figure.facecolor': '#ffffff', 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})


class PI:
    """PI con anti-windup por saturacion condicional."""

    def __init__(self, kp, ki, lo, hi):
        self.kp, self.ki, self.lo, self.hi = kp, ki, lo, hi
        self.i = 0.0

    def __call__(self, err, dt, ff=0.0):
        u = self.kp * err + self.i + ff
        if self.lo < u < self.hi:
            self.i += self.ki * err * dt
        else:
            # solo integra si el error empuja de vuelta al rango lineal
            if (u >= self.hi and err < 0) or (u <= self.lo and err > 0):
                self.i += self.ki * err * dt
        return min(max(self.kp * err + self.i + ff, self.lo), self.hi)


def run():
    # ---------------- discretizacion ----------------
    T_END = 0.60
    dt = P.T_S / 10.0                 # 6.25 us
    n = int(T_END / dt)
    ctrl_every = 10                   # el control corre a 16 kHz

    # ---------------- sintonia ----------------
    L = P.L1 + P.L2
    Td = 1.5 * P.T_S
    kp_i = L / (2 * Td)
    ki_i = kp_i * P.R_L / L
    Vmax = P.V_DC / math.sqrt(3.0)

    pi_id = PI(kp_i, ki_i, -Vmax, Vmax)
    pi_iq = PI(kp_i, ki_i, -Vmax, Vmax)

    kpl = 1.5 * (P.V_PH * math.sqrt(2)) / (P.C_BUS * P.V_DC)
    Tsum = 2 * Td + P.T_S * 3
    a = 3.0
    kp_v = 1.0 / (kpl * a * Tsum)
    ki_v = kp_v / ((a ** 2) * Tsum)
    I_LIM = 1.6 * P.I_PK
    pi_vdc = PI(kp_v, ki_v, -I_LIM, I_LIM)

    # motor: lazo de corriente y de velocidad
    kp_m = P.LD / (2 * Td)
    ki_m = kp_m * P.RS / P.LD
    pi_msd = PI(kp_m, ki_m, -Vmax, Vmax)
    pi_msq = PI(kp_m, ki_m, -Vmax, Vmax)
    IQ_LIM = P.IQ_LIM
    pi_w = PI(J_ := 0.0 or (P.J_MOT / (10 * Tsum * P.KT)),
              (P.J_MOT / (10 * Tsum * P.KT)) / (30 * Tsum),
              -IQ_LIM, IQ_LIM)

    # PLL (marco sincrono)
    pll_kp = 2 * 0.707 * (2 * math.pi * 25)
    pll_ki = (2 * math.pi * 25) ** 2
    pll_int = P.W_G
    th_pll = 0.0

    # ---------------- estados ----------------
    th_g = 0.0
    pll_err_ctrl = 0.0
    id_g = iq_g = 0.0                 # corriente de red en dq del PLL
    vdc = P.V_PK_RECT                 # arranca precargado por los diodos
    isd = isq = 0.0                   # corriente de estator dq
    wm = 0.0                          # velocidad mecanica
    th_e = 0.0

    vcd = vcq = vsd = vsq = 0.0
    p_inv = 0.0
    idref = iqref = 0.0
    isqref = 0.0
    w_ref = 0.0
    T_LOAD = P.T_LOAD

    Vg = P.V_PH * math.sqrt(2.0)      # amplitud de fase

    # ---------------- registros ----------------
    rec = {k: np.zeros(n) for k in
           ('t', 'vdc', 'id', 'iq', 'wm', 'te', 'pgrid', 'pinv',
            'ia', 'va', 'pll_err', 'isq', 'wref')}

    for k in range(n):
        t = k * dt

        # consigna con rampa (un variador real nunca da un escalon)
        if t < 0.05:
            w_tgt = 0.0
        elif t < 0.35:
            w_tgt = 250.0
        else:
            w_tgt = 40.0              # FRENADO -> regeneracion
        slew = 4000.0 * dt            # rad/s2 -> deceleracion regenerativa
        w_ref += max(-slew, min(slew, w_tgt - w_ref))

        # ---------- control cada T_s ----------
        if k % ctrl_every == 0:
            dtc = P.T_S
            # --- PLL: alinea el eje d con el vector de tension de red ---
            # normalizado por la amplitud: si no, la ganancia de lazo se
            # multiplica por Vg (326) y el PLL se vuelve inestable
            # error medido ANTES de avanzar el angulo: el PLL adelanta un
            # paso a proposito para compensar el retardo de muestreo
            pll_err_ctrl = math.atan2(math.sin(th_g - th_pll),
                                      math.cos(th_g - th_pll))
            vq_pll = math.sin(th_g - th_pll)
            pll_int += pll_ki * vq_pll * dtc
            w_pll = pll_int + pll_kp * vq_pll
            th_pll = (th_pll + w_pll * dtc) % (2 * math.pi)

            # --- lazo externo de bus DC -> Id* ---
            # feedforward de la potencia del inversor: sin el, un frenado
            # brusco dispara el bus antes de que reaccione el PI
            id_ff = p_inv / (1.5 * Vg) if abs(Vg) > 1 else 0.0
            idref = pi_vdc(P.V_DC - vdc, dtc, ff=id_ff)
            iqref = 0.0                       # factor de potencia unitario

            # --- lazo de corriente del AFE con desacoplo y feedforward ---
            ud = pi_id(idref - id_g, dtc)
            uq = pi_iq(iqref - iq_g, dtc)
            vcd = Vg + P.W_G * L * iq_g - ud
            vcq = 0.0 - P.W_G * L * id_g - uq

            # --- lazo de velocidad del motor -> Isq* ---
            isqref = pi_w(w_ref - wm, dtc)
            we = P.P_POLES * wm
            usd = pi_msd(0.0 - isd, dtc)      # Id* = 0 (sin debilitamiento)
            usq = pi_msq(isqref - isq, dtc)
            vsd = usd - we * P.LQ * isq
            vsq = usq + we * (P.LD * isd + P.LAMBDA_PM)

        # ---------- planta ----------
        th_g = (th_g + P.W_G * dt) % (2 * math.pi)

        # AFE: corriente de red en dq del PLL
        did = (Vg - vcd - P.R_L * id_g + P.W_G * L * iq_g) / L
        diq = (0.0 - vcq - P.R_L * iq_g - P.W_G * L * id_g) / L
        id_g += did * dt
        iq_g += diq * dt

        # motor: corriente de estator dq
        we = P.P_POLES * wm
        disd = (vsd - P.RS * isd + we * P.LQ * isq) / P.LD
        disq = (vsq - P.RS * isq - we * (P.LD * isd + P.LAMBDA_PM)) / P.LQ
        isd += disd * dt
        isq += disq * dt
        th_e = (th_e + we * dt) % (2 * math.pi)

        te = P.KT * isq
        t_load = T_LOAD * (1.0 if wm > 1.0 else 0.0)
        wm += (te - t_load - P.B_VISC * wm) / P.J_MOT * dt

        # potencias
        p_grid = 1.5 * (Vg * id_g)                    # red -> convertidor
        p_inv = 1.5 * (vsd * isd + vsq * isq)         # convertidor -> motor

        # bus DC
        vdc += (p_grid - p_inv) / (P.C_BUS * max(vdc, 1.0)) * dt
        # chopper de frenado como respaldo
        if vdc > P.V_DC_CHOP:
            vdc -= ((vdc ** 2) / P.R_BRAKE) / (P.C_BUS * vdc) * dt

        # corriente y tension de fase A reconstruidas
        ia = id_g * math.cos(th_pll) - iq_g * math.sin(th_pll)
        va = Vg * math.cos(th_g)

        rec['t'][k] = t; rec['vdc'][k] = vdc
        rec['id'][k] = id_g; rec['iq'][k] = iq_g
        rec['wm'][k] = wm; rec['te'][k] = te
        rec['pgrid'][k] = p_grid; rec['pinv'][k] = p_inv
        rec['ia'][k] = ia; rec['va'][k] = va
        rec['pll_err'][k] = pll_err_ctrl
        rec['isq'][k] = isq; rec['wref'][k] = w_ref

    return rec


def _win(rec, t0, t1):
    m = (rec['t'] >= t0) & (rec['t'] <= t1)
    return m


def evalua(rec):
    """Comprobaciones cuantitativas sobre el resultado."""
    chk = []
    t = rec['t']

    # regimen motorizando
    m_ss = (t > 0.28) & (t < 0.34)
    vdc_ss = rec['vdc'][m_ss]
    err = 100 * abs(vdc_ss.mean() - P.V_DC) / P.V_DC
    rip = 100 * (vdc_ss.max() - vdc_ss.min()) / P.V_DC
    chk.append(('Error de regulacion del bus (motorizando)', err, 1.0,
                err < 1.0, '%', f'media {vdc_ss.mean():.1f} V'))
    chk.append(('Rizado del bus en regimen', rip, P.V_DC_RIPPLE_MAX,
                rip < P.V_DC_RIPPLE_MAX, '%'))

    # sobretension durante el frenado
    m_br = (t > 0.35) & (t < 0.45)
    vpk = rec['vdc'][m_br].max()
    chk.append(('Pico de bus durante el frenado', vpk, P.V_DC_MAX,
                vpk < P.V_DC_MAX, 'V',
                f'chopper en {P.V_DC_CHOP:.0f} V, disparo en '
                f'{P.V_DC_MAX:.0f} V'))

    # factor de potencia en regimen (Iq ~ 0)
    idm = rec['id'][m_ss].mean()
    iqm = rec['iq'][m_ss].mean()
    pf = abs(idm) / math.hypot(idm, iqm) if math.hypot(idm, iqm) > 1e-6 else 1
    chk.append(('Factor de potencia en la red', pf, P.PF_MIN, pf > P.PF_MIN,
                '', f'Id = {idm:.2f} A, Iq = {iqm:.3f} A'))

    # inversion real del flujo de potencia
    p_mot = rec['pgrid'][m_ss].mean()
    p_reg = rec['pgrid'][(t > 0.36) & (t < 0.40)].mean()
    chk.append(('Potencia de red motorizando', p_mot / 1000, 0.0,
                p_mot > 0, 'kW', 'positiva = consume de la red'))
    chk.append(('Potencia de red frenando', p_reg / 1000, 0.0,
                p_reg < 0, 'kW', 'NEGATIVA = devuelve a la red (regenera)'))

    # PLL
    err_pll = np.degrees(np.abs(rec['pll_err'][t > 0.05])).max()
    chk.append(('Error maximo del PLL tras enganche', err_pll, 1.0,
                err_pll < 1.0, 'grados'))

    # seguimiento de velocidad
    wss = rec['wm'][(t > 0.32) & (t < 0.34)].mean()
    e_w = 100 * abs(wss - 250.0) / 250.0
    chk.append(('Error de velocidad en regimen', e_w, 2.0, e_w < 2.0, '%',
                f'{wss:.1f} rad/s de 250 rad/s'))

    out = []
    for row in chk:
        a, b, c, d, e = row[:5]
        f = row[5] if len(row) > 5 else ''
        out.append(dict(name=a, value=b, limit=c, ok=bool(d), unit=e, note=f))
    return out


def grafica(rec):
    t = rec['t']
    fig, ax = plt.subplots(4, 1, figsize=(11, 11), sharex=True)

    ax[0].plot(t, rec['vdc'], lw=1.4, color='#1f6feb')
    ax[0].axhline(P.V_DC, ls='--', lw=1.0, color='#16a34a')
    ax[0].axhline(P.V_DC_CHOP, ls=':', lw=1.0, color='#e67e22')
    ax[0].axhline(P.V_DC_MAX, ls='-', lw=1.0, color='#c0392b')
    ax[0].annotate('consigna 700 V', (0.02, P.V_DC + 6), fontsize=8,
                   color='#16a34a')
    ax[0].annotate('chopper 770 V', (0.02, P.V_DC_CHOP + 6), fontsize=8,
                   color='#e67e22')
    ax[0].annotate('disparo 800 V', (0.02, P.V_DC_MAX + 6), fontsize=8,
                   color='#c0392b')
    ax[0].set_ylabel('$V_{dc}$ [V]')
    ax[0].set_title('Bus DC: regulacion y transitorio de frenado')
    ax[0].set_ylim(520, 830)

    ax[1].plot(t, rec['wref'], lw=1.0, ls='--', color='#7f8c8d',
               label='consigna')
    ax[1].plot(t, rec['wm'], lw=1.5, color='#8e44ad', label='$\\omega_m$')
    ax[1].set_ylabel('velocidad [rad/s]')
    ax[1].legend(fontsize=8, loc='upper right')
    axb = ax[1].twinx()
    axb.plot(t, rec['te'], lw=1.0, color='#e67e22', alpha=0.8)
    axb.set_ylabel('$T_e$ [N m]', color='#e67e22')
    axb.grid(False)
    ax[1].set_title('Motor: velocidad (morado) y par (naranja). '
                    'A t = 0.35 s se ordena frenar')

    ax[2].plot(t, rec['pgrid'] / 1000, lw=1.4, color='#1f6feb',
               label='$P_{red}$')
    ax[2].plot(t, rec['pinv'] / 1000, lw=1.2, color='#16a34a', alpha=0.8,
               label='$P_{motor}$')
    ax[2].axhline(0, color='#2c3e50', lw=1.0)
    ax[2].fill_between(t, 0, rec['pgrid'] / 1000,
                       where=(rec['pgrid'] < 0), color='#c0392b', alpha=0.25)
    ax[2].annotate('REGENERACION\n(potencia hacia la red)', (0.325, -7),
                   fontsize=9, color='#c0392b', weight='bold')
    ax[2].set_ylabel('Potencia [kW]')
    ax[2].legend(fontsize=8, loc='upper right')
    ax[2].set_title('Flujo de potencia: positivo = consume, '
                    'negativo = devuelve a la red')

    ax[3].plot(t, rec['id'], lw=1.4, color='#c0392b', label='$I_d$ (activa)')
    ax[3].plot(t, rec['iq'], lw=1.2, color='#16a34a', label='$I_q$ (reactiva)')
    ax[3].axhline(0, color='#2c3e50', lw=1.0)
    ax[3].set_ylabel('corriente de red [A]')
    ax[3].set_xlabel('t [s]')
    ax[3].legend(fontsize=8, loc='upper right')
    ax[3].set_title('Corriente de red en dq: $I_d$ cambia de signo al '
                    'regenerar, $I_q$ se mantiene en 0 (FP unitario)')
    for a in ax:
        a.axvline(0.35, color='#c0392b', lw=0.8, ls=':')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '04_b2b_temporal.png'), dpi=130)
    plt.close(fig)

    # --- zoom de fase: tension vs corriente antes y despues del frenado ---
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for i, (t0, t1, ttl) in enumerate(
            [(0.300, 0.330, 'MOTORIZANDO: I en fase con V (consume)'),
             (0.365, 0.395, 'REGENERANDO: I en oposicion (devuelve)')]):
        m = _win(rec, t0, t1)
        ax[i].plot(rec['t'][m] * 1000, rec['va'][m], lw=1.3, color='#1f6feb',
                   label='$v_a$ [V]')
        axi = ax[i].twinx()
        axi.plot(rec['t'][m] * 1000, rec['ia'][m], lw=1.5, color='#c0392b',
                 label='$i_a$ [A]')
        axi.grid(False)
        ax[i].set_title(ttl, fontsize=9)
        ax[i].set_xlabel('t [ms]')
        ax[i].set_ylabel('$v_a$ [V]', color='#1f6feb')
        axi.set_ylabel('$i_a$ [A]', color='#c0392b')
        ax[i].axhline(0, color='#2c3e50', lw=0.7)
    fig.suptitle('Prueba del frenado regenerativo: relacion de fase entre '
                 'tension y corriente de red', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '05_fase_regeneracion.png'), dpi=130)
    plt.close(fig)
