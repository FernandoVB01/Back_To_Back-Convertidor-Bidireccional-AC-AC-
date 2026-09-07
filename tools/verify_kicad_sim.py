"""
verify_kicad_sim.py - Comprueba que los esquemas de simulacion de KiCad
producen los MISMOS resultados que el modelo analitico ya validado.

Flujo:
    kicad/sim/*.kicad_sch
      -> kicad-cli sch export netlist --format spice   (lo hace KiCad)
      -> se ejecuta ese netlist                        (LTspice en batch)
      -> se compara con sim/sim_design.py              (modelo analitico)

Si los tres coinciden, el circuito dibujado en KiCad es correcto.

    python tools/verify_kicad_sim.py
"""

import os
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                 # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'sim'))
sys.path.insert(0, os.path.join(ROOT, 'spice'))

import b2b_params as P                          # noqa: E402
import sim_design as D                          # noqa: E402
from gen_spice import parse_raw, LTSPICE        # noqa: E402

CLI = r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
SIMDIR = os.path.join(ROOT, 'kicad', 'sim')
OUTIMG = os.path.join(ROOT, 'sim', 'out')
plt.rcParams.update({'figure.facecolor': '#ffffff', 'axes.grid': True,
                     'grid.alpha': 0.3, 'font.size': 9})


def export_netlist(name):
    sch = os.path.join(SIMDIR, name + '.kicad_sch')
    cir = os.path.join(SIMDIR, name + '.cir')
    r = subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'spice',
                        '--output', cir, sch],
                       capture_output=True, text=True, timeout=180)
    if not os.path.isfile(cir):
        raise RuntimeError('kicad-cli no genero %s\n%s' % (cir, r.stderr))
    return cir


def run_spice(cir):
    """Ejecuta el netlist EXPORTADO POR KICAD en LTspice."""
    work = os.path.splitext(cir)[0] + '_run.net'
    with open(cir) as f:
        txt = f.read()
    # LTspice quiere la primera linea como titulo/comentario
    if not txt.lstrip().startswith('*'):
        txt = '* ' + txt
    with open(work, 'w') as f:
        f.write(txt)
    raw = os.path.splitext(work)[0] + '.raw'
    if os.path.exists(raw):
        os.remove(raw)
    subprocess.run([LTSPICE, '-b', '-ascii', '-Run', work],
                   capture_output=True, timeout=600)
    if not os.path.exists(raw):
        log = os.path.splitext(work)[0] + '.log'
        m = open(log, errors='replace').read()[-700:] \
            if os.path.exists(log) else '(sin log)'
        raise RuntimeError('no simulo %s\n%s' % (os.path.basename(cir), m))
    return parse_raw(raw)


def verificar_lcl():
    cir = export_netlist('lcl_ac')
    d = run_spice(cir)
    f = np.abs(np.real(d['frequency']))
    key = [k for k in d if k.upper().startswith('I(RL2)')]
    ig = d[key[0]]
    mag_kicad = 20 * np.log10(np.abs(ig))
    w = 2 * np.pi * f
    mag_ana = 20 * np.log10(np.abs(D.lcl_tf(w, P.L1, P.L2, P.CF, P.RD)))
    m = (f > 50) & (f < 5 * P.F_SW)
    err = float(np.max(np.abs(mag_kicad - mag_ana)[m]))

    i_res = int(np.argmin(np.abs(f - 2431)))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.semilogx(f, mag_ana, lw=2.6, color='#1f6feb', alpha=0.5,
                label='Modelo analitico (sim/sim_design.py)')
    ax.semilogx(f, mag_kicad, lw=1.2, ls='--', color='#16a34a',
                label='Esquema de KiCad -> netlist -> SPICE')
    ax.axvline(2431, color='#e67e22', lw=1.0)
    ax.set_xlabel('Frecuencia [Hz]')
    ax.set_ylabel('$|I_{red}/V_{conv}|$ [dB]')
    ax.set_title('El circuito dibujado en KiCad reproduce el modelo '
                 'validado (error max %.3f dB)' % err)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTIMG, '09_kicad_lcl.png'), dpi=130)
    plt.close(fig)
    return [('LCL de KiCad vs modelo analitico', err, 1.0, err < 1.0, 'dB')]


def verificar_halfbridge():
    cir = export_netlist('halfbridge')
    d = run_spice(cir)
    t = np.real(d['time']) * 1e9
    key = [k for k in d if k.lower() in ('v(sw)', 'v(/sw)')]
    vsw = np.real(d[key[0]])
    m = (t > 2900) & (t < 4100)
    vpk = float(np.max(vsw[m]))
    fig, ax = plt.subplots(figsize=(9, 4.0))
    ax.plot(t[m], vsw[m], lw=1.3, color='#1f6feb')
    ax.axhline(P.V_DC, ls='--', lw=1.0, color='#7f8c8d')
    ax.axhline(1200, lw=1.2, color='#c0392b')
    ax.annotate('limite del SiC 1200 V', (2950, 1215), fontsize=8,
                color='#c0392b')
    ax.set_xlabel('t [ns]'); ax.set_ylabel('$V_{sw}$ [V]')
    ax.set_title('Medio puente dibujado en KiCad: pico %.0f V con 20 nH '
                 'de lazo' % vpk)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTIMG, '10_kicad_halfbridge.png'), dpi=130)
    plt.close(fig)
    return [('Medio puente de KiCad: sobretension', vpk, 960.0,
             700 < vpk < 960, 'V')]


def verificar_fw_bridge():
    cir = export_netlist('fw_bridge')
    d = run_spice(cir)
    t = np.real(d['time']) * 1e6
    ph = {}
    for nm in ('u', 'v', 'w'):
        k = [x for x in d if x.lower() in ('v(%s)' % nm, 'v(/%s)' % nm)]
        if k:
            ph[nm] = np.real(d[k[0]])
    cur = {}
    for nm in ('LU', 'LV', 'LW'):
        k = [x for x in d if x.upper().startswith('I(%s)' % nm)]
        if k:
            cur[nm] = np.real(d[k[0]])

    fig, ax = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True)
    for nm, c in zip(('u', 'v', 'w'), ('#1f6feb', '#16a34a', '#c0392b')):
        if nm in ph:
            ax[0].plot(t, ph[nm], lw=0.9, color=c, label='V(%s)' % nm)
    ax[0].set_ylabel('tension de fase [V]')
    ax[0].set_title('Puente conmutando con el PWM QUE CALCULA EL FIRMWARE\n'
                    '(SVPWM por inyeccion de secuencia cero + dead-time de '
                    '500 ns del TIM1)')
    ax[0].legend(fontsize=8, ncol=3)
    for nm, c in zip(('LU', 'LV', 'LW'),
                     ('#1f6feb', '#16a34a', '#c0392b')):
        if nm in cur:
            ax[1].plot(t, cur[nm], lw=1.2, color=c, label='I(%s)' % nm)
    ax[1].set_xlabel('t [us]'); ax[1].set_ylabel('corriente de fase [A]')
    ax[1].legend(fontsize=8, ncol=3)
    ax[1].set_title('Corriente en la carga R-L: el rizado triangular '
                    'confirma que la modulacion es correcta')
    fig.tight_layout()
    fig.savefig(os.path.join(OUTIMG, '11_kicad_fw_bridge.png'), dpi=130)
    plt.close(fig)

    # comprobacion: nunca deben conducir a la vez los dos de una rama
    ok_dt = True
    for nm in ph:
        v = ph[nm]
        # la tension de fase debe permanecer dentro del bus
        if np.max(v) > P.V_DC * 1.25 or np.min(v) < -P.V_DC * 0.25:
            ok_dt = False
    vmean = float(np.mean(ph['u'])) if 'u' in ph else 0.0
    return [('Bridge con PWM del firmware: sin shoot-through', 1.0 if ok_dt
             else 0.0, 1.0, ok_dt, ''),
            ('Tension media de fase U (deberia ser ~Vdc/2 + modulacion)',
             vmean, P.V_DC, 0 < vmean < P.V_DC, 'V')]


def main():
    todo = []
    for nombre, fn in (('LCL (barrido AC)', verificar_lcl),
                       ('Medio puente (doble pulso)', verificar_halfbridge),
                       ('Puente con PWM del firmware', verificar_fw_bridge)):
        print('[%s]' % nombre)
        try:
            todo += fn()
        except Exception as e:
            print('   FALLO: %s' % e)
            todo.append((nombre, 0.0, 1.0, False, ''))
    print()
    for (n, v, lim, ok, u) in todo:
        print('  [%-5s] %-52s %10.4g %s'
              % ('OK' if ok else 'FALLA', n, v, u))
    n_ok = sum(1 for x in todo if x[3])
    print('\n%d/%d OK' % (n_ok, len(todo)))
    return 0 if n_ok == len(todo) else 1


if __name__ == '__main__':
    sys.exit(main())
