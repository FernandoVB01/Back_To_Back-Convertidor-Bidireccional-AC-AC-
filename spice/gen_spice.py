"""
gen_spice.py - Simulaciones SPICE del convertidor (LTspice en batch).

Lo que SPICE aporta y el modelo promediado de sim/ no puede dar:
  A) El transitorio de conmutacion real del medio puente SiC con la
     INDUCTANCIA PARASITA del lazo -> sobretension de drain, dv/dt y
     campaneo de gate. Es lo que valida la regla de "lazo < 20 nH" del
     floorplan de PCB.
  B) Barrido de la inductancia de lazo: cuanta sobretension cuesta cada nH.
  C) Respuesta AC del filtro LCL, para contrastar con el modelo analitico.
  D) Transitorio de precarga con la resistencia real.

Los .net generados se pueden ABRIR DIRECTAMENTE en LTspice (File > Open) y
tambien se ejecutan aqui en batch.

    python spice/gen_spice.py
"""

import os
import re
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'sim'))
import b2b_params as P                       # noqa: E402

NET = os.path.join(HERE, 'net')
OUT = os.path.join(ROOT, 'sim', 'out')
os.makedirs(NET, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

LTSPICE = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                       'Programs', 'ADI', 'LTspice', 'LTspice.exe')

plt.rcParams.update({'figure.facecolor': '#ffffff', 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})


# ---------------------------------------------------------------- modelo SiC
# VDMOS aproximado a un C3M0075120K (1200 V, 75 mOhm, TO-247-4).
# No es el modelo del fabricante: sirve para evaluar el efecto de las
# PARASITAS DE LAYOUT, que es el objetivo de esta simulacion.
SIC_MODEL = """
.model SiC1200 VDMOS(Rg=4 Vto=2.6 Kp=22 Lambda=0.002 Cgdmax=1.8n Cgdmin=8p
+ Cgs=1.1n Cjo=0.9n Is=3e-14 Rd=48m Rs=12m Rb=1m mfg=Wolfspeed
+ Vds=1200 Ron=75m Qg=51n)
"""


# ---------------------------------------------------------------- utilidades
def run_lt(path):
    """Ejecuta LTspice en batch y devuelve el .raw en ASCII."""
    if not os.path.isfile(LTSPICE):
        raise FileNotFoundError('LTspice no encontrado en ' + LTSPICE)
    raw = os.path.splitext(path)[0] + '.raw'
    if os.path.exists(raw):
        os.remove(raw)
    subprocess.run([LTSPICE, '-b', '-ascii', '-Run', path],
                   check=False, capture_output=True, timeout=300)
    if not os.path.exists(raw):
        log = os.path.splitext(path)[0] + '.log'
        msg = open(log, errors='replace').read()[-800:] \
            if os.path.exists(log) else '(sin log)'
        raise RuntimeError('LTspice no genero .raw para %s\n%s'
                           % (os.path.basename(path), msg))
    return parse_raw(raw)


def parse_raw(path):
    """Parser del .raw ASCII de LTspice -> dict nombre -> np.array.

    Maneja los DOS formatos de LTspice:
      - 'real'    (.tran, .dc): un numero por variable y punto.
      - 'complex' (.ac):        DOS numeros (real, imaginaria) por variable.
    Confundirlos desalinea todas las columnas y da resultados absurdos.
    """
    with open(path, 'r', errors='replace') as f:
        txt = f.read()
    mvars = re.search(r'Variables:\s*\n(.*?)\nValues:\s*\n', txt, re.S)
    names = []
    for line in mvars.group(1).strip().split('\n'):
        parts = [p for p in line.split('\t') if p.strip()]
        if len(parts) >= 2:
            names.append(parts[1])
    npts = int(re.search(r'No\. Points:\s*(\d+)', txt).group(1))
    is_cx = bool(re.search(r'Flags:.*complex', txt, re.I))
    body = txt.split('Values:\n', 1)[1]
    nums = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', body)
    nv = len(names)
    per = 2 if is_cx else 1
    # vectorizado: un bucle de Python sobre millones de numeros tarda
    # minutos con archivos .raw de decenas de MB
    width = 1 + nv * per                         # indice + variables
    arr = np.asarray(nums[:npts * width], dtype=float).reshape(npts, width)
    vals = arr[:, 1:]
    if is_cx:
        data = vals[:, 0::2] + 1j * vals[:, 1::2]
    else:
        data = vals
    return {n: data[:, i] for i, n in enumerate(names)}


def write(name, text):
    p = os.path.join(NET, name)
    with open(p, 'w') as f:
        f.write(text)
    return p


# =====================================================================
# A) MEDIO PUENTE SiC CON PARASITAS DE LAYOUT
# =====================================================================
def netlist_halfbridge(l_loop_nh, l_gate_nh=10.0, rg_on=10.0, rg_off=3.3):
    """Prueba de doble pulso. La inductancia parasita va DENTRO del lazo de
    conmutacion (condensador -> MOSFET alto -> MOSFET bajo -> vuelta), que es
    el unico sitio donde produce sobretension real."""
    return f"""* Medio puente SiC 1200 V - prueba de doble pulso
* L_lazo = {l_loop_nh} nH   L_gate = {l_gate_nh} nH
* Rg_on = {rg_on} ohm   Rg_off = {rg_off} ohm   Vbus = {P.V_DC} V
Vbus  dcpc 0 {P.V_DC}
Cdec  dcpc dcnc 2u
Rgnd  dcnc 0 1u
* --- parasita del lazo, repartida entre el rail + y el rail - ---
Lp    dcpc dcp {l_loop_nh / 2}n Rser=0.35
Ln    dcn  dcnc {l_loop_nh / 2}n Rser=0.35
* --- rama superior: apagada, su diodo de cuerpo hace de freewheel ---
MH    dcp  gh sw sw SiC1200
* El gate del pasivo NO se sujeta con una fuente ideal: lleva su Rg real,
* que es lo que permite ver el encendido parasito por Miller.
Vghs  ghs  sw -4
Rgh   ghs  gh {rg_off}
* --- rama inferior: la que conmuta ---
ML    sw   gl kl kl SiC1200
Lk    kl   dcn 1n Rser=0.15
* --- carga: doble pulso, la corriente la construye el primer pulso ---
Lload dcpc sw 70u Rser=0.05
* --- driver con Rg partido (encendido lento, apagado rapido) ---
Vdrv  drv kl PWL(0 -4 100n -4 115n 15 3u 15 3.015u -4 4u -4 4.015u 15
+ 4.6u 15 4.615u -4 8u -4)
Rgon  drv gm {rg_on}
Rgoff drv gm {rg_off}
Dgoff gm drv Dfast
Lgate gm gl {l_gate_nh}n Rser=0.2
.model Dfast D(Ron=0.05 Roff=1meg Vfwd=0.6)
{SIC_MODEL}
.tran 0.02n 5.2u 0 0.2n uic
.backanno
.end
"""


def sim_halfbridge():
    checks = []
    casos = [(5.0, 'lazo apretado (objetivo del floorplan)'),
             (20.0, 'lazo del diseno (< 20 nH)'),
             (60.0, 'lazo descuidado'),
             (150.0, 'lazo malo (cables largos)')]
    res = {}
    for lnh, _lbl in casos:
        p = write('hb_%dnH.net' % int(lnh), netlist_halfbridge(lnh))
        res[lnh] = run_lt(p)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    tabla = []
    for (lnh, lbl), col in zip(casos, ['#16a34a', '#1f6feb', '#e67e22',
                                       '#c0392b']):
        d = res[lnh]
        t = np.real(d['time']) * 1e9
        vsw = np.real(d.get('V(sw)', d.get('V(SW)')))
        vgh = np.real(d.get('V(gh)', d.get('V(GH)')))
        # Vgs del transistor PASIVO (el alto): aqui se ve el encendido
        # parasito por el dv/dt a traves de Cgd
        vgs = vgh - vsw
        m = (t > 2900) & (t < 4100)      # ventana del apagado (doble pulso)
        vpk = float(np.max(vsw[m]))
        over = vpk - P.V_DC
        # dv/dt por tiempo de subida 10-90 %: el gradiente instantaneo sobre
        # un paso adaptativo da valores absurdos (dos puntos casi pegados)
        tt = np.real(d['time'])[m]
        v10, v90 = 0.1 * P.V_DC, 0.9 * P.V_DC
        try:
            i0 = int(np.where(vsw[m] > v10)[0][0])
            i1 = int(np.where(vsw[m] > v90)[0][0])
            trise = max(tt[i1] - tt[i0], 1e-12)
            dvdt = (v90 - v10) / trise / 1e9          # V/ns
        except IndexError:
            dvdt = float('nan')
        vgs_pk = float(np.max(vgs[m]))
        vgs_min = float(np.min(vgs[m]))
        vgs_pk = vgs_pk + 4.0            # respecto al nivel de apagado (-4 V)
        tabla.append((lnh, lbl, vpk, over, dvdt, vgs_pk, vgs_min))
        ax[0].plot(t[m], vsw[m], lw=1.3, color=col,
                   label='%g nH  (pico %.0f V)' % (lnh, vpk))
        ax[1].plot(t[m], vgs[m], lw=1.3, color=col, label='%g nH' % lnh)

    ax[0].axhline(P.V_DC, ls='--', lw=1.0, color='#7f8c8d')
    ax[0].axhline(1200, ls='-', lw=1.2, color='#c0392b')
    ax[0].annotate('limite del dispositivo 1200 V', (200, 1215), fontsize=8,
                   color='#c0392b')
    ax[0].set_xlabel('t [ns]'); ax[0].set_ylabel('$V_{sw}$ [V]')
    ax[0].set_title('Sobretension en el nodo de conmutacion\n'
                    'segun la inductancia del lazo')
    ax[0].legend(fontsize=8)
    ax[1].axhline(20, ls='-', lw=1.0, color='#c0392b')
    ax[1].axhline(-6, ls='-', lw=1.0, color='#c0392b')
    ax[1].axhline(2.6, ls=':', lw=1.2, color='#e67e22')
    ax[1].annotate('$V_{th}$ = 2.6 V  (por encima: encendido parasito)',
                   (2950, 3.4), fontsize=8, color='#e67e22')
    ax[1].set_xlabel('t [ns]'); ax[1].set_ylabel('$V_{gs}$ [V]')
    ax[1].set_title('$V_{gs}$ del transistor PASIVO: encendido parasito '
                    'por dv/dt a traves de $C_{gd}$')
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '06_spice_halfbridge.png'), dpi=130)
    plt.close(fig)

    d20 = [r for r in tabla if r[0] == 20.0][0]
    checks.append(dict(name='SPICE: sobretension con lazo de 20 nH',
                       value=d20[2], limit=1200.0 * 0.8, ok=d20[2] < 960,
                       unit='V',
                       note='pico en el nodo de conmutacion; '
                            'margen sobre los 1200 V del SiC'))
    checks.append(dict(name='SPICE: dv/dt con lazo de 20 nH', value=d20[4],
                       limit=50.0, ok=d20[4] < 50.0, unit='V/ns',
                       note='CMTI del driver debe superarlo (UCC21520: '
                            '100 V/ns)'))
    checks.append(dict(name='SPICE: excursion de Vgs del pasivo',
                       value=d20[5], limit=6.6, ok=d20[5] < 6.6, unit='V',
                       note='margen hasta Vth=2.6 V desde el bias de -4 V; '
                            'el Miller clamp lo sujeta'))
    d150 = [r for r in tabla if r[0] == 150.0][0]
    checks.append(dict(name='SPICE: penalizacion de un lazo malo (150 nH)',
                       value=d150[2], limit=1200.0, ok=d150[2] < 1200.0,
                       unit='V',
                       note='demuestra por que el lazo debe ir apretado'))
    return checks, tabla


# =====================================================================
# B) FILTRO LCL: BARRIDO AC (contraste con el modelo analitico)
# =====================================================================
def sim_lcl_ac():
    net = f"""* Filtro LCL - barrido AC - corriente de red / tension de convertidor
Vconv conv 0 AC 1
L1    conv mid {P.L1}
Rl1   mid  midr 0.025
Cf    midr cfa {P.CF}
Rd    cfa  0 {P.RD}
L2    midr out {P.L2}
Rl2   out  0 0.025
.ac dec 400 10 200k
.backanno
.end
"""
    p = write('lcl_ac.net', net)
    d = run_lt(p)
    f = np.abs(np.real(d['frequency']))
    ig = d['I(Rl2)']                       # corriente que entra en la red
    mag_spice = 20 * np.log10(np.abs(ig))

    sys.path.insert(0, os.path.join(ROOT, 'sim'))
    import sim_design as D
    w = 2 * np.pi * f
    mag_ana = 20 * np.log10(np.abs(D.lcl_tf(w, P.L1, P.L2, P.CF, P.RD)))

    err = float(np.max(np.abs(mag_spice - mag_ana)[
        (f > 50) & (f < 5 * P.F_SW)]))

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.semilogx(f, mag_ana, lw=2.4, color='#1f6feb', alpha=0.55,
                label='Modelo analitico (sim_design.py)')
    ax.semilogx(f, mag_spice, lw=1.2, ls='--', color='#c0392b',
                label='SPICE (LTspice)')
    ax.axvline(2431, color='#e67e22', lw=1.0)
    ax.axvline(P.F_SW, color='#2c3e50', lw=1.0, ls=':')
    ax.set_xlabel('Frecuencia [Hz]'); ax.set_ylabel('$|I_{red}/V_{conv}|$ [dB]')
    ax.set_title('Validacion cruzada del filtro LCL: '
                 'discrepancia maxima %.2f dB' % err)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '07_spice_lcl.png'), dpi=130)
    plt.close(fig)

    return [dict(name='SPICE vs analitico: discrepancia del LCL', value=err,
                 limit=1.0, ok=err < 1.0, unit='dB',
                 note='dos modelos independientes deben coincidir')]


# =====================================================================
# C) PRECARGA
# =====================================================================
def sim_precharge():
    net = f"""* Precarga del bus DC a traves de la resistencia de soft-start
Vac  ac 0 PULSE(0 {P.V_PK_RECT} 1m 10u 10u 10 20)
Rpc  ac dcp {P.R_PC}
Cbus dcp 0 {P.C_BUS}
Rbld dcp 0 100k
.tran 0.2m 500m uic
.backanno
.end
"""
    p = write('precarga.net', net)
    d = run_lt(p)
    t = (np.real(d['time']) - 1e-3) * 1e3
    v = np.real(d.get('V(dcp)', d.get('V(DCP)')))
    i = (np.real(d.get('V(ac)', d.get('V(AC)'))) - v) / P.R_PC
    m = t >= 0
    ipk = float(np.max(i[m]))

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    ax[0].plot(t[m], v[m], lw=1.8, color='#1f6feb')
    ax[0].axhline(0.9 * P.V_PK_RECT, ls='--', lw=1.0, color='#16a34a')
    ax[0].set_xlabel('t [ms]'); ax[0].set_ylabel('$V_{dc}$ [V]')
    ax[0].set_title('Precarga (SPICE)')
    ax[1].plot(t[m], i[m], lw=1.8, color='#c0392b')
    ax[1].axhline(P.I_INRUSH_MAX, ls='--', lw=1.0, color='#7f8c8d')
    ax[1].set_xlabel('t [ms]'); ax[1].set_ylabel('$I$ [A]')
    ax[1].set_title('Inrush: pico %.2f A' % ipk)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, '08_spice_precarga.png'), dpi=130)
    plt.close(fig)

    return [dict(name='SPICE: inrush de precarga', value=ipk,
                 limit=P.I_INRUSH_MAX, ok=ipk < P.I_INRUSH_MAX, unit='A',
                 note='coincide con el calculo Vpk/Rpc')]


def main():
    print('LTspice:', LTSPICE)
    todos = []
    print('[A] Medio puente SiC con parasitas de layout ...')
    c, tabla = sim_halfbridge()
    todos += c
    print('    L_lazo   V_pico   sobretension   dv/dt      Vgs_max')
    for lnh, lbl, vpk, over, dvdt, vgsp, vgsm in tabla:
        print('    %5.0f nH  %6.0f V  %+8.0f V   %5.1f V/ns  %+6.2f V   %s'
              % (lnh, vpk, over, dvdt, vgsp, lbl))
    print('[B] Filtro LCL: barrido AC ...')
    todos += sim_lcl_ac()
    print('[C] Precarga ...')
    todos += sim_precharge()

    print()
    for c in todos:
        print('  [%-5s] %-46s %10.3f %s'
              % ('OK' if c['ok'] else 'FALLA', c['name'], c['value'],
                 c['unit']))
    n_ok = sum(1 for c in todos if c['ok'])
    print('\n%d/%d OK' % (n_ok, len(todos)))
    return todos


if __name__ == '__main__':
    main()
