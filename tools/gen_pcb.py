"""
gen_pcb.py - Construye la PCB del convertidor back-to-back con la API pcbnew.

Entrada : netlist exportada del esquematico (kicad-cli sch export netlist)
Salida  : kicad/b2b_converter.kicad_pcb

Coloca cada componente en la region del floorplan que le corresponde segun su
hoja de origen, respetando la separacion ZONA HV / BARRERA / ZONA LV.

Ejecutar con el Python de KiCad:
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/gen_pcb.py
"""

import os
import sys
import functools
print = functools.partial(print, flush=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pcbnew                                         # noqa: E402
from kisch import parse, _find, _findall, Sym         # noqa: E402

ROOT_DIR = os.path.dirname(HERE)
KIDIR = r'C:\Program Files\KiCad\9.0\share\kicad'
FPDIR = os.path.join(KIDIR, 'footprints')
NETLIST = os.path.join(ROOT_DIR, 'kicad', 'b2b_converter.net')
OUTPCB = os.path.join(ROOT_DIR, 'kicad', 'b2b_converter.kicad_pcb')

# ---------------------------------------------------------------- geometria
BW, BH = 340.0, 240.0          # placa 340 x 240 mm
MARGIN = 8.0

# Regiones del floorplan: hoja -> (x0, y0, x1, y1)  en mm
# ZONA HV arriba (y 10..126) | BARRERA (y 126..146) | ZONA LV abajo (y 146..222)
BARRIER_Y0, BARRIER_Y1 = 145.0, 151.0   # franja sin cobre (6 mm)
BARRIER_MID = 148.0                     # los drivers se centran aqui

REGIONS = {
    '01_AC_Input_LCL':     (8,   12,  86, 134),
    '02_AFE_Bridge':       (90,  62, 150, 134),
    '03_DClink_Precharge': (152, 12, 232, 134),
    '04_Inverter_Bridge':  (236, 62, 332, 134),
    '05_Gate_Drivers':     (90, 138, 332, 168),      # a caballo de la barrera
    '09_PSU_Aux_Bias':     (8,  160,  84, 232),
    '06_Sense_I_V':        (88, 160, 170, 232),
    '07_MCU_STM32':        (174, 160, 236, 206),
    '08_Protection_IO':    (174, 208, 262, 232),
    '10_Isolation_Comms':  (240, 160, 268, 186),     # barrera funcional
    '11_ESP32_IoT':        (274, 160, 332, 232),
}
DEFAULT_REGION = (8, 160, 332, 232)

# Colocacion EXPLICITA de la etapa de potencia (el flujo automatico no sirve
# aqui: la posicion de estos componentes ES el diseno).
# Los 12 SiC van en dos filas alineadas al borde del disipador.
EXPLICIT = {}
for _i in range(6):                       # AFE: Q1..Q6  (3 ramas x 2)
    EXPLICIT['Q%d' % (_i + 1)] = (98 + (_i // 2) * 18, 26 + (_i % 2) * 24, 0)
for _i in range(6):                       # Inversor: Q7..Q12
    EXPLICIT['Q%d' % (_i + 7)] = (244 + (_i // 2) * 18, 26 + (_i % 2) * 24, 0)
EXPLICIT['QBRK'] = (300, 26, 0)
for _i in range(4):                       # banco DC-link 2x2
    EXPLICIT['C%d' % (_i + 1)] = (172 + (_i % 2) * 38, 34 + (_i // 2) * 40, 0)
EXPLICIT['J1'] = (16, 20, 270)            # entrada de red
EXPLICIT['J4'] = (326, 118, 90)           # salida a motor
EXPLICIT['J3'] = (200, 120, 0)            # resistencia de frenado
EXPLICIT['RPC'] = (196, 96, 90)           # precarga
EXPLICIT['K2'] = (196, 108, 90)
# Drivers U11..U16 a caballo de la barrera.
# rot=90 es OBLIGATORIO: el UCC21520DW lleva la logica en los pines 1-8 y la
# potencia en 9-16, o sea la barrera del encapsulado va ENTRE SUS DOS FILAS.
# Con rot=0 la logica queda del lado HV y PWM_* tendria que cruzar el
# aislamiento para llegar al STM32.
for _i in range(6):
    EXPLICIT['U%d' % (_i + 11)] = (104 + _i * 38, 148.0, 90)


def mm(v):
    return pcbnew.FromMM(float(v))


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


# ---------------------------------------------------------------- netlist
def read_netlist(path):
    with open(path, encoding='utf-8') as f:
        d = parse(f.read())
    comps = []
    design = _find(d, Sym('components'))
    for c in _findall(design, Sym('comp')):
        ref = _find(c, Sym('ref'))[1]
        val = _find(c, Sym('value'))
        fp = _find(c, Sym('footprint'))
        sp = _find(c, Sym('sheetpath'))
        sheet = ''
        if sp is not None:
            nm = _find(sp, Sym('names'))
            if nm is not None:
                sheet = str(nm[1]).strip('/')
        comps.append({
            'ref': ref,
            'value': str(val[1]) if val is not None else '',
            'fp': str(fp[1]) if fp is not None else '',
            'sheet': sheet,
        })
    nets = []
    nb = _find(d, Sym('nets'))
    for n in _findall(nb, Sym('net')):
        name = _find(n, Sym('name'))[1]
        nodes = []
        for nd in _findall(n, Sym('node')):
            nodes.append((_find(nd, Sym('ref'))[1],
                          str(_find(nd, Sym('pin'))[1])))
        nets.append((str(name), nodes))
    return comps, nets


# ---------------------------------------------------------------- footprints
_IO = None


def load_fp(board, fpid):
    global _IO
    if _IO is None:
        _IO = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    libname, name = fpid.split(':', 1)
    libpath = os.path.join(FPDIR, libname + '.pretty')
    fp = _IO.FootprintLoad(libpath, name)
    if fp is None:
        return None
    fp.SetParent(board)
    return fp


# ---------------------------------------------------------------- placement
def place_region(board, fps, region, gap=4.0):
    """Coloca una lista de FOOTPRINT en flujo dentro de la region."""
    x0, y0, x1, y1 = region
    cx, cy, rowh = x0, y0, 0.0
    for fp in fps:
        bb = fp.GetBoundingBox()
        w = pcbnew.ToMM(bb.GetWidth())
        h = pcbnew.ToMM(bb.GetHeight())
        w = max(w, 1.0)
        h = max(h, 1.0)
        if cx + w > x1 and cx > x0:
            cx = x0
            cy += rowh + gap
            rowh = 0.0
        fp.SetPosition(vec(cx + w / 2.0, cy + h / 2.0))
        cx += w + gap
        rowh = max(rowh, h)
    return cy + rowh


def main():
    if not os.path.isfile(NETLIST):
        print('ERROR: falta la netlist. Genera primero con:')
        print('  kicad-cli sch export netlist --output kicad/b2b_converter.net'
              ' kicad/b2b_converter.kicad_sch')
        return 1

    comps, nets = read_netlist(NETLIST)
    print('netlist: %d componentes, %d redes' % (len(comps), len(nets)))

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)

    # --- reglas basicas de diseno ---
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(4)

    # --- footprints ---
    added = {}
    missing = []
    for c in comps:
        if not c['fp']:
            missing.append((c['ref'], '(sin footprint)'))
            continue
        fp = load_fp(board, c['fp'])
        if fp is None:
            missing.append((c['ref'], c['fp']))
            continue
        fp.SetReference(c['ref'])
        fp.SetValue(c['value'])
        fp.Value().SetVisible(False)
        board.Add(fp)
        added[c['ref']] = fp
    print('footprints colocados: %d   fallidos: %d' % (len(added),
                                                       len(missing)))
    for r, f in missing[:10]:
        print('   FALTA %-8s %s' % (r, f))

    # --- colocacion por region de floorplan ---
    for ref, (px, py, rot) in EXPLICIT.items():
        fp = added.get(ref)
        if fp is None:
            continue
        fp.SetPosition(vec(px, py))
        if rot:
            fp.SetOrientationDegrees(rot)
    bysheet = {}
    for c in comps:
        if c['ref'] in added and c['ref'] not in EXPLICIT:
            bysheet.setdefault(c['sheet'], []).append(added[c['ref']])
    HV_SHEETS = ('01_AC_Input_LCL', '02_AFE_Bridge', '03_DClink_Precharge',
                 '04_Inverter_Bridge')
    for sheet, fps in sorted(bysheet.items()):
        reg = REGIONS.get(sheet, DEFAULT_REGION)
        fps.sort(key=lambda f: (-f.GetBoundingBox().GetWidth(),
                                f.GetReference()))
        # en zona HV la net class exige 3 mm: se separa mas
        place_region(board, fps, reg, gap=7.0 if sheet in HV_SHEETS else 4.0)
        print('  %-22s %3d componentes -> region %s' %
              (sheet or '(raiz)', len(fps), reg))

    # --- redes ---
    netmap = {}
    for name, nodes in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
        for ref, pin in nodes:
            fp = added.get(ref)
            if fp is None:
                continue
            pad = fp.FindPadByNumber(pin)
            if pad is not None:
                pad.SetNet(ni)
    print('redes asignadas: %d' % len(netmap))

    # --- contorno de placa ---
    for (ax, ay, bx, by) in ((0, 0, BW, 0), (BW, 0, BW, BH),
                             (BW, BH, 0, BH), (0, BH, 0, 0)):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(vec(ax, ay))
        seg.SetEnd(vec(bx, by))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    # --- agujeros de montaje M4 ---
    for (hx, hy) in ((6, 6), (BW - 6, 6), (6, BH - 6), (BW - 6, BH - 6),
                     (BW / 2, 6), (BW / 2, BH - 6)):
        h = load_fp(board, 'MountingHole:MountingHole_4.3mm_M4')
        if h is not None:
            h.SetPosition(vec(hx, hy))
            board.Add(h)

    # --- rotulos de zona en la serigrafia ---
    labels = [
        (BW / 2, 6.5, 'ZONA HV - 800 V - DESCARGAR EL BUS ANTES DE MANIPULAR'),
        (BW / 2, 141, 'BARRERA DE AISLAMIENTO REFORZADA - NO CRUZAR PISTAS'),
        (BW / 2, 236, 'ZONA LV - CONTROL Y TELEMETRIA'),
        (48, 16, '01 ENTRADA AC + LCL'), (117, 16, '02 AFE'),
        (181, 16, '03 BUS DC'), (263, 16, '04 INVERSOR'),
        (45, 164, '09 AUX'), (128, 164, '06 SENSADO'),
        (204, 164, '07 STM32'), (216, 212, '08 PROTECCION'),
        (253, 164, '10 ISO'), (302, 164, '11 ESP32'),
    ]
    for (tx, ty, txt) in labels:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(vec(tx, ty))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.6), mm(1.6)))
        t.SetTextThickness(mm(0.25))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        board.Add(t)

    # --- linea de barrera en serigrafia (guia visual) ---
    for yy in (BARRIER_Y0, BARRIER_Y1):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(vec(2, yy))
        seg.SetEnd(vec(BW - 2, yy))
        seg.SetLayer(pcbnew.F_SilkS)
        seg.SetWidth(mm(0.3))
        board.Add(seg)

    # ---------------------------------------------------------- zonas
    def add_zone(netname, layer, x0, y0, x1, y1, prio=0):
        z = pcbnew.ZONE(board)
        pts = pcbnew.VECTOR_VECTOR2I()
        for (px, py) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            pts.append(vec(px, py))
        z.AddPolygon(pts)
        z.SetLayer(layer)
        ni = netmap.get(netname)
        if ni is None:
            # Una zona SIN red es cobre huerfano: todos los pads de alrededor
            # la ven como otra red y violan clearance (fueron 198 errores).
            print('   AVISO: la red %r no existe en la netlist -> zona omitida'
                  % netname)
            return None
        z.SetNet(ni)
        z.SetAssignedPriority(prio)
        z.SetLocalClearance(mm(0.5))
        z.SetMinThickness(mm(0.25))
        board.Add(z)
        return z

    HVY0, HVY1 = 10.0, 130.0
    LVY0, LVY1 = 160.0, BH - 6
    # BUS DC LAMINADO. Es el "ruteo" del lazo de conmutacion: en vez de
    # tirar pistas, DC_P (F.Cu) y DC_N (B.Cu) se vierten SOLAPADOS sobre
    # TODA la fila de potencia (AFE + banco + inversor). Los campos de ida
    # y vuelta se cancelan y la inductancia del lazo se minimiza.
    # Antes solo cubrian el banco (x 152..234) y los 12 MOSFET, que estan
    # en x 98..286, quedaban fuera del bus.
    # NOTA: extender estas zonas sobre toda la fila de potencia (x 92..330)
    # se probo y EMPEORA el DRC: con 3 mm de clearance exigido a la clase
    # HV_DC y los pines del TO-247-4 a 2.54 mm, el plano no cabe entre el
    # drenador y la puerta (293 violaciones de clearance, 34 cortos).
    # El bus laminado sobre el banco se mantiene; llevar el bus hasta cada
    # medio puente exige recortes locales alrededor de gate/Kelvin, que es
    # trabajo de ruteo manual.
    add_zone('DC_P', pcbnew.F_Cu, 152, 14, 234, 126, prio=60)
    add_zone('DC_N', pcbnew.B_Cu, 152, 14, 234, 126, prio=60)
    # Masa de la zona HV en la capa interna 1.  Se vierte en GND porque el
    # net-tie NT2 une PGND<->GND: en la netlist solo existe GND.
    add_zone('GND', pcbnew.In1_Cu, 8, HVY0, BW - 8, HVY1, prio=50)
    # tierras del dominio de control
    add_zone('GND', pcbnew.In1_Cu, 8, LVY0, 268, LVY1, prio=50)
    add_zone('GND', pcbnew.In2_Cu, 8, LVY0, 268, LVY1, prio=45)
    add_zone('GND', pcbnew.B_Cu, 8, LVY0, 268, LVY1, prio=40)
    # isla aislada del ESP32 (IOGND) - sin union con GND
    add_zone('IOGND', pcbnew.In1_Cu, 272, LVY0, BW - 8, LVY1, prio=50)
    add_zone('IOGND', pcbnew.B_Cu, 272, LVY0, BW - 8, LVY1, prio=40)

    # area de exclusion: BARRERA DE AISLAMIENTO (sin cobre en ninguna capa)
    ka = pcbnew.ZONE(board)
    pts = pcbnew.VECTOR_VECTOR2I()
    for (px, py) in ((2, BARRIER_Y0), (BW - 2, BARRIER_Y0),
                     (BW - 2, BARRIER_Y1), (2, BARRIER_Y1)):
        pts.append(vec(px, py))
    ka.AddPolygon(pts)
    ka.SetIsRuleArea(True)
    ka.SetDoNotAllowCopperPour(True)
    ka.SetDoNotAllowPads(True)
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(True)
    ka.SetZoneName('ISO_BARRIER')
    lset = pcbnew.LSET()
    for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        lset.addLayer(L)
    ka.SetLayerSet(lset)
    board.Add(ka)

    print('zonas creadas: %d' % len(board.Zones()))

    board.BuildListOfNets()
    pcbnew.SaveBoard(OUTPCB, board)
    print('PCB guardada: %s' % os.path.relpath(OUTPCB, ROOT_DIR))

    # El relleno de zonas necesita el contexto de proyecto: se hace tras
    # recargar la placa desde disco.
    if os.environ.get('FILL_ZONES', '1') == '1':
        print('recargando para rellenar zonas...')
        b2 = pcbnew.LoadBoard(OUTPCB)
        zl = pcbnew.ZONES()
        for z in b2.Zones():
            if not z.GetIsRuleArea():
                zl.append(z)
        pcbnew.ZONE_FILLER(b2).Fill(zl)
        pcbnew.SaveBoard(OUTPCB, b2)
        filled = sum(1 for z in b2.Zones()
                     if not z.GetIsRuleArea() and not z.IsFilled() is True)
        print('zonas rellenadas: %d' % len(zl))
    return 0


if __name__ == '__main__':
    sys.exit(main())
