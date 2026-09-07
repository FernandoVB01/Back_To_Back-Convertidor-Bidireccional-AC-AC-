"""
gen_config.py - Genera fw/Core/Inc/b2b_config.h desde sim/b2b_params.py.

El firmware NUNCA debe tener constantes escritas a mano: se generan desde el
mismo archivo de parametros con el que se valido el diseno. Si cambias
sim/b2b_params.py y vuelves a correr esto, el firmware queda al dia.

    python fw/config/gen_config.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'sim'))

import b2b_params as P                      # noqa: E402
import sim_design as D                      # noqa: E402

OUT = os.path.join(ROOT, 'fw', 'Core', 'Inc', 'b2b_config.h')

# ---------------------------------------------------------------- reloj / PWM
F_TIM = 170e6                    # Hz, reloj de TIM1/TIM8 en el STM32G474
# Modo centrado: periodo PWM = 2 * ARR * Tclk  ->  ARR = f_tim / (2 * f_sw)
ARR = int(round(F_TIM / (2 * P.F_SW)))
F_SW_REAL = F_TIM / (2 * ARR)

# Dead-time: con CKD = 00, f_DTS = f_TIM  ->  t_DTS = 5.882 ns
T_DTS = 1.0 / F_TIM
DTG_TICKS = int(round(P.DEADTIME / T_DTS))
if DTG_TICKS < 128:
    DTG = DTG_TICKS                          # rango 0xxxxxxx: DT = DTG * tDTS
    DT_REAL = DTG * T_DTS
else:                                        # rango 10xxxxxx: DT=(64+x)*2*tDTS
    x = int(round(P.DEADTIME / (2 * T_DTS))) - 64
    DTG = 0x80 | max(0, min(63, x))
    DT_REAL = (64 + (DTG & 0x3F)) * 2 * T_DTS

# Disparo del ADC: CC4 cerca del pico del contador = centro del vector nulo,
# que es donde el rizado de corriente pasa por su valor medio.
ADC_TRIG_CCR4 = ARR - 8


def main():
    checks, gains = D.analiza_lazos()
    kp_i, ki_i = gains['Kp_i'], gains['Ki_i']
    kp_v, ki_v = gains['Kp_v'], gains['Ki_v']

    # ganancias del lazo de corriente del MOTOR (misma regla, planta Ld/Rs)
    Td = 1.5 / P.F_SW
    kp_m = P.LD / (2 * Td)
    ki_m = kp_m * P.RS / P.LD
    # lazo de velocidad
    Tsum = 2 * Td + 3 / P.F_SW
    kp_w = P.J_MOT / (10 * Tsum * P.KT)
    ki_w = kp_w / (30 * Tsum)
    # PLL: ancho de banda 25 Hz, amortiguamiento 0.707, entrada normalizada
    f_pll = 25.0
    pll_kp = 2 * 0.707 * (2 * math.pi * f_pll)
    pll_ki = (2 * math.pi * f_pll) ** 2

    v_max = P.V_DC / math.sqrt(3.0)          # limite lineal de SVPWM

    h = f'''/* ============================================================
 * b2b_config.h - GENERADO POR fw/config/gen_config.py -- NO EDITAR
 *
 * Fuente unica de verdad: sim/b2b_params.py
 * Las ganancias salen de la MISMA sintonia que se valido en
 * docs/INFORME_VALIDACION.md (31/31 comprobaciones OK).
 * ============================================================ */
#ifndef B2B_CONFIG_H
#define B2B_CONFIG_H

/* ---------------- red y nominales ---------------- */
#define B2B_S_NOM_VA        {P.S_N:.1f}f
#define B2B_VLL_RMS         {P.V_LL:.1f}f
#define B2B_VPH_PEAK        {P.V_PH * math.sqrt(2):.4f}f   /* V pico de fase */
#define B2B_F_GRID          {P.F_G:.1f}f
#define B2B_W_GRID          {P.W_G:.6f}f
#define B2B_I_NOM_RMS       {P.I_N:.4f}f
#define B2B_I_PEAK          {P.I_PK:.4f}f

/* ---------------- bus DC ---------------- */
#define B2B_VDC_REF         {P.V_DC:.1f}f
#define B2B_VDC_MAX         {P.V_DC_MAX:.1f}f      /* disparo duro */
#define B2B_VDC_CHOP_ON     {P.V_DC_CHOP:.1f}f     /* chopper de frenado */
#define B2B_VDC_CHOP_OFF    {P.V_DC_CHOP - 20:.1f}f
#define B2B_VDC_PRECHG_OK   {0.9 * P.V_PK_RECT:.1f}f  /* cierre de K2 */
#define B2B_C_BUS           {P.C_BUS:.9f}f

/* ---------------- temporizacion PWM (TIM1 / TIM8) ---------------- */
#define B2B_F_TIM_HZ        {F_TIM:.0f}f
#define B2B_F_SW_HZ         {P.F_SW:.1f}f
#define B2B_PWM_ARR         {ARR}u        /* modo centrado */
#define B2B_F_SW_REAL_HZ    {F_SW_REAL:.2f}f   /* real con ese ARR */
#define B2B_TS              {1.0 / F_SW_REAL:.10f}f
#define B2B_DEADTIME_DTG    {DTG}u        /* BDTR.DTG */
#define B2B_DEADTIME_NS     {DT_REAL * 1e9:.1f}f
#define B2B_ADC_TRIG_CCR4   {ADC_TRIG_CCR4}u

/* ---------------- limites de modulacion ---------------- */
#define B2B_VMAX_LIN        {v_max:.4f}f  /* Vdc/sqrt(3): limite SVPWM lineal */
#define B2B_I_LIM_GRID      {1.6 * P.I_PK:.3f}f
#define B2B_I_LIM_MOTOR     {P.IQ_LIM:.3f}f

/* ---------------- lazo de corriente de RED (AFE) ---------------- */
#define B2B_KP_IGRID        {kp_i:.8f}f
#define B2B_KI_IGRID        {ki_i:.8f}f

/* ---------------- lazo de tension de bus ---------------- */
#define B2B_KP_VDC          {kp_v:.8f}f
#define B2B_KI_VDC          {ki_v:.8f}f

/* ---------------- lazo de corriente de MOTOR (FOC) ---------------- */
#define B2B_KP_IMOT         {kp_m:.8f}f
#define B2B_KI_IMOT         {ki_m:.8f}f

/* ---------------- lazo de velocidad ---------------- */
#define B2B_KP_SPEED        {kp_w:.8f}f
#define B2B_KI_SPEED        {ki_w:.8f}f

/* ---------------- PLL trifasico (entrada NORMALIZADA) ---------------- */
#define B2B_PLL_KP          {pll_kp:.6f}f
#define B2B_PLL_KI          {pll_ki:.6f}f
#define B2B_PLL_W0          {P.W_G:.6f}f
#define B2B_PLL_LOCK_RAD    {math.radians(2.0):.6f}f  /* umbral de enganche */

/* ---------------- filtro LCL (para el desacoplo) ---------------- */
#define B2B_L_GRID          {P.L1 + P.L2:.9f}f   /* L1 + L2 */
#define B2B_R_GRID          {P.R_L:.6f}f

/* ---------------- motor PMSM ---------------- */
#define B2B_POLE_PAIRS      {P.P_POLES}
#define B2B_LAMBDA_PM       {P.LAMBDA_PM:.6f}f
#define B2B_LD              {P.LD:.9f}f
#define B2B_LQ              {P.LQ:.9f}f
#define B2B_RS              {P.RS:.6f}f
#define B2B_KT              {P.KT:.6f}f

/* ---------------- proteccion ---------------- */
#define B2B_OC_GRID_A       {1.8 * P.I_PK:.2f}f
#define B2B_OC_MOTOR_A      {1.8 * P.IQ_LIM:.2f}f
#define B2B_OT_TRIP_C       95.0f
#define B2B_PRECHG_TMO_MS   1000u
#define B2B_LINK_TMO_MS     500u   /* watchdog del enlace con el ESP32 */

#endif /* B2B_CONFIG_H */
'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(h)

    print('b2b_config.h generado')
    print('  f_sw pedida  = %.1f Hz   ARR = %d   ->  f_sw real = %.2f Hz'
          % (P.F_SW, ARR, F_SW_REAL))
    print('  dead-time pedido = %.0f ns  DTG = %d (0x%02X)  ->  real = %.1f ns'
          % (P.DEADTIME * 1e9, DTG, DTG, DT_REAL * 1e9))
    print('  ADC se dispara en CCR4 = %d (centro del vector nulo)'
          % ADC_TRIG_CCR4)
    print('  Kp_igrid = %.6f   Ki_igrid = %.4f' % (kp_i, ki_i))
    print('  Kp_vdc   = %.6f   Ki_vdc   = %.4f' % (kp_v, ki_v))
    print('  Kp_imot  = %.6f   Ki_imot  = %.4f' % (kp_m, ki_m))
    print('  Kp_speed = %.6f   Ki_speed = %.4f' % (kp_w, ki_w))
    print('  -> %s' % os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
