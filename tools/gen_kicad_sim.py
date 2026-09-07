"""
gen_kicad_sim.py - Genera esquemas SIMULABLES dentro de KiCad (ngspice).

Salida en kicad/sim/:
  lcl_ac.kicad_sch      barrido AC del filtro LCL
  halfbridge.kicad_sch  doble pulso del medio puente SiC con parasitas
  fw_bridge.kicad_sch   *** puente trifasico gobernado por el PWM QUE CALCULA
                        EL FIRMWARE REAL *** (fw/verify/control_ref.py)
  sic.lib               modelo VDMOS del SiC

Se abren en KiCad y se simulan con  Inspeccionar > Simulador.
El comando de analisis va como texto en la propia hoja (formato KiCad 9).

    python tools/gen_kicad_sim.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'sim'))
sys.path.insert(0, os.path.join(ROOT, 'fw', 'verify'))

from kisch import SymbolCache, Schematic       # noqa: E402
import b2b_params as P                         # noqa: E402
import control_ref as CR                       # noqa: E402

SYMDIR = r'C:\Program Files\KiCad\9.0\share\kicad\symbols'
OUT = os.path.join(ROOT, 'kicad', 'sim')
os.makedirs(OUT, exist_ok=True)
lib = SymbolCache(SYMDIR)

PROJ = 'b2b_sim'
ROOT_UUID = 'b2b51a00-0000-4000-8000-000000000000'

S_R, S_C, S_L = 'Device:R', 'Device:C', 'Device:L'
S_VDC = 'Simulation_SPICE:VDC'
S_VPWL = 'Simulation_SPICE:VPWL'
S_VSIN = 'Simulation_SPICE:VSIN'
S_NMOS = 'Simulation_SPICE:NMOS'

SIC_LIB = """* Modelo VDMOS aproximado a un SiC 1200 V / 75 mOhm (TO-247-4).
* No es el modelo del fabricante: sirve para evaluar el efecto de las
* parasitas de layout y la forma de onda de conmutacion.
.model SiC1200 VDMOS(Rg=4 Vto=2.6 Kp=22 Lambda=0.002 Cgdmax=1.8n Cgdmin=8p
+ Cgs=1.1n Cjo=0.9n Is=3e-14 Rd=48m Rs=12m Rb=1m
+ Vds=1200 Ron=75m Qg=51n mfg=Wolfspeed)
"""


def simf(dev, typ, pins, params=None, libname=None, model=None):
    """Construye el dict de propiedades Sim.* de KiCad."""
    d = {'Sim.Device': dev, 'Sim.Type': typ, 'Sim.Pins': pins}
    if params:
        d['Sim.Params'] = params
    if libname:
        d['Sim.Library'] = libname
    if model:
        d['Sim.Name'] = model
    return d


def vdc(sch, ref, volts, x, y, rot=0):
    return sch.place(S_VDC, ref, str(volts), x, y, rot,
                     fields=simf('V', 'DC', '1=+ 2=-'))


def vac(sch, ref, x, y, rot=0, dc=0, ac=1):
    """Fuente para barrido .ac. Un VDC normal sale como 'DC 1' y su
    amplitud AC es CERO: el barrido daria corriente nula en todo el rango."""
    return sch.place(S_VDC, ref, 'AC %g' % ac, x, y, rot,
                     fields={'Sim.Device': 'SPICE',
                             'Sim.Pins': '1=1 2=2',
                             'Sim.Params': 'type="V" model="DC %g AC %g" '
                                           'lib=""' % (dc, ac)})


def nmos(sch, ref, x, y, rot=0):
    return sch.place(S_NMOS, ref, 'SiC1200', x, y, rot,
                     fields=simf('NMOS', 'VDMOS', '1=D 2=G 3=S',
                                 libname='sic.lib', model='SiC1200'))


def vpwl(sch, ref, pts, x, y, rot=0):
    s = ' '.join('%.10g %.6g' % (t, v) for t, v in pts)
    return sch.place(S_VPWL, ref, 'PWL', x, y, rot,
                     fields=simf('V', 'PWL', '1=+ 2=-', params='pwl="%s"' % s))


# =====================================================================
# 1) LCL: barrido AC
# =====================================================================
def sheet_lcl():
    sch = Schematic('SIM - Filtro LCL (barrido AC)', lib, PROJ, ROOT_UUID,
                    None, paper='A3',
                    comments=('Contraste con sim/sim_design.py y LTspice',))
    sch.text('SIMULACION DEL FILTRO LCL EN KICAD (ngspice)\n\n'
             'Abrir con  Inspeccionar > Simulador  y pulsar Ejecutar.\n'
             'Representar  I(RL2)  para ver la corriente que entra en la red.\n'
             'La resonancia debe salir en 2431 Hz y el pico amortiguado en '
             '19 dB.', (20, 15), size=2.0)

    y = 70
    v = vac(sch, 'V1', 40, y + 12, 0, dc=0, ac=1)
    sch.wire(v.pin('1'), (40, y))
    sch.label('conv', (40, y), 0)
    sch.power('GND', v.pin('2'))

    l1, a1, b1 = (sch.place(S_L, 'L1', '%.6g' % P.L1, 70, y, 90),), None, None
    l1 = l1[0]
    sch.wire((40, y), l1.pin('1'))
    r1 = sch.place(S_R, 'RL1', '0.025', 100, y, 90)
    sch.wire(l1.pin('2'), r1.pin('1'))
    sch.wire(r1.pin('2'), (130, y))
    sch.label('mid', (130, y), 0)
    sch.junction((130, y))

    # rama de amortiguamiento Cf + Rd
    cf = sch.place(S_C, 'CF', '%.6g' % P.CF, 130, y + 20, 0)
    sch.wire((130, y), cf.pin('1'))
    rd = sch.place(S_R, 'RD', '%.6g' % P.RD, 130, y + 40, 0)
    sch.wire(cf.pin('2'), rd.pin('1'))
    sch.power('GND', rd.pin('2'))

    l2 = sch.place(S_L, 'L2', '%.6g' % P.L2, 160, y, 90)
    sch.wire((130, y), l2.pin('1'))
    r2 = sch.place(S_R, 'RL2', '0.025', 190, y, 90)
    sch.wire(l2.pin('2'), r2.pin('1'))
    sch.wire(r2.pin('2'), (215, y))
    sch.label('red', (215, y), 0)
    sch.power('GND', (215, y))

    sch.text('.ac dec 400 10 200k', (40, 150), size=2.2)
    sch.text('* Rd = %.1f ohm  (valor optimizado por simulacion:\n'
             '* con 2.2 ohm el pico de resonancia era de 26 dB)' % P.RD,
             (40, 158), size=1.8)
    return sch


# =====================================================================
# 2) Medio puente SiC: doble pulso
# =====================================================================
def sheet_halfbridge(l_loop_nh=20.0):
    sch = Schematic('SIM - Medio puente SiC (doble pulso)', lib, PROJ,
                    ROOT_UUID, None, paper='A3',
                    comments=('Parasita de lazo %g nH' % l_loop_nh,))
    sch.text('DOBLE PULSO DEL MEDIO PUENTE SiC\n\n'
             'Representar  V(sw)  para ver la sobretension de conmutacion.\n'
             'Con %g nH de lazo el pico debe rondar los 820 V sobre un bus\n'
             'de 700 V. Cambia el valor de LP/LN para ver como empeora:\n'
             '  5 nH -> 753 V   20 nH -> 823 V   60 nH -> 929 V   '
             '150 nH -> 1136 V (limite del dispositivo)' % l_loop_nh,
             (20, 15), size=2.0)

    ytop, ybot = 80, 160
    v = vdc(sch, 'VBUS', P.V_DC, 40, 120, 0)
    sch.wire(v.pin('1'), (40, ytop))
    sch.label('dcpc', (40, ytop), 0)
    sch.power('GND', v.pin('2'))

    cd = sch.place(S_C, 'CDEC', '2u', 65, 120, 0)
    sch.wire((40, ytop), (65, ytop))
    sch.wire((65, ytop), cd.pin('1'))
    sch.junction((65, ytop))
    sch.power('GND', cd.pin('2'))

    lp = sch.place(S_L, 'LP', '%gn' % (l_loop_nh / 2), 100, ytop, 90)
    sch.wire((65, ytop), lp.pin('1'))
    sch.wire(lp.pin('2'), (130, ytop))
    sch.label('dcp', (130, ytop), 0)

    qh = nmos(sch, 'QH', 150, ytop + 20, 0)
    sch.wire((130, ytop), qh.pin('1'))
    sch.wire(qh.pin('3'), (150, 120))
    sch.label('sw', (150, 120), 0)
    sch.junction((150, 120))
    vgh = vdc(sch, 'VGH', -4, 120, ytop + 20, 0)
    sch.wire(vgh.pin('1'), qh.pin('2'))
    sch.wire(vgh.pin('2'), (120, 120))
    sch.wire((120, 120), (150, 120))

    ql = nmos(sch, 'QL', 150, 145, 0)
    sch.wire((150, 120), ql.pin('1'))
    sch.wire(ql.pin('3'), (150, ybot))
    sch.label('dcn', (150, ybot), 0)

    # driver: doble pulso
    ts = 1.0 / P.F_SW
    pts = [(0, -4), (100e-9, -4), (115e-9, 15), (3e-6, 15),
           (3.015e-6, -4), (4e-6, -4), (4.015e-6, 15), (4.6e-6, 15),
           (4.615e-6, -4), (8e-6, -4)]
    vg = vpwl(sch, 'VDRV', pts, 100, 145, 0)
    rg = sch.place(S_R, 'RG', '10', 125, 145, 90)
    sch.wire(vg.pin('1'), rg.pin('1'))
    sch.wire(rg.pin('2'), ql.pin('2'))
    sch.wire(vg.pin('2'), (100, ybot))
    sch.wire((100, ybot), (150, ybot))

    ln = sch.place(S_L, 'LN', '%gn' % (l_loop_nh / 2), 185, ybot, 90)
    sch.wire((150, ybot), ln.pin('1'))
    sch.power('GND', ln.pin('2'))

    lload = sch.place(S_L, 'LLOAD', '70u', 200, 100, 0)
    sch.wire((65, ytop), (200, ytop))
    sch.wire((200, ytop), lload.pin('1'))
    sch.wire(lload.pin('2'), (200, 120))
    sch.wire((200, 120), (150, 120))

    sch.text('.tran 0.02n 5.2u 0 0.2n uic', (40, 190), size=2.2)
    sch.text('* La parasita del lazo (LP + LN) va DENTRO del lazo de\n'
             '* conmutacion: cap -> QH -> QL -> vuelta. Fuera de el no\n'
             '* produce sobretension.', (40, 198), size=1.8)
    return sch


# =====================================================================
# 3) PUENTE TRIFASICO GOBERNADO POR EL FIRMWARE REAL
# =====================================================================
def sheet_fw_bridge(n_periods=3):
    """Ejecuta el control REAL (control_ref.py, transliteracion del C) y
    convierte sus ciclos de trabajo en fuentes PWL que gobiernan el puente."""
    foc = CR.FOC()
    ts = 1.0 / CR.C('B2B_F_SW_REAL_HZ')
    dt_gate = CR.C('B2B_DEADTIME_NS') * 1e-9

    # punto de operacion: motor girando en regimen, con carga
    w_mech = 250.0
    theta_e = 0.6
    isd, isq = 0.0, 25.0
    vdc_op = CR.C('B2B_VDC_REF')
    gates = [[], [], []]          # por fase: (hi_pts, lo_pts)
    duties_log = []

    for k in range(n_periods):
        t0 = k * ts
        d = foc.step(theta_e, w_mech, isd, isq, vdc_op, w_mech, 4000.0, ts)
        duties_log.append(d)
        g = CR.duties_to_gates(d, t0, ts, dt_gate)
        for ph in range(3):
            gates[ph].append(g[ph])
        theta_e = (theta_e + CR.C('B2B_POLE_PAIRS') * w_mech * ts) % (2 * math.pi)

    # concatenar los tramos PWL de cada puerta
    def cat(idx, hilo):
        pts = []
        for per in gates[idx]:
            seg = per[hilo]
            for (t, v) in seg:
                if pts and abs(t - pts[-1][0]) < 1e-12:
                    continue
                pts.append((t, v * 15.0 - 4.0))   # 0/1 -> -4 V / +15 V
        return pts

    sch = Schematic('SIM - Puente trifasico con el PWM DEL FIRMWARE', lib,
                    PROJ, ROOT_UUID, None, paper='A3',
                    comments=('PWM generado por fw/verify/control_ref.py',
                              'transliteracion literal de b2b_control.h'))
    sch.text(
        'PUENTE TRIFASICO GOBERNADO POR EL FIRMWARE\n\n'
        'Las 6 fuentes VPWL NO son formas de onda inventadas: son los flancos\n'
        'de puerta que produce el codigo de control real (SVPWM por inyeccion\n'
        'de secuencia cero + el tiempo muerto de %.0f ns del TIM1).\n'
        'Ciclos de trabajo calculados por el firmware en estos %d periodos:\n'
        '%s\n\n'
        'Representar  V(u) V(v) V(w)  o las corrientes I(LU) I(LV) I(LW).\n'
        'KiCad no puede EJECUTAR firmware (no tiene modelo de nucleo ARM):\n'
        'lo que se hace aqui es inyectar su salida real en el circuito.'
        % (dt_gate * 1e9, n_periods,
           '  '.join('(%.3f %.3f %.3f)' % d for d in duties_log[:3])),
        (20, 12), size=1.9)

    ytop, ybot = 95, 175
    v = vdc(sch, 'VBUS', P.V_DC, 30, 135, 0)
    sch.wire(v.pin('1'), (30, ytop))
    sch.label('dcp', (30, ytop), 0)
    sch.power('GND', v.pin('2'))
    sch.wire((30, ytop), (250, ytop))

    names = ['u', 'v', 'w']
    for i, nm in enumerate(names):
        x = 70 + i * 60
        qh = nmos(sch, 'Q%dH' % (i + 1), x, ytop + 20, 0)
        ql = nmos(sch, 'Q%dL' % (i + 1), x, ybot - 20, 0)
        sch.wire((x, ytop), qh.pin('1'))
        sch.junction((x, ytop))
        sch.wire(qh.pin('3'), (x, 135))
        sch.wire(ql.pin('1'), (x, 135))
        sch.junction((x, 135))
        sch.wire(ql.pin('3'), (x, ybot))
        sch.junction((x, ybot))
        sch.label(nm, (x, 135), 0)
        # fuentes de puerta con la salida real del firmware
        gh = vpwl(sch, 'VG%dH' % (i + 1), cat(i, 0), x - 26, ytop + 20, 0)
        sch.wire(gh.pin('1'), qh.pin('2'))
        sch.wire(gh.pin('2'), (x - 26, 135))
        sch.wire((x - 26, 135), (x, 135))
        gl = vpwl(sch, 'VG%dL' % (i + 1), cat(i, 1), x - 26, ybot - 20, 0)
        sch.wire(gl.pin('1'), ql.pin('2'))
        sch.wire(gl.pin('2'), (x - 26, ybot))
        sch.wire((x - 26, ybot), (x, ybot))
    sch.wire((30, ybot), (250, ybot))
    sch.label('dcn', (250, ybot), 0)
    sch.power('GND', (250, ybot))

    # carga: motor como R-L en estrella
    for i, nm in enumerate(names):
        x = 70 + i * 60
        ll = sch.place(S_L, 'L%s' % nm.upper(), '%.6g' % P.LQ, x, 205, 0)
        sch.wire((x, 135), (x, 195))
        sch.wire((x, 195), ll.pin('1'))
        rr = sch.place(S_R, 'R%s' % nm.upper(), '%.6g' % P.RS, x, 225, 0)
        sch.wire(ll.pin('2'), rr.pin('1'))
        sch.wire(rr.pin('2'), (x, 240))
        sch.label('neutro', (x, 240), 0)
    sch.text('* carga: modelo R-L del estator en estrella', (70, 248),
             size=1.8)

    sch.text('.tran 100n %.7g 0 100n uic' % (n_periods * ts), (30, 262),
             size=2.2)
    # Sin .save, LTspice guarda TODOS los nodos en cada paso adaptativo y el
    # .raw se va a >100 MB: con 6 SiC conmutando refina hasta el femtosegundo.
    sch.text('.save V(u) V(v) V(w) I(LU) I(LV) I(LW)', (30, 270), size=2.2)
    return sch


def main():
    with open(os.path.join(OUT, 'sic.lib'), 'w') as f:
        f.write(SIC_LIB)
    hojas = [('lcl_ac', sheet_lcl()),
             ('halfbridge', sheet_halfbridge()),
             ('fw_bridge', sheet_fw_bridge())]
    for name, sch in hojas:
        p = os.path.join(OUT, name + '.kicad_sch')
        sch.save(p)
        n = len([x for x in sch.placed if not getattr(x, 'is_power', False)])
        print('  %-14s %2d componentes -> %s'
              % (name, n, os.path.relpath(p, ROOT)))
    # un .kicad_pro minimo por hoja para que KiCad las abra como proyecto
    for name, _ in hojas:
        pro = os.path.join(OUT, name + '.kicad_pro')
        if not os.path.exists(pro):
            with open(pro, 'w') as f:
                f.write('{"board":{},"boards":[],"cvpcb":{},"libraries":{},'
                        '"meta":{"filename":"%s.kicad_pro","version":3},'
                        '"net_settings":{},"pcbnew":{},"schematic":{},'
                        '"sheets":[],"text_variables":{}}\n' % name)
    print('sic.lib escrito en kicad/sim/')


if __name__ == '__main__':
    main()
