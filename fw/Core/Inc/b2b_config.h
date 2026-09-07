/* ============================================================
 * b2b_config.h - GENERADO POR fw/config/gen_config.py -- NO EDITAR
 *
 * Fuente unica de verdad: sim/b2b_params.py
 * Las ganancias salen de la MISMA sintonia que se valido en
 * docs/INFORME_VALIDACION.md (31/31 comprobaciones OK).
 * ============================================================ */
#ifndef B2B_CONFIG_H
#define B2B_CONFIG_H

/* ---------------- red y nominales ---------------- */
#define B2B_S_NOM_VA        15000.0f
#define B2B_VLL_RMS         400.0f
#define B2B_VPH_PEAK        326.5986f   /* V pico de fase */
#define B2B_F_GRID          60.0f
#define B2B_W_GRID          376.991118f
#define B2B_I_NOM_RMS       21.6506f
#define B2B_I_PEAK          30.6186f

/* ---------------- bus DC ---------------- */
#define B2B_VDC_REF         700.0f
#define B2B_VDC_MAX         800.0f      /* disparo duro */
#define B2B_VDC_CHOP_ON     770.0f     /* chopper de frenado */
#define B2B_VDC_CHOP_OFF    750.0f
#define B2B_VDC_PRECHG_OK   509.1f  /* cierre de K2 */
#define B2B_C_BUS           0.000600000f

/* ---------------- temporizacion PWM (TIM1 / TIM8) ---------------- */
#define B2B_F_TIM_HZ        170000000f
#define B2B_F_SW_HZ         16000.0f
#define B2B_PWM_ARR         5312u        /* modo centrado */
#define B2B_F_SW_REAL_HZ    16001.51f   /* real con ese ARR */
#define B2B_TS              0.0000624941f
#define B2B_DEADTIME_DTG    85u        /* BDTR.DTG */
#define B2B_DEADTIME_NS     500.0f
#define B2B_ADC_TRIG_CCR4   5304u

/* ---------------- limites de modulacion ---------------- */
#define B2B_VMAX_LIN        404.1452f  /* Vdc/sqrt(3): limite SVPWM lineal */
#define B2B_I_LIM_GRID      48.990f
#define B2B_I_LIM_MOTOR     40.000f

/* ---------------- lazo de corriente de RED (AFE) ---------------- */
#define B2B_KP_IGRID        11.20000000f
#define B2B_KI_IGRID        266.66666667f

/* ---------------- lazo de tension de bus ---------------- */
#define B2B_KP_VDC          0.76231602f
#define B2B_KI_VDC          225.94626537f

/* ---------------- lazo de corriente de MOTOR (FOC) ---------------- */
#define B2B_KP_IMOT         16.00000000f
#define B2B_KI_IMOT         800.00000000f

/* ---------------- lazo de velocidad ---------------- */
#define B2B_KP_SPEED        3.38624339f
#define B2B_KI_SPEED        300.99941211f

/* ---------------- PLL trifasico (entrada NORMALIZADA) ---------------- */
#define B2B_PLL_KP          222.110601f
#define B2B_PLL_KI          24674.011003f
#define B2B_PLL_W0          376.991118f
#define B2B_PLL_LOCK_RAD    0.034907f  /* umbral de enganche */

/* ---------------- filtro LCL (para el desacoplo) ---------------- */
#define B2B_L_GRID          0.002100000f   /* L1 + L2 */
#define B2B_R_GRID          0.050000f

/* ---------------- motor PMSM ---------------- */
#define B2B_POLE_PAIRS      3
#define B2B_LAMBDA_PM       0.350000f
#define B2B_LD              0.003000000f
#define B2B_LQ              0.003000000f
#define B2B_RS              0.150000f
#define B2B_KT              1.575000f

/* ---------------- proteccion ---------------- */
#define B2B_OC_GRID_A       55.11f
#define B2B_OC_MOTOR_A      72.00f
#define B2B_OT_TRIP_C       95.0f
#define B2B_PRECHG_TMO_MS   1000u
#define B2B_LINK_TMO_MS     500u   /* watchdog del enlace con el ESP32 */

#endif /* B2B_CONFIG_H */
