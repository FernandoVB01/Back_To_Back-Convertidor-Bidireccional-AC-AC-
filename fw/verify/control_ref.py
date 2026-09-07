"""
control_ref.py - Transliteracion LITERAL de fw/Core/Inc/b2b_control.h a Python.

Objetivo: poder ejecutar EXACTAMENTE la misma matematica que corre en el
STM32 contra la planta ya validada, y contra el circuito SPICE de KiCad.

Regla: cada funcion de aqui debe ser linea por linea equivalente a su gemela
en C. Si cambias una, cambia la otra.
"""

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CFG = os.path.join(ROOT, 'fw', 'Core', 'Inc', 'b2b_config.h')


# --------------------------------------------------------------- config
def load_config(path=CFG):
    """Lee b2b_config.h y devuelve un dict con los #define numericos.

    Asi la referencia usa LAS MISMAS constantes que compila el firmware:
    no hay forma de que se desincronicen.
    """
    cfg = {}
    # acepta los sufijos de C: 5312u, 0.5f, 1e-3f ...
    rx = re.compile(r'#define\s+(B2B_\w+)\s+([-+0-9.eE]+)[fuFU]?\s*(?:/\*|$)')
    with open(path, encoding='utf-8') as f:
        for line in f:
            m = rx.match(line.strip())
            if m:
                try:
                    cfg[m.group(1)] = float(m.group(2))
                except ValueError:
                    pass
    if not cfg:
        raise RuntimeError('no se pudo leer %s (ejecuta gen_config.py)' % path)
    return cfg


CFG_D = load_config()


def C(name):
    return CFG_D[name]


# --------------------------------------------------------------- PI
class PI:
    """Equivalente de pi_t / pi_step() en b2b_control.h"""

    def __init__(self, kp, ki, lo, hi):
        self.kp, self.ki, self.lo, self.hi = kp, ki, lo, hi
        self.integ = 0.0

    def reset(self):
        self.integ = 0.0

    def step(self, err, dt, ff=0.0):
        u = self.kp * err + self.integ + ff
        if self.lo < u < self.hi:
            self.integ += self.ki * err * dt
        elif (u >= self.hi and err < 0.0) or (u <= self.lo and err > 0.0):
            self.integ += self.ki * err * dt
        u = self.kp * err + self.integ + ff
        return min(max(u, self.lo), self.hi)


# --------------------------------------------------------------- Clarke/Park
def clarke(ia, ib):
    return (ia, (ia + 2.0 * ib) * 0.57735026919)


def park(a, b, cs, sn):
    return (a * cs + b * sn, -a * sn + b * cs)


def ipark(d, q, cs, sn):
    return (d * cs - q * sn, d * sn + q * cs)


# --------------------------------------------------------------- SVPWM
def svpwm(valpha, vbeta, vdc):
    """Inyeccion de secuencia cero (min/max). Devuelve (da, db, dc) en [0,1]."""
    inv = (1.0 / vdc) if vdc > 1.0 else 0.0
    va = valpha
    vb = -0.5 * valpha + 0.86602540378 * vbeta
    vc = -0.5 * valpha - 0.86602540378 * vbeta
    vmax = max(va, vb, vc)
    vmin = min(va, vb, vc)
    voff = -0.5 * (vmax + vmin)
    d = [0.5 + (va + voff) * inv,
         0.5 + (vb + voff) * inv,
         0.5 + (vc + voff) * inv]
    return tuple(min(max(x, 0.0), 1.0) for x in d)


def dq_limit(d, q, vmax):
    m2 = d * d + q * q
    if m2 > vmax * vmax and m2 > 1e-9:
        k = vmax / math.sqrt(m2)
        return d * k, q * k
    return d, q


# --------------------------------------------------------------- PLL
class PLL:
    """SRF-PLL con entrada NORMALIZADA (ver nota en b2b_control.h)."""

    def __init__(self):
        self.theta = 0.0
        self.w = C('B2B_PLL_W0')
        self.integ = C('B2B_PLL_W0')
        self.cs, self.sn = 1.0, 0.0
        self.locked = False
        self.err = 0.0

    def step(self, va, vb, vc, dt):
        al, be = clarke(va, vb)
        vd, vq = park(al, be, self.cs, self.sn)
        amp = math.hypot(vd, vq)
        # normalizacion: sin ella la ganancia de lazo se multiplica por la
        # amplitud de red (~326 V) y el PLL se vuelve inestable
        e = (vq / amp) if amp > 1.0 else 0.0
        self.err = e
        self.integ += C('B2B_PLL_KI') * e * dt
        self.w = self.integ + C('B2B_PLL_KP') * e
        self.theta = (self.theta + self.w * dt) % (2.0 * math.pi)
        self.cs = math.cos(self.theta)
        self.sn = math.sin(self.theta)
        self.locked = abs(e) < C('B2B_PLL_LOCK_RAD')
        return self.theta


# --------------------------------------------------------------- AFE
class AFE:
    def __init__(self):
        ilim = C('B2B_I_LIM_GRID')
        vmax = C('B2B_VMAX_LIN')
        self.pi_vdc = PI(C('B2B_KP_VDC'), C('B2B_KI_VDC'), -ilim, ilim)
        self.pi_id = PI(C('B2B_KP_IGRID'), C('B2B_KI_IGRID'), -vmax, vmax)
        self.pi_iq = PI(C('B2B_KP_IGRID'), C('B2B_KI_IGRID'), -vmax, vmax)
        self.id_ref = self.iq_ref = 0.0
        self.vd = self.vq = 0.0

    def step(self, pll, id_m, iq_m, vdc, vdc_ref, p_inv, iq_ref, dt):
        vg = C('B2B_VPH_PEAK')
        L = C('B2B_L_GRID')
        w = C('B2B_W_GRID')
        # feedforward de potencia del inversor: sin el, un frenado brusco
        # dispara el bus antes de que reaccione el PI de tension
        id_ff = p_inv / (1.5 * vg) if vg > 1.0 else 0.0
        self.id_ref = self.pi_vdc.step(vdc_ref - vdc, dt, ff=id_ff)
        self.iq_ref = iq_ref
        ud = self.pi_id.step(self.id_ref - id_m, dt)
        uq = self.pi_iq.step(self.iq_ref - iq_m, dt)
        # desacoplo cruzado + feedforward de la tension de red
        self.vd = vg + w * L * iq_m - ud
        self.vq = 0.0 - w * L * id_m - uq
        self.vd, self.vq = dq_limit(self.vd, self.vq, C('B2B_VMAX_LIN'))
        al, be = ipark(self.vd, self.vq, pll.cs, pll.sn)
        return svpwm(al, be, vdc)


# --------------------------------------------------------------- FOC
class FOC:
    def __init__(self):
        vmax = C('B2B_VMAX_LIN')
        iq_lim = C('B2B_I_LIM_MOTOR')
        self.pi_w = PI(C('B2B_KP_SPEED'), C('B2B_KI_SPEED'), -iq_lim, iq_lim)
        self.pi_id = PI(C('B2B_KP_IMOT'), C('B2B_KI_IMOT'), -vmax, vmax)
        self.pi_iq = PI(C('B2B_KP_IMOT'), C('B2B_KI_IMOT'), -vmax, vmax)
        self.w_ref = 0.0
        self.id_ref = self.iq_ref = 0.0
        self.p_out = 0.0
        self.vd = self.vq = 0.0

    def step(self, theta_e, w_mech, isd, isq, vdc, w_tgt, slew, dt):
        # rampa de consigna: un variador nunca aplica un escalon
        dw = w_tgt - self.w_ref
        self.w_ref += max(-slew * dt, min(slew * dt, dw))
        self.iq_ref = self.pi_w.step(self.w_ref - w_mech, dt)
        self.id_ref = 0.0                      # sin debilitamiento de campo
        we = C('B2B_POLE_PAIRS') * w_mech
        ud = self.pi_id.step(self.id_ref - isd, dt)
        uq = self.pi_iq.step(self.iq_ref - isq, dt)
        self.vd = ud - we * C('B2B_LQ') * isq
        self.vq = uq + we * (C('B2B_LD') * isd + C('B2B_LAMBDA_PM'))
        self.vd, self.vq = dq_limit(self.vd, self.vq, C('B2B_VMAX_LIN'))
        self.p_out = 1.5 * (self.vd * isd + self.vq * isq)
        cs, sn = math.cos(theta_e), math.sin(theta_e)
        al, be = ipark(self.vd, self.vq, cs, sn)
        return svpwm(al, be, vdc)


# --------------------------------------------------------------- gate + DT
def duties_to_gates(duty, t0, tsw, deadtime):
    """Convierte un ciclo de trabajo en los flancos REALES de las 6 puertas,
    con el tiempo muerto que inserta el hardware del TIM1.

    Devuelve, por fase, dos listas PWL [(t, v), ...] para alto y bajo.
    PWM centrado: el pulso esta centrado en el periodo.
    """
    out = []
    for d in duty:
        ton = d * tsw
        t_start = t0 + (tsw - ton) * 0.5
        t_end = t_start + ton
        # el alto conduce [t_start+DT, t_end]; el bajo el complemento, con
        # DT de guarda a cada lado -> nunca conducen a la vez
        hi = [(t0, 0.0), (t_start + deadtime, 0.0),
              (t_start + deadtime + 1e-9, 1.0),
              (t_end, 1.0), (t_end + 1e-9, 0.0), (t0 + tsw, 0.0)]
        lo = [(t0, 1.0), (t_start, 1.0), (t_start + 1e-9, 0.0),
              (t_end + deadtime, 0.0), (t_end + deadtime + 1e-9, 1.0),
              (t0 + tsw, 1.0)]
        out.append((hi, lo))
    return out


if __name__ == '__main__':
    print('Constantes leidas de b2b_config.h: %d' % len(CFG_D))
    for k in ('B2B_F_SW_REAL_HZ', 'B2B_PWM_ARR', 'B2B_DEADTIME_NS',
              'B2B_KP_IGRID', 'B2B_KI_IGRID', 'B2B_KP_VDC', 'B2B_KI_VDC',
              'B2B_VMAX_LIN'):
        print('  %-22s = %g' % (k, CFG_D[k]))
    # prueba rapida de SVPWM: modulacion maxima lineal
    vmax = C('B2B_VMAX_LIN')
    d = svpwm(vmax, 0.0, C('B2B_VDC_REF'))
    print('SVPWM a modulacion lineal maxima -> duties %.4f %.4f %.4f'
          % d)
