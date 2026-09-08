"""
b2b_params.py - Parametros unicos del convertidor back-to-back.

TODA la simulacion y la documentacion salen de aqui. Si cambias el punto de
diseno, cambialo SOLO en este archivo y vuelve a correr sim/run_all.py.
"""

import math

# ============================================================ RED / NOMINALES
S_N = 15000.0          # VA   potencia aparente nominal
V_LL = 400.0           # V    tension de red linea-linea (RMS)
F_G = 60.0             # Hz   frecuencia de red
V_PH = V_LL / math.sqrt(3.0)          # 231 V  fase-neutro RMS
I_N = S_N / (math.sqrt(3.0) * V_LL)   # 21.65 A RMS
I_PK = I_N * math.sqrt(2.0)           # 30.6 A pico
W_G = 2 * math.pi * F_G

# ============================================================ BUS DC
V_DC = 700.0           # V    consigna de regulacion
V_DC_MAX = 800.0       # V    disparo duro
V_DC_CHOP = 770.0      # V    umbral del chopper de frenado
C_BUS = 600e-6         # F    4 x 150 uF / 900 V film

# ============================================================ CONMUTACION
F_SW = 16000.0         # Hz   frecuencia de conmutacion (AFE e inversor)
T_S = 1.0 / F_SW       # s    periodo de control (1 ejecucion por periodo PWM)
DEADTIME = 500e-9      # s    tiempo muerto por hardware

# ============================================================ FILTRO LCL
L1 = 1.5e-3            # H    inductor lado convertidor
CF = 10e-6             # F    condensador de filtro (conexion Y)
RD = 6.8               # ohm  amortiguamiento (optimizado: pico 19 dB, 12 W)
L2 = 0.6e-3            # H    inductor lado red
R_L = 0.05             # ohm  resistencia parasita total de los inductores

# ============================================================ PRECARGA
R_PC = 68.0            # ohm  resistencia de precarga
V_PK_RECT = math.sqrt(2.0) * V_LL     # 566 V rectificado natural por diodos
I_INRUSH_MAX = 10.0    # A    limite de inrush admitido

# ============================================================ SEMICONDUCTORES
# Wolfspeed C3M0075120K (el de la libreria).  Para el build real ver
# C3M0040120K: mismo TO-247-4, 40 mOhm -> menos perdidas.
SIC_NAME = 'C3M0075120K'
RDSON_25 = 75e-3       # ohm  a 25 C
RDSON_K = 1.5          # factor a 125 C (aprox. del datasheet)
E_SW_REF = 0.30e-3     # J    Eon+Eoff a la referencia de datasheet
E_SW_V_REF = 800.0     # V
E_SW_I_REF = 20.0      # A
V_F_BODY = 3.3         # V    caida del diodo de cuerpo SiC

# Alternativa recomendada para 15 kVA
SIC_ALT_NAME = 'C3M0040120K'
RDSON_ALT_25 = 40e-3

# ============================================================ TERMICO
T_A = 45.0             # C    ambiente dentro del gabinete
T_J_MAX = 125.0        # C    objetivo de union (derate desde 175)
RTH_JC = 0.60          # C/W  union-capsula (TO-247-4)
RTH_CS = 0.30          # C/W  capsula-disipador (interfaz termica)
N_SW_TOTAL = 12        # dispositivos sobre el disipador comun

# ============================================================ MOTOR PMSM
P_POLES = 3            # pares de polos
LAMBDA_PM = 0.35       # Wb   flujo de iman permanente
LD = 3.0e-3            # H
LQ = 3.0e-3            # H
RS = 0.15              # ohm  resistencia de estator
J_MOT = 0.02           # kg m2  inercia (motor + carga)
B_VISC = 0.002         # N m s  friccion viscosa
T_LOAD = 40.0          # N m    par resistente de la carga
IQ_LIM = 40.0          # A      limite de corriente de par
R_BRAKE = 12.0         # ohm    resistencia de frenado del chopper
# Par = 1.5 * p * lambda_pm * iq
KT = 1.5 * P_POLES * LAMBDA_PM        # 1.575 N m / A

# ============================================================ LIMITES / SPEC
THD_LIMIT = 5.0        # %    IEEE 519 / IEC 61000-3-12 para corriente de red
PF_MIN = 0.99          # factor de potencia minimo en el punto nominal
V_DC_RIPPLE_MAX = 2.0  # %    rizado admisible en regimen
PM_MIN = 45.0          # grados, margen de fase minimo de los lazos
GM_MIN = 6.0           # dB,  margen de ganancia minimo


def resumen():
    return f"""PUNTO DE DISENO
  S = {S_N/1000:.0f} kVA | {V_LL:.0f} V_LL | {F_G:.0f} Hz | I_n = {I_N:.2f} A
  Bus DC = {V_DC:.0f} V (max {V_DC_MAX:.0f} V) | C_bus = {C_BUS*1e6:.0f} uF
  f_sw = {F_SW/1000:.0f} kHz | T_s = {T_S*1e6:.1f} us | dead-time = {DEADTIME*1e9:.0f} ns
  LCL: L1 = {L1*1e3:.2f} mH | Cf = {CF*1e6:.1f} uF | Rd = {RD:.1f} ohm | L2 = {L2*1e3:.2f} mH
  SiC: {SIC_NAME} ({RDSON_25*1e3:.0f} mOhm) x {N_SW_TOTAL}
  Motor: PMSM p={P_POLES} lambda={LAMBDA_PM} Wb Kt={KT:.3f} Nm/A J={J_MOT} kg m2"""


if __name__ == '__main__':
    print(resumen())
