/* ============================================================
 * b2b_control.h - Matematica de control del convertidor B2B.
 *
 * Sin dependencias de HAL ni de hardware: esto es codigo puro y por eso
 * se puede verificar contra el modelo de simulacion validado
 * (ver fw/verify/).
 * ============================================================ */
#ifndef B2B_CONTROL_H
#define B2B_CONTROL_H

#include <stdint.h>
#include <stdbool.h>
#include "b2b_config.h"

/* ------------------------------------------------------------------
 * PI con anti-windup por integracion condicional.
 * Es el MISMO esquema que se simulo: si la salida esta saturada, solo
 * se integra cuando el error empuja de vuelta al rango lineal.
 * ------------------------------------------------------------------ */
typedef struct {
    float kp;
    float ki;
    float lo;        /* limite inferior de salida */
    float hi;        /* limite superior de salida */
    float integ;     /* estado del integrador */
} pi_t;

static inline void pi_init(pi_t *p, float kp, float ki, float lo, float hi)
{
    p->kp = kp; p->ki = ki; p->lo = lo; p->hi = hi; p->integ = 0.0f;
}

static inline void pi_reset(pi_t *p) { p->integ = 0.0f; }

/* ff = termino de feedforward (se suma antes de saturar) */
static inline float pi_step(pi_t *p, float err, float dt, float ff)
{
    float u = p->kp * err + p->integ + ff;
    if (u > p->lo && u < p->hi) {
        p->integ += p->ki * err * dt;
    } else if ((u >= p->hi && err < 0.0f) || (u <= p->lo && err > 0.0f)) {
        p->integ += p->ki * err * dt;
    }
    u = p->kp * err + p->integ + ff;
    if (u > p->hi) u = p->hi;
    if (u < p->lo) u = p->lo;
    return u;
}

/* ------------------------------------------------------------------
 * Transformadas de Clarke y Park
 * ------------------------------------------------------------------ */
typedef struct { float a, b; } ab_t;      /* alpha-beta */
typedef struct { float d, q; } dq_t;

/* Clarke invariante en amplitud (3 hilos: ic = -ia - ib) */
static inline ab_t clarke(float ia, float ib)
{
    ab_t o;
    o.a = ia;
    o.b = (ia + 2.0f * ib) * 0.57735026919f;   /* 1/sqrt(3) */
    return o;
}

static inline dq_t park(ab_t x, float cs, float sn)
{
    dq_t o;
    o.d =  x.a * cs + x.b * sn;
    o.q = -x.a * sn + x.b * cs;
    return o;
}

static inline ab_t ipark(dq_t x, float cs, float sn)
{
    ab_t o;
    o.a = x.d * cs - x.q * sn;
    o.b = x.d * sn + x.q * cs;
    return o;
}

/* ------------------------------------------------------------------
 * SVPWM por inyeccion de secuencia cero (min/max).
 * Da el mismo resultado que el SVPWM clasico por sectores pero sin
 * tablas ni ramas: extiende el rango lineal hasta Vdc/sqrt(3).
 * Devuelve 3 ciclos de trabajo en [0, 1].
 * ------------------------------------------------------------------ */
typedef struct { float a, b, c; } duty_t;

static inline duty_t svpwm(ab_t v, float vdc)
{
    duty_t d;
    float inv = (vdc > 1.0f) ? (1.0f / vdc) : 0.0f;
    /* Clarke inversa -> tensiones de fase */
    float va = v.a;
    float vb = -0.5f * v.a + 0.86602540378f * v.b;
    float vc = -0.5f * v.a - 0.86602540378f * v.b;
    /* inyeccion de secuencia cero */
    float vmax = va, vmin = va;
    if (vb > vmax) vmax = vb;
    if (vc > vmax) vmax = vc;
    if (vb < vmin) vmin = vb;
    if (vc < vmin) vmin = vc;
    float voff = -0.5f * (vmax + vmin);
    d.a = 0.5f + (va + voff) * inv;
    d.b = 0.5f + (vb + voff) * inv;
    d.c = 0.5f + (vc + voff) * inv;
    /* recorte de seguridad */
    if (d.a < 0.0f) d.a = 0.0f; if (d.a > 1.0f) d.a = 1.0f;
    if (d.b < 0.0f) d.b = 0.0f; if (d.b > 1.0f) d.b = 1.0f;
    if (d.c < 0.0f) d.c = 0.0f; if (d.c > 1.0f) d.c = 1.0f;
    return d;
}

/* Limita un vector dq a un modulo maximo, conservando su direccion */
static inline dq_t dq_limit(dq_t v, float vmax)
{
    float m2 = v.d * v.d + v.q * v.q;
    if (m2 > vmax * vmax && m2 > 1e-9f) {
        float k = vmax / __builtin_sqrtf(m2);
        v.d *= k; v.q *= k;
    }
    return v;
}

/* ------------------------------------------------------------------
 * PLL trifasico en marco sincrono (SRF-PLL)
 *
 * OJO: la entrada va NORMALIZADA por la amplitud del vector de red. Si se
 * alimenta con Vq en voltios, la ganancia de lazo queda multiplicada por
 * la amplitud (~326 V) y el PLL se vuelve inestable. Este fallo aparecio
 * en la simulacion y esta documentado en el informe de validacion.
 * ------------------------------------------------------------------ */
typedef struct {
    float theta;      /* rad, angulo estimado */
    float w;          /* rad/s, frecuencia estimada */
    float integ;      /* estado del integrador */
    float cs, sn;     /* cos/sin del angulo, cacheados */
    bool  locked;
    float err;        /* error normalizado del ultimo paso */
} pll_t;

void pll_init(pll_t *p);
void pll_step(pll_t *p, float va, float vb, float vc, float dt);

/* ------------------------------------------------------------------
 * Active Front End: lazo de bus + lazo de corriente en dq
 * ------------------------------------------------------------------ */
typedef struct {
    pi_t  pi_vdc;
    pi_t  pi_id;
    pi_t  pi_iq;
    float id_ref, iq_ref;
    float vd_cmd, vq_cmd;
} afe_t;

void afe_init(afe_t *a);
/* p_inv = potencia que consume el inversor [W] (feedforward). Sin ella el
 * bus se dispara en un frenado brusco antes de que reaccione el PI. */
duty_t afe_step(afe_t *a, const pll_t *pll, float ia, float ib,
                float vdc, float vdc_ref, float p_inv, float iq_ref,
                float dt);

/* ------------------------------------------------------------------
 * Inversor: control orientado al campo del PMSM
 * ------------------------------------------------------------------ */
typedef struct {
    pi_t  pi_w;
    pi_t  pi_id;
    pi_t  pi_iq;
    float id_ref, iq_ref;
    float w_ref;          /* rad/s mecanicos, ya rampeado */
    float p_out;          /* W, potencia estimada -> feedforward del AFE */
} foc_t;

void foc_init(foc_t *f);
duty_t foc_step(foc_t *f, float theta_e, float w_mech,
                float ia, float ib, float vdc, float w_ref_target,
                float slew, float dt);

#endif /* B2B_CONTROL_H */
