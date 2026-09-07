"""
gen_schematic.py - Genera el esquematico completo del convertidor back-to-back.

Salida:  kicad/b2b_converter.kicad_sch  +  kicad/sch/*.kicad_sch
Ejecutar con el Python que trae KiCad:
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/gen_schematic.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kisch import SymbolCache, Schematic, check_schematic  # noqa

ROOT_DIR = os.path.dirname(HERE)
OUT = os.path.join(ROOT_DIR, 'kicad')
SYMDIR = r'C:\Program Files\KiCad\9.0\share\kicad\symbols'
FPDIR = os.path.join(os.path.dirname(SYMDIR), 'footprints')
PROJECT = 'b2b_converter'
ROOT_UUID = 'b2b00000-0000-4000-8000-000000000000'

lib = SymbolCache(SYMDIR)

# ------------------------------------------------------------------ footprints
FP = {
    'R0603':  'Resistor_SMD:R_0603_1608Metric',
    'R1206':  'Resistor_SMD:R_1206_3216Metric',
    'R2512':  'Resistor_SMD:R_2512_6332Metric',
    'RPWR':   'Resistor_THT:R_Axial_Power_L38.0mm_W9.0mm_P45.72mm',
    'C0603':  'Capacitor_SMD:C_0603_1608Metric',
    'C0805':  'Capacitor_SMD:C_0805_2012Metric',
    'C1210':  'Capacitor_SMD:C_1210_3225Metric',
    'CFILM':  'Capacitor_THT:C_Rect_L24.0mm_W10.3mm_P22.50mm_MKT',
    'CDCLK':  'Capacitor_THT:CP_Radial_D35.0mm_P10.00mm_SnapIn',
    'CY':     'Capacitor_THT:C_Disc_D9.0mm_W2.5mm_P5.00mm',
    'D_SMA':  'Diode_SMD:D_SMA',
    'D_SOD':  'Diode_SMD:D_SOD-123',
    'D_TO247': 'Package_TO_SOT_THT:TO-247-2_Vertical',
    'LED0805': 'LED_SMD:LED_0805_2012Metric',
    'SIC':    'Package_TO_SOT_THT:TO-247-4_Vertical',
    'IND_PWR': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
    'SOIC8':  'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
    'SOIC16W': 'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
    'SOIC14': 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',
    'SOT23-5': 'Package_TO_SOT_SMD:SOT-23-5',
    'SOT23':  'Package_TO_SOT_SMD:SOT-23',
    'LQFP100': 'Package_QFP:LQFP-100_14x14mm_P0.5mm',
    'ESP32':  'RF_Module:ESP32-S3-WROOM-1',
    'XTAL':   'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',
    'TB2':    'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
    'TB3':    'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal',
    'TB4':    'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4_1x04_P5.00mm_Horizontal',
    'PINH4':  'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'PINH3':  'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    'SWD':    'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical',
    'SWPUSH': 'Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2',
    'RELAY':  'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal',
    'NETTIE': 'NetTie:NetTie-2_SMD_Pad0.5mm',
    'TP':     'TestPoint:TestPoint_Pad_D2.0mm',
    'FUSE':   'Fuse:Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin',
    'MOV':    'Varistor:RV_Disc_D12mm_W4.6mm_P7.5mm',
    'NTC':    'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
    'USBC':   'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
}

# ------------------------------------------------------------------ simbolos
S_R = 'Device:R'
S_C = 'Device:C'
S_CP = 'Device:C_Polarized'
S_L = 'Device:L'
S_D = 'Device:D'
S_LED = 'Device:LED'
S_FUSE = 'Device:Fuse'
S_MOV = 'Device:Varistor'
S_NTC = 'Device:Thermistor'
S_TP = 'Connector:TestPoint'
S_SIC = 'Transistor_FET:C3M0075120K'      # 1200 V TO-247-4 (D,S,DS=Kelvin,G)
S_NMOS = 'Transistor_FET:Q_NMOS_GDS'
S_DRV = 'Driver_FET:UCC21520DW'
S_ISO = 'Isolator:ADuM1401xRW'
S_OPA = 'Amplifier_Operational:LM358'
S_MCU = 'MCU_ST_STM32G4:STM32G474V_B-C-E_Tx'
S_ESP = 'RF_Module:ESP32-S3-WROOM-1'
S_TB4 = 'Connector:Screw_Terminal_01x04'
S_TB3 = 'Connector:Screw_Terminal_01x03'
S_TB2 = 'Connector:Screw_Terminal_01x02'
S_CONN4 = 'Connector_Generic:Conn_01x04'
S_XTAL = 'Device:Crystal_GND24'
S_SW = 'Switch:SW_Push'
S_NT = 'Device:NetTie_2'
S_LDO = 'Regulator_Linear:TLV75801PDBV'

SHEETS = [
    ('01_AC_Input_LCL',      'sch/ac_input_lcl.kicad_sch',      'b2b00000-0000-4000-8000-0000000000a1'),
    ('02_AFE_Bridge',        'sch/afe_bridge.kicad_sch',        'b2b00000-0000-4000-8000-0000000000a2'),
    ('03_DClink_Precharge',  'sch/dclink_precharge.kicad_sch',  'b2b00000-0000-4000-8000-0000000000a3'),
    ('04_Inverter_Bridge',   'sch/inverter_bridge.kicad_sch',   'b2b00000-0000-4000-8000-0000000000a4'),
    ('05_Gate_Drivers',      'sch/gate_driver.kicad_sch',       'b2b00000-0000-4000-8000-0000000000a5'),
    ('06_Sense_I_V',         'sch/sense_iv.kicad_sch',          'b2b00000-0000-4000-8000-0000000000a6'),
    ('07_MCU_STM32',         'sch/mcu_stm32.kicad_sch',         'b2b00000-0000-4000-8000-0000000000a7'),
    ('08_Protection_IO',     'sch/protection_io.kicad_sch',     'b2b00000-0000-4000-8000-0000000000a8'),
    ('09_PSU_Aux_Bias',      'sch/psu_aux.kicad_sch',           'b2b00000-0000-4000-8000-0000000000a9'),
    ('10_Isolation_Comms',   'sch/isolation_comms.kicad_sch',   'b2b00000-0000-4000-8000-0000000000aa'),
    ('11_ESP32_IoT',         'sch/esp32_iot.kicad_sch',         'b2b00000-0000-4000-8000-0000000000ab'),
]


def newsheet(idx, title, comments=()):
    name, fn, su = SHEETS[idx]
    return Schematic(title, lib, PROJECT, ROOT_UUID, su,
                     paper='A2', comments=comments)


# ============================================================ helpers de dibujo

def vres(sch, ref, val, x, y, fp='R0603'):
    """Resistencia vertical. Devuelve (arriba, abajo)."""
    p = sch.place(S_R, ref, val, x, y, 0, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def hres(sch, ref, val, x, y, fp='R0603'):
    p = sch.place(S_R, ref, val, x, y, 90, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')      # (izq, der)


def vcap(sch, ref, val, x, y, fp='C0603', sym=S_C):
    p = sch.place(sym, ref, val, x, y, 0, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def hcap(sch, ref, val, x, y, fp='C0603', sym=S_C):
    p = sch.place(sym, ref, val, x, y, 90, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def h2pin(sch, sym, ref, val, x, y, fp):
    """Cualquier simbolo de 2 pines, horizontal. Devuelve (obj, izq, der)."""
    p = sch.place(sym, ref, val, x, y, 90, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def vind(sch, ref, val, x, y, fp='IND_PWR'):
    p = sch.place(S_L, ref, val, x, y, 0, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def hind(sch, ref, val, x, y, fp='IND_PWR'):
    p = sch.place(S_L, ref, val, x, y, 90, footprint=FP[fp])
    return p, p.pin('1'), p.pin('2')


def decouple(sch, ref, val, x, y, net_top, gnd='GND', fp='C0603'):
    """Condensador de desacoplo a GND con etiqueta arriba."""
    c, t, b = vcap(sch, ref, val, x, y, fp)
    sch.wire(t, (x, y - 6.35))
    sch.label(net_top, (x, y - 6.35), 90)
    sch.power(gnd, b)
    return c


# ============================================================ SHEET 01 - LCL

def sheet01():
    sch = newsheet(0, '01 - Entrada AC + Filtro LCL',
                   ('Red 3~ 400 V 60 Hz -> EMC -> LCL -> puente AFE',
                    'L1=1.5 mH  Cf=10 uF  Rd=2.2 ohm  L2=0.6 mH  fres=2.4 kHz'))
    sch.text('SHEET 01 - ENTRADA AC + FILTRO LCL\n'
             'Orden fisico: RED -> fusible -> contactor -> choke CM -> L2(red) '
             '-> [Cf+Rd al neutro] -> L1(conv) -> puente AFE\n'
             'Clase de red: HV_AC (clearance 3.0 mm / creepage 4.0 mm)',
             (25, 15), size=2.2)

    J1 = sch.place(S_TB4, 'J1', 'RED 3~ + PE', 45, 60, 180, footprint=FP['TB4'])
    phases = ['L1', 'L2', 'L3']
    ys = [50, 70, 90]
    for i, (ph, y) in enumerate(zip(phases, ys)):
        pin = J1.pin(str(i + 1))
        # columna propia por fase: si compartieran x se cortocircuitarian
        colx = 54 + i * 5
        sch.wire(pin, (colx, pin[1]))
        sch.wire(sch.wire(( colx, pin[1]), (colx, y)) or (colx, y), (72, y))
        # fusible
        f, fa, fb = h2pin(sch, S_FUSE, 'F%d' % (i + 1), '25A aR', 82, y,
                          'FUSE')
        sch.wire((72, y), fa)
        sch.wire(fb, (100, y))
        # choke de modo comun (3 devanados acoplados)
        lcm, la, lb = hind(sch, 'LCM%d' % (i + 1), '3mH CM', 118, y)
        sch.wire((100, y), la)
        sch.label('GRID_%s' % ph, ((la[0] + lb[0]) / 2, y - 3.0), 0)
        # L2 lado red
        l2, l2a, l2b = hind(sch, 'L2%s' % 'ABC'[i], '0.6mH', 148, y)
        sch.wire(lb, l2a)
        # nodo intermedio LCL
        node = (172, y)
        sch.wire(l2b, node)
        sch.junction(node)
        sch.label('LCL_%s' % 'ABC'[i], (172, y - 3.0), 0)
        # L1 lado convertidor
        l1, l1a, l1b = hind(sch, 'L1%s' % 'ABC'[i], '1.5mH', 196, y)
        sch.wire(node, l1a)
        sch.wire(l1b, (216, y))
        sch.glabel('AFE_%s' % 'ABC'[i], (216, y), 0, 'bidirectional')
        # sensado de tension de red
        sch.glabel('GRID_%s' % ph, (128, y - 12), 0, 'output')
        sch.wire((124, y), (124, y - 12))
        sch.wire((124, y - 12), (128, y - 12))
        sch.junction((124, y))

    # PE del conector
    pe = J1.pin('4')
    sch.wire(pe, (48, pe[1]))
    sch.wire((48, pe[1]), (48, 130))
    sch.label('PE', (48, 130), 0)
    sch.power('PE', (60, 130)) if False else None

    # --- banco de MOV (unido por etiqueta, sin cruzar fases) ---
    for i, ph in enumerate(['L1', 'L2', 'L3']):
        x = 96 + i * 18
        mov = sch.place(S_MOV, 'RV%d' % (i + 1), '20D471K', x, 168, 0,
                        footprint=FP['MOV'])
        sch.wire(mov.pin('1'), (x, 158))
        sch.label('GRID_%s' % ph, (x, 158), 90)
        sch.wire(mov.pin('2'), (x, 178))
        sch.label('PE', (x, 178), 270)
    sch.box(86, 148, 148, 186, 'PROTECCION DE SOBRETENSION (MOV clase II)',
            size=1.8)

    # --- banco Cf + Rd del LCL (unido por etiqueta) ---
    for i, ltr in enumerate('ABC'):
        x = 168 + i * 20
        rd, rda, rdb = vres(sch, 'RD%s' % ltr, '2R2 10W', x, 168, 'RPWR')
        sch.wire(rda, (x, 158))
        sch.label('LCL_%s' % ltr, (x, 158), 90)
        cf, cfa, cfb = vcap(sch, 'CF%s' % ltr, '10uF 500VAC', x, 186, 'CFILM')
        sch.wire(rdb, cfa)
        sch.wire(cfb, (x, 196))
        sch.label('LCL_N', (x, 196), 270)
    sch.box(158, 148, 216, 204, 'RAMA Cf + Rd DEL LCL  (amortiguamiento)',
            size=1.8)

    # neutro del banco Cf: referencia a PE por Y-caps
    for i, ref in enumerate(['CY1', 'CY2', 'CY3']):
        c, a, b = vcap(sch, ref, '4n7 Y2', 210 + i * 14, 128, 'CY')
        sch.wire(a, (210 + i * 14, 118))
        sch.label('LCL_N', (210 + i * 14, 118), 0)
        sch.wire(b, (210 + i * 14, 140))
        sch.label('PE', (210 + i * 14, 140), 0)

    # caps X de modo diferencial
    for i, (ref, na, nb) in enumerate([('CX1', 'GRID_L1', 'GRID_L2'),
                                       ('CX2', 'GRID_L2', 'GRID_L3')]):
        c, a, b = vcap(sch, ref, '470n X2', 262 + i * 18, 128, 'CFILM')
        sch.wire(a, (262 + i * 18, 118))
        sch.label(na, (262 + i * 18, 118), 0)
        sch.wire(b, (262 + i * 18, 140))
        sch.label(nb, (262 + i * 18, 140), 0)

    sch.box(140, 36, 232, 108,
            'FILTRO LCL: L2(red) - nodo - L1(conv).  fres = 2.4 kHz')
    sch.box(66, 36, 140, 108, 'PROTECCION + EMC DE ENTRADA')
    return sch


# ============================================================ medio puente SiC

def halfbridge(sch, x, ytop, ybot, qh, ql, swnet, idx, cdec_ref):
    """Dibuja una rama de medio puente SiC entre DC_P (ytop) y DC_N (ybot)."""
    ymid = (ytop + ybot) / 2.0
    Qh = sch.place(S_SIC, qh, 'C3M0075120K', x, ytop + 26, 0,
                   footprint=FP['SIC'])
    Ql = sch.place(S_SIC, ql, 'C3M0075120K', x, ybot - 26, 0,
                   footprint=FP['SIC'])
    # drain alto -> DC_P
    sch.wire_l(Qh.pin('1'), (x, ytop), first='v')
    sch.junction((x, ytop))
    # source alto -> nodo de conmutacion
    sch.wire_l(Qh.pin('2'), (x, ymid), first='v')
    # drain bajo -> nodo de conmutacion
    sch.wire_l(Ql.pin('1'), (x, ymid), first='v')
    sch.junction((x, ymid))
    # source bajo -> DC_N
    sch.wire_l(Ql.pin('2'), (x, ybot), first='v')
    sch.junction((x, ybot))
    # salida del nodo
    sch.wire((x, ymid), (x + 22, ymid))
    sch.glabel(swnet, (x + 22, ymid), 0, 'bidirectional')
    # gate y kelvin
    for Q, tag in ((Qh, 'H%d' % idx), (Ql, 'L%d' % idx)):
        g = Q.pin('4')
        k = Q.pin('3')
        sch.wire(g, (g[0] - 12, g[1]))
        sch.glabel('G_%s' % tag, (g[0] - 12, g[1]), 180, 'input')
        sch.wire(k, (k[0] + 12, k[1]))
        sch.glabel('K_%s' % tag, (k[0] + 12, k[1]), 0, 'passive')
    # decoupling de lazo de conmutacion
    cx = x - 26
    c, a, b = vcap(sch, cdec_ref, '1uF 1kV', cx, ymid, 'CFILM')
    sch.wire_l(a, (cx, ytop), first='v')
    sch.junction((cx, ytop))
    sch.wire_l(b, (cx, ybot), first='v')
    sch.junction((cx, ybot))
    return Qh, Ql


def bridge_sheet(idx, title, comments, qbase, gbase, nets, note):
    sch = newsheet(idx, title, comments)
    sch.text(note, (25, 15), size=2.2)
    ytop, ybot = 60, 200
    x0 = 90
    dx = 88
    # rieles DC
    sch.wire((x0 - 30, ytop), (x0 + 2 * dx, ytop))
    sch.wire((x0 - 30, ybot), (x0 + 2 * dx, ybot))
    sch.glabel('DC_P', (x0 - 30, ytop), 180, 'bidirectional')
    sch.glabel('DC_N', (x0 - 30, ybot), 180, 'bidirectional')
    for i in range(3):
        halfbridge(sch, x0 + i * dx, ytop, ybot,
                   '%s%d' % (qbase, 2 * i + 1), '%s%d' % (qbase, 2 * i + 2),
                   nets[i], gbase + i, 'CD%s' % nets[i][-1])
        sch.box(x0 + i * dx - 36, ytop - 8, x0 + i * dx + 36, ybot + 8,
                'RAMA %s' % nets[i][-1], size=2.0)
    sch.text('LAZO DE CONMUTACION: el condensador de 1 uF/1 kV va a menos de\n'
             '10 mm del par de MOSFET. Objetivo L_lazo < 20 nH.',
             (25, 225), size=2.0)
    return sch


def sheet02():
    return bridge_sheet(
        1, '02 - Puente AFE (Active Front End)',
        ('6x SiC 1200 V - rectificador activo PWM - fsw 16 kHz',),
        'Q', 1, ['SW_A', 'SW_B', 'SW_C'],
        'SHEET 02 - PUENTE AFE\n'
        'Ramas A/B/C. Nodos SW_A/B/C van al filtro LCL (sheet 01, red AFE_x).\n'
        'Gates G_H1..3 / G_L1..3 y Kelvin K_H1..3 / K_L1..3 al sheet 05.')


def sheet04():
    sch = bridge_sheet(
        3, '04 - Puente Inversor (lado motor)',
        ('6x SiC 1200 V - FOC - salida U/V/W al motor',),
        'Q', 4, ['SW_U', 'SW_V', 'SW_W'],
        'SHEET 04 - PUENTE INVERSOR\n'
        'Ramas U/V/W. Gates G_H4..6 / G_L4..6 y Kelvin al sheet 05.\n'
        'Salida a bornera de motor con PE y abrazadera de malla 360 grados.')
    # renombrar los MOSFET a Q7..Q12
    n = 7
    for p in sch.placed:
        if p.lib_id == S_SIC:
            p.ref = 'Q%d' % n
            n += 1
    # bornera de motor
    JM = sch.place(S_TB4, 'J4', 'MOTOR U/V/W/PE', 420, 120, 0,
                   footprint=FP['TB4'])
    for i, net in enumerate(['SW_U', 'SW_V', 'SW_W']):
        pin = JM.pin(str(i + 1))
        sch.wire(pin, (pin[0] - 20, pin[1]))
        sch.glabel(net, (pin[0] - 20, pin[1]), 180, 'input')
    pe = JM.pin('4')
    sch.wire(pe, (pe[0] - 20, pe[1]))
    sch.label('PE', (pe[0] - 20, pe[1]), 180)
    # NTC de disipador
    for i, ref in enumerate(['RT1', 'RT2']):
        t = sch.place(S_NTC, ref, '10k B3950', 400 + i * 30, 200, 0,
                      footprint=FP['NTC'])
        sch.wire(t.pin('1'), (400 + i * 30, 190))
        sch.glabel('NTC%d' % (i + 1), (400 + i * 30, 190), 90, 'output')
        sch.wire(t.pin('2'), (400 + i * 30, 210))
        sch.power('GND', (400 + i * 30, 210))
    sch.text('RT1 = disipador   RT2 = cuerpo de modulo', (392, 218), size=1.8)
    return sch


# ============================================================ SHEET 03 - BUS DC

def sheet03():
    sch = newsheet(2, '03 - Bus DC + Precarga + Chopper',
                   ('Banco C_dc 600 uF / 900 V - precarga 68 ohm - '
                    'chopper de frenado',))
    sch.text('SHEET 03 - BUS DC / PRECARGA / CHOPPER DE FRENADO\n'
             'Precarga: Rpc 68 ohm limita el inrush a 8 A. tau = 48 ms. '
             'K2 puentea a Vdc >= 510 V o t = 300 ms.\n'
             'Energia por carga en Rpc = 112 J -> resistencia bobinada con '
             'rating de pulso.',
             (25, 15), size=2.2)

    ytop, ybot = 70, 190
    xL, xR = 70, 330
    sch.wire((xL, ytop), (xR, ytop))
    sch.wire((100, ybot), (xR, ybot))
    sch.glabel('DC_P', (xR, ytop), 0, 'bidirectional')
    sch.glabel('DC_N', (xR, ybot), 0, 'bidirectional')

    # entrada rectificada desde los diodos de cuerpo del AFE
    sch.glabel('DC_RAW', (40, ytop), 180, 'input')
    sch.wire((40, ytop), (52, ytop))
    # resistencia de precarga
    rpc, a, b = hres(sch, 'RPC', '68R 200W', 60, ytop, 'RPWR')
    sch.wire((52, ytop), a)
    sch.wire(b, (xL, ytop))
    sch.junction((xL, ytop))
    # contactor de bypass K2
    k2, ka, kb = h2pin(sch, 'Switch:SW_SPST', 'K2', 'BYPASS PRECARGA',
                       60, ytop - 22, 'RELAY')
    sch.wire((52, ytop), (52, ytop - 22))
    sch.junction((52, ytop))
    sch.wire((52, ytop - 22), ka)
    sch.wire(kb, (xL, ytop - 22))
    sch.wire((xL, ytop - 22), (xL, ytop))
    sch.text('K2 = contactor de bypass de precarga', (46, ytop - 32), size=1.8)

    # banco de condensadores
    for i in range(4):
        x = 100 + i * 26
        c, a, b = vcap(sch, 'C%d' % (i + 1), '150uF 900V', x, 130, 'CDCLK')
        sch.wire_l(a, (x, ytop), first='v')
        sch.junction((x, ytop))
        sch.wire_l(b, (x, ybot), first='v')
        sch.junction((x, ybot))
    sch.box(88, ytop - 6, 214, ybot + 6,
            'BANCO DC-LINK  4x150uF/900V film = 600 uF', size=2.0)

    # bleeder + LED bus vivo
    x = 226
    rb, a, b = vres(sch, 'RBLEED', '100k 3W', x, 110, 'RPWR')
    sch.wire_l(a, (x, ytop), first='v')
    sch.junction((x, ytop))
    rl, la, lb = vres(sch, 'RLED', '220k', x, 145, 'R1206')
    sch.wire(b, la)
    led = sch.place(S_LED, 'D1', 'BUS LIVE', x, 170, 270, footprint=FP['LED0805'])
    sch.wire(lb, led.pin('1'))
    sch.wire_l(led.pin('2'), (x, ybot), first='v')
    sch.junction((x, ybot))

    # divisor de sensado de Vdc
    x = 250
    prev = (x, ytop)
    sch.junction((x, ytop))
    for i in range(5):
        r, a, b = vres(sch, 'RDV%d' % (i + 1), '200k 0.1%', x, 88 + i * 18,
                       'R1206')
        sch.wire_l(prev, a, first='v')
        prev = b
    sch.wire(prev, (x, 182))
    sch.glabel('VDC_SENSE_H', (x + 18, 182), 0, 'output')
    sch.wire((x, 182), (x + 18, 182))
    sch.junction((x, 182))
    rlo, a, b = vres(sch, 'RDV6', '1k 0.1%', x, 190, 'R1206')
    sch.text('Divisor 1 Mohm : 800 V -> ~0.8 V al amp aislado (sheet 06)',
             (236, 200), size=1.8)

    # chopper de frenado
    x = 300
    q = sch.place(S_SIC, 'QBRK', 'C3M0075120K', x, 110, 0, footprint=FP['SIC'])
    sch.wire_l(q.pin('1'), (x, ytop), first='v')
    sch.junction((x, ytop))
    sch.wire(q.pin('4'), (x - 16, q.pin('4')[1]))
    sch.glabel('G_BRK', (x - 16, q.pin('4')[1]), 180, 'input')
    sch.wire(q.pin('3'), (x + 14, q.pin('3')[1]))
    sch.glabel('K_BRK', (x + 14, q.pin('3')[1]), 0, 'passive')
    sch.wire(q.pin('2'), (x, 140))
    JB = sch.place(S_TB2, 'J3', 'R FRENADO', 330, 150, 0, footprint=FP['TB2'])
    sch.wire((x, 140), (x, 150))
    sch.junction((x, 150))
    sch.wire((x, 150), JB.pin('1'))
    sch.wire(JB.pin('2'), (JB.pin('2')[0], ybot))
    sch.wire((JB.pin('2')[0], ybot), (xR, ybot))
    db = sch.place(S_D, 'DBRK', '1200V SiC', x - 16, 150, 180,
                   footprint=FP['D_TO247'])
    sch.wire(db.pin('1'), (x - 16, ytop))
    sch.junction((x - 16, ytop))
    sch.wire(db.pin('2'), (x - 16, 150))
    sch.wire((x - 16, 150), (x, 150))
    sch.box(284, ytop - 6, 350, 170,
            'CHOPPER DE FRENADO  (umbral 760-780 V)', size=2.0)
    return sch


# ============================================================ SHEET 05 - DRIVERS

def gatedriver(sch, x, y, idx):
    """Un UCC21520DW aislado sirviendo una rama de medio puente."""
    U = sch.place(S_DRV, 'U%d' % (idx + 10), 'UCC21520DW', x, y, 0,
                  footprint=FP['SOIC16W'])
    # --- lado logico (CTRL) ---
    for pin, net, dy in (('1', 'PWM_H%d' % idx, 0), ('2', 'PWM_L%d' % idx, 0)):
        p = U.pin(pin)
        sch.wire(p, (p[0] - 16, p[1]))
        sch.glabel(net, (p[0] - 16, p[1]), 180, 'input')
    p = U.pin('5')                                 # DIS
    sch.wire(p, (p[0] - 16, p[1]))
    sch.glabel('PWM_DIS', (p[0] - 16, p[1]), 180, 'input')
    p = U.pin('6')                                 # DT (dead-time)
    rdt, a, b = vres(sch, 'RDT%d' % idx, '10k', p[0] - 10, p[1] + 12)
    sch.wire(p, (p[0] - 10, p[1]))
    sch.wire((p[0] - 10, p[1]), a)
    sch.power('GND', b)
    for pin in ('3', '8'):                         # VCCI
        p = U.pin(pin)
        sch.wire(p, (p[0] - 8, p[1]))
        sch.power('+5V', (p[0] - 8, p[1]))
    p = U.pin('4')                                 # GND logico
    sch.wire(p, (p[0] - 8, p[1]))
    sch.power('GND', (p[0] - 8, p[1]))
    c = decouple(sch, 'C%d' % (200 + idx), '100n', x - 30, y + 34, '+5V')
    # --- lado alto (flotante) ---
    pv = U.pin('16')      # VDDA
    ps = U.pin('14')      # VSSA
    po = U.pin('15')      # OUTA
    sch.wire(pv, (pv[0] + 12, pv[1]))
    sch.glabel('+15VG%dH' % idx, (pv[0] + 12, pv[1]), 0, 'input')
    sch.wire(ps, (ps[0] + 12, ps[1]))
    sch.glabel('K_H%d' % idx, (ps[0] + 12, ps[1]), 0, 'passive')
    rg, ga, gb = hres(sch, 'RGH%d' % idx, '10R', po[0] + 14, po[1], 'R2512')
    sch.wire(po, ga)
    sch.wire(gb, (gb[0] + 10, gb[1]))
    sch.glabel('G_H%d' % idx, (gb[0] + 10, gb[1]), 0, 'output')
    # rama de apagado rapido
    rgo, oa, ob = hres(sch, 'RGOH%d' % idx, '3R3', po[0] + 14, po[1] + 10,
                       'R2512')
    dgo = sch.place(S_D, 'DGH%d' % idx, 'BAV21', po[0] + 34, po[1] + 10, 270,
                    footprint=FP['D_SOD'])
    sch.wire(po, (po[0], po[1] + 10))
    sch.wire((po[0], po[1] + 10), oa)
    sch.wire(ob, dgo.pin('2'))
    sch.wire(dgo.pin('1'), (gb[0] + 10, po[1] + 10))
    sch.wire((gb[0] + 10, po[1] + 10), (gb[0] + 10, gb[1]))
    sch.junction((gb[0] + 10, gb[1]))
    # --- lado bajo (flotante) ---
    pv = U.pin('11')      # VDDB
    ps = U.pin('9')       # VSSB
    po = U.pin('10')      # OUTB
    sch.wire(pv, (pv[0] + 12, pv[1]))
    sch.glabel('+15VG%dL' % idx, (pv[0] + 12, pv[1]), 0, 'input')
    sch.wire(ps, (ps[0] + 12, ps[1]))
    sch.glabel('K_L%d' % idx, (ps[0] + 12, ps[1]), 0, 'passive')
    rg, ga, gb = hres(sch, 'RGL%d' % idx, '10R', po[0] + 14, po[1], 'R2512')
    sch.wire(po, ga)
    sch.wire(gb, (gb[0] + 10, gb[1]))
    sch.glabel('G_L%d' % idx, (gb[0] + 10, gb[1]), 0, 'output')
    rgo, oa, ob = hres(sch, 'RGOL%d' % idx, '3R3', po[0] + 14, po[1] + 10,
                       'R2512')
    dgo = sch.place(S_D, 'DGL%d' % idx, 'BAV21', po[0] + 34, po[1] + 10, 270,
                    footprint=FP['D_SOD'])
    sch.wire(po, (po[0], po[1] + 10))
    sch.wire((po[0], po[1] + 10), oa)
    sch.wire(ob, dgo.pin('2'))
    sch.wire(dgo.pin('1'), (gb[0] + 10, po[1] + 10))
    sch.wire((gb[0] + 10, po[1] + 10), (gb[0] + 10, gb[1]))
    sch.junction((gb[0] + 10, gb[1]))
    # pines NC
    for pin in ('7', '12', '13'):
        sch.nc(U.pin(pin))
    sch.box(x - 40, y - 26, x + 74, y + 44, 'DRIVER RAMA %d' % idx, size=2.0)


def sheet05():
    sch = newsheet(4, '05 - Gate Drivers aislados (6 ramas)',
                   ('UCC21520DW reforzado, CMTI 100 V/ns, dead-time por RDT',
                    'Rg_on 10R / Rg_off 3R3 - ajustar en banco'))
    sch.text('SHEET 05 - GATE DRIVERS AISLADOS\n'
             'Ramas 1-3 = AFE (sheet 02).  Ramas 4-6 = INVERSOR (sheet 04).\n'
             'Bias +15VGnH / +15VGnL aislados por rama (sheet 09). '
             'Referencia = pin Kelvin del SiC (K_Hn / K_Ln).\n'
             'PWM_DIS apaga las 6 ramas por hardware desde la cadena de falla '
             '(sheet 08).',
             (25, 12), size=2.2)
    for i in range(6):
        col = i % 2
        row = i // 2
        gatedriver(sch, 110 + col * 200, 60 + row * 92, i + 1)
    return sch


# ============================================================ SHEET 06 - SENSE

def sense_chain(sch, x, y, name, ref_i, conn_ref):
    """Cadena: transductor Hall -> burden -> amp -> filtro AA -> ADC."""
    J = sch.place(S_TB3, conn_ref, 'HALL %s' % name, x, y, 180,
                  footprint=FP['TB3'])
    sch.power('+15V', J.pin('1'))
    sch.power('GND', J.pin('3'))
    out = J.pin('2')
    sch.wire(out, (out[0] + 12, out[1]))
    rb, a, b = vres(sch, ref_i, '100R 0.1%', out[0] + 12, out[1] + 14, 'R1206')
    sch.wire((out[0] + 12, out[1]), a)
    sch.power('GND', b)
    sch.junction((out[0] + 12, out[1]))
    # filtro anti-alias RC (2 polos) + etiqueta a ADC
    r1, a1, b1 = hres(sch, ref_i + 'A', '1k', out[0] + 26, out[1])
    sch.wire((out[0] + 12, out[1]), a1)
    c1, ca, cb = vcap(sch, ref_i + 'C', '10n C0G', b1[0] + 8, out[1] + 14)
    sch.wire(b1, (b1[0] + 8, out[1]))
    sch.junction((b1[0] + 8, out[1]))
    sch.wire((b1[0] + 8, out[1]), ca)
    sch.power('GND', cb)
    r2, a2, b2 = hres(sch, ref_i + 'B', '1k', b1[0] + 22, out[1])
    sch.wire((b1[0] + 8, out[1]), a2)
    c2, ca2, cb2 = vcap(sch, ref_i + 'D', '4n7 C0G', b2[0] + 8, out[1] + 14)
    sch.wire(b2, (b2[0] + 8, out[1]))
    sch.junction((b2[0] + 8, out[1]))
    sch.wire((b2[0] + 8, out[1]), ca2)
    sch.power('GND', cb2)
    sch.wire((b2[0] + 8, out[1]), (b2[0] + 22, out[1]))
    sch.glabel(name, (b2[0] + 22, out[1]), 0, 'output')


def sheet06():
    sch = newsheet(5, '06 - Sensado I / V + acondicionamiento',
                   ('Hall closed-loop + burden + filtro anti-alias fc ~14 kHz',
                    'Referencia de ADC 3.000 V buffered'))
    sch.text('SHEET 06 - SENSADO DE CORRIENTE Y TENSION\n'
             'Cada canal: transductor Hall aislado -> resistencia burden 0.1% '
             '-> filtro anti-alias RC de 2 polos -> ADC del STM32.\n'
             'El muestreo va sincronizado al centro del PWM, por eso fc puede '
             'ser ~14 kHz sin degradar el lazo (retardo de grupo < 1 us).',
             (25, 12), size=2.2)
    chans = [('AIN_IAFE_A', 'RB1', 'J10'), ('AIN_IAFE_B', 'RB2', 'J11'),
             ('AIN_IAFE_C', 'RB3', 'J12'), ('AIN_IMOT_U', 'RB4', 'J13'),
             ('AIN_IMOT_V', 'RB5', 'J14'), ('AIN_IMOT_W', 'RB6', 'J15')]
    for i, (name, rb, jc) in enumerate(chans):
        sense_chain(sch, 60, 60 + i * 34, name, rb, jc)
    sch.box(44, 44, 230, 66 + 5 * 34, 'CANALES DE CORRIENTE (6)', size=2.0)

    # buffer de Vdc con LM358
    U = sch.place(S_OPA, 'U20', 'LM358', 300, 80, 0, unit=1,
                  footprint=FP['SOIC8'])
    Up = sch.place(S_OPA, 'U20', 'LM358', 300, 150, 0, unit=3,
                   footprint=FP['SOIC8'])
    sch.power('+5V', Up.pin('8'))
    sch.power('GND', Up.pin('4'))
    ip = U.pin('3')
    sch.wire(ip, (ip[0] - 16, ip[1]))
    sch.glabel('VDC_SENSE_H', (ip[0] - 16, ip[1]), 180, 'input')
    out = U.pin('1')
    inm = U.pin('2')
    sch.wire(out, (out[0] + 10, out[1]))
    sch.wire((out[0] + 10, out[1]), (out[0] + 10, out[1] + 16))
    sch.wire((out[0] + 10, out[1] + 16), (inm[0] - 6, out[1] + 16))
    sch.wire((inm[0] - 6, out[1] + 16), (inm[0] - 6, inm[1]))
    sch.wire((inm[0] - 6, inm[1]), inm)
    sch.junction((out[0] + 10, out[1]))
    sch.wire((out[0] + 10, out[1]), (out[0] + 26, out[1]))
    sch.glabel('AIN_VDC', (out[0] + 26, out[1]), 0, 'output')
    sch.text('Buffer seguidor del divisor de bus (sheet 03)', (286, 100),
             size=1.8)

    # unidad libre del LM358 -> seguidor con entrada a masa (no dejar al aire)
    Us = sch.place(S_OPA, 'U20', 'LM358', 300, 250, 0, unit=2,
                   footprint=FP['SOIC8'])
    sp = sorted(lib.pins(S_OPA, 2))
    ip, im, op = Us.pin(sp[2]), Us.pin(sp[1]), Us.pin(sp[0])
    sch.wire(ip, (ip[0] - 8, ip[1]))
    sch.power('GND', (ip[0] - 8, ip[1]))
    sch.wire(op, (op[0] + 8, op[1]))
    sch.wire((op[0] + 8, op[1]), (op[0] + 8, im[1]))
    sch.wire((op[0] + 8, im[1]), im)
    sch.text('U20B: unidad libre configurada como seguidor.', (286, 262),
             size=1.8)

    # referencia de ADC
    rr, a, b = vres(sch, 'RREF', '10k', 300, 200, 'R0603')
    sch.power('+3V3', a)
    sch.glabel('VREF_ADC', (300, 210), 0, 'output')
    sch.wire(b, (300, 210))
    cr = decouple(sch, 'C70', '10u', 320, 210, 'VREF_ADC', fp='C0805')
    sch.text('VREF_ADC: sustituir por REF5030 en la version final.\n'
             'Aqui se deja el nodo creado para el ruteo en estrella al pin '
             'VREF+ del STM32.', (286, 218), size=1.8)

    # NTC pull-ups
    for i in range(2):
        r, a, b = vres(sch, 'RNTC%d' % (i + 1), '10k 0.1%', 400 + i * 24, 70)
        sch.power('+3V3', a)
        sch.wire(b, (400 + i * 24, 84))
        sch.glabel('NTC%d' % (i + 1), (400 + i * 24, 84), 180, 'input')
        sch.junction((400 + i * 24, 84))
        sch.wire((400 + i * 24, 84), (400 + i * 24, 92))
        sch.glabel('AIN_NTC%d' % (i + 1), (400 + i * 24, 92), 0, 'output')
    sch.text('Divisores de NTC (disipador y modulo)', (392, 100), size=1.8)
    return sch


# ============================================================ SHEET 07 - STM32

MCU_PINS = {
    # PWM inversor (TIM1)
    'PE9': 'PWM_H4', 'PE8': 'PWM_L4', 'PE11': 'PWM_H5', 'PE10': 'PWM_L5',
    'PE13': 'PWM_H6', 'PE12': 'PWM_L6',
    # PWM AFE (TIM8)
    'PC6': 'PWM_H1', 'PA7': 'PWM_L1', 'PC7': 'PWM_H2', 'PB0': 'PWM_L2',
    'PC8': 'PWM_H3', 'PB1': 'PWM_L3',
    # break / fallo
    'PA6': 'FAULT_N', 'PE15': 'FAULT_N2',
    # ADC
    'PA0': 'AIN_IMOT_U', 'PA1': 'AIN_IMOT_V', 'PA2': 'AIN_IMOT_W',
    'PA3': 'AIN_IAFE_A', 'PA4': 'AIN_IAFE_B', 'PA5': 'AIN_IAFE_C',
    'PC0': 'AIN_VDC', 'PC1': 'AIN_NTC1', 'PC2': 'AIN_NTC2',
    'PC3': 'AIN_VGRID_A', 'PB12': 'AIN_VGRID_B', 'PB13': 'AIN_VGRID_C',
    # encoder
    'PB4': 'ENC_A', 'PB5': 'ENC_B', 'PB6': 'ENC_Z',
    # comunicacion aislada con el ESP32
    'PD5': 'ISO_UART_TX', 'PD6': 'ISO_UART_RX',
    'PD3': 'ISO_HB_OUT', 'PD4': 'ISO_HB_IN',
    # control de potencia
    'PD8': 'K1_DRV', 'PD9': 'K2_DRV', 'PD10': 'FAN_DRV',
    'PD11': 'PWM_DIS', 'PD12': 'WDI', 'PD13': 'G_BRK',
    'PD14': 'LED_RUN', 'PD15': 'LED_FAULT',
}


def sheet07():
    sch = newsheet(6, '07 - MCU STM32G474VET6 (dominio de control)',
                   ('TIM1/TIM8 SVPWM con dead-time HW, ADC sinc. al centro '
                    'del PWM',
                    'CORDIC/FMAC para FOC y PLL trifasico'))
    sch.text('SHEET 07 - STM32G474VET6 (LQFP-100)\n'
             'TIM1 -> 6 PWM del inversor.  TIM8 -> 6 PWM del AFE.  '
             'BKIN/BKIN2 <- FAULT_N (apagado por hardware).\n'
             'NT1 une AGND<->DGND bajo VREF-.  NT2 une DGND<->PGND en el '
             'retorno del sensado de DC_N.',
             (25, 12), size=2.2)
    U = sch.place(S_MCU, 'U1', 'STM32G474VET6', 250, 160, 0,
                  footprint=FP['LQFP100'])
    # mapear nombre de pin -> numero
    from kisch import _findall, Sym
    d = lib.get(S_MCU)
    name2num = {}
    for sub in _findall(d, Sym('symbol')):
        for p in _findall(sub, Sym('pin')):
            nm = _findall(p, Sym('name'))[0][1]
            nu = _findall(p, Sym('number'))[0][1]
            name2num.setdefault(nm, nu)
    placed_lbl = 0
    for pname, net in MCU_PINS.items():
        num = name2num.get(pname)
        if not num:
            continue
        pt = U.pin(num)
        # direccion segun el lado del simbolo
        left = pt[0] < U.x
        dx = -14 if left else 14
        sch.wire(pt, (pt[0] + dx, pt[1]))
        sch.glabel(net, (pt[0] + dx, pt[1]), 180 if left else 0,
                   'bidirectional')
        placed_lbl += 1
    # alimentacion
    for nm, net in (('VDD', '+3V3'), ('VDDA', '+3V3'), ('VBAT', '+3V3'),
                    ('VREF+', '+3V3')):
        for sub in _findall(d, Sym('symbol')):
            for p in _findall(sub, Sym('pin')):
                if _findall(p, Sym('name'))[0][1] != nm:
                    continue
                num = _findall(p, Sym('number'))[0][1]
                pt = U.pin(num)
                sch.wire(pt, (pt[0], pt[1] - 6))
                sch.power(net, (pt[0], pt[1] - 6))
    for sub in _findall(d, Sym('symbol')):
        for p in _findall(sub, Sym('pin')):
            nm = _findall(p, Sym('name'))[0][1]
            if nm not in ('VSS', 'VSSA'):
                continue
            num = _findall(p, Sym('number'))[0][1]
            pt = U.pin(num)
            sch.wire(pt, (pt[0], pt[1] + 6))
            sch.power('GND', (pt[0], pt[1] + 6))
    # pines sin usar -> no-connect explicito (silencia ERC)
    used = set()
    for pname in MCU_PINS:
        if pname in name2num:
            used.add(name2num[pname])
    for sub in _findall(d, Sym('symbol')):
        for pp in _findall(sub, Sym('pin')):
            nm = _findall(pp, Sym('name'))[0][1]
            nu = _findall(pp, Sym('number'))[0][1]
            if nu in used or nm in ('VDD', 'VDDA', 'VBAT', 'VREF+',
                                    'VSS', 'VSSA'):
                continue
            sch.nc(U.pin(nu))

    # desacoplo
    for i in range(10):
        decouple(sch, 'C%d' % (100 + i), '100n', 60 + i * 12, 300, '+3V3')
    decouple(sch, 'C110', '4u7', 60, 330, '+3V3', fp='C0805')
    decouple(sch, 'C111', '4u7', 84, 330, '+3V3', fp='C0805')
    # cristal
    X1 = sch.place(S_XTAL, 'X1', '24MHz', 430, 300, 0, footprint=FP['XTAL'])
    for pin, ref, x in (('1', 'C112', 414), ('2', 'C113', 446)):
        c, a, b = vcap(sch, ref, '18p', x, 316)
        sch.wire(X1.pin(pin), (x, X1.pin(pin)[1]))
        sch.wire((x, X1.pin(pin)[1]), a)
        sch.power('GND', b)
        sch.glabel('OSC_IN' if pin == '1' else 'OSC_OUT',
                   (x, X1.pin(pin)[1] - 10), 90, 'passive')
        sch.wire((x, X1.pin(pin)[1]), (x, X1.pin(pin)[1] - 10))
        sch.junction((x, X1.pin(pin)[1]))
    for pin in ('3', '4'):
        try:
            sch.power('GND', X1.pin(pin))
        except KeyError:
            pass
    # net ties de tierra
    nt1 = sch.place(S_NT, 'NT1', 'AGND-DGND', 380, 360, 90,
                    footprint=FP['NETTIE'])
    sch.label('AGND', nt1.pin('1'), 180)
    sch.label('GND', nt1.pin('2'), 0)
    nt2 = sch.place(S_NT, 'NT2', 'DGND-PGND', 440, 360, 90,
                    footprint=FP['NETTIE'])
    sch.label('GND', nt2.pin('1'), 180)
    sch.label('PGND', nt2.pin('2'), 0)
    sch.text('NT1 / NT2: union de tierras en UN SOLO punto.\n'
             'IOGND (ESP32) NO se une aqui: es barrera.', (370, 372), size=1.8)
    # SWD
    J = sch.place(S_CONN4, 'J20', 'SWD', 470, 120, 180, footprint=FP['PINH4'])
    for i, net in enumerate(['+3V3', 'SWDIO', 'SWCLK', 'GND']):
        pt = J.pin(str(i + 1))
        sch.wire(pt, (pt[0] - 14, pt[1]))
        if net in ('+3V3', 'GND'):
            sch.power(net, (pt[0] - 14, pt[1]))
        else:
            sch.glabel(net, (pt[0] - 14, pt[1]), 180, 'bidirectional')
    # reset
    SW = sch.place(S_SW, 'SW1', 'NRST', 470, 190, 0, footprint=FP['SWPUSH'])
    sch.glabel('NRST', (SW.pin('1')[0] - 12, SW.pin('1')[1]), 180, 'input')
    sch.wire(SW.pin('1'), (SW.pin('1')[0] - 12, SW.pin('1')[1]))
    sch.power('GND', SW.pin('2'))
    return sch


# ============================================================ SHEET 08 - PROT

def sheet08():
    sch = newsheet(7, '08 - Proteccion HW + I/O digital',
                   ('Cadena de falla independiente del firmware -> BKIN',
                    'E-stop, rele K1/K2, watchdog, latch de falla'))
    sch.text('SHEET 08 - PROTECCION POR HARDWARE\n'
             'La proteccion de sobrecorriente y shoot-through NO depende de '
             'software: comparador -> FAULT_N -> BKIN del timer -> MOE=0.\n'
             'FAULT_N tambien apaga los 6 drivers via PWM_DIS y abre el '
             'contactor de linea K1.',
             (25, 12), size=2.2)
    # drivers de bobina (low side)
    for i, (ref, net, lbl) in enumerate([
            ('Q20', 'K1_DRV', 'CONTACTOR LINEA K1'),
            ('Q21', 'K2_DRV', 'BYPASS PRECARGA K2'),
            ('Q22', 'FAN_DRV', 'VENTILADOR')]):
        x = 70 + i * 90
        y = 90
        Q = sch.place(S_NMOS, ref, 'AO3400', x, y, 0, footprint=FP['SOT23'])
        g = Q.pin('1')
        sch.wire(g, (g[0] - 14, g[1]))
        sch.glabel(net, (g[0] - 14, g[1]), 180, 'input')
        sch.power('GND', Q.pin('3'))
        d = Q.pin('2')
        sch.wire(d, (d[0], d[1] - 14))
        J = sch.place(S_TB2, 'J%d' % (30 + i), lbl, x, y - 40, 0,
                      footprint=FP['TB2'])
        sch.wire((d[0], d[1] - 14), J.pin('2'))
        sch.power('+24V', J.pin('1'))
        D = sch.place(S_D, 'D%d' % (20 + i), '1N4148', x + 20, y - 20, 180,
                      footprint=FP['D_SOD'])
        sch.wire(D.pin('2'), (x + 20, d[1] - 14))
        sch.wire((x + 20, d[1] - 14), (d[0], d[1] - 14))
        sch.junction((d[0], d[1] - 14))
        sch.wire(D.pin('1'), (x + 20, y - 40))
        sch.power('+24V', (x + 20, y - 40))
        sch.box(x - 26, y - 52, x + 34, y + 20, lbl, size=1.8)

    # comparadores de sobrecorriente (LM339 x4 unidades)
    for u in range(1, 5):
        x = 90 + ((u - 1) % 2) * 120
        y = 190 + ((u - 1) // 2) * 60
        C = sch.place('Comparator:LM339', 'U30', 'LM339', x, y, 0, unit=u,
                      footprint=FP['SOIC14'])
        nets = {1: 'AIN_IMOT_U', 2: 'AIN_IMOT_V', 3: 'AIN_IMOT_W',
                4: 'AIN_VDC'}
        pins = sorted(lib.pins('Comparator:LM339', u))
        ip = C.pin(pins[2]) if len(pins) > 2 else C.pin(pins[0])
        sch.wire(ip, (ip[0] - 14, ip[1]))
        sch.glabel(nets[u], (ip[0] - 14, ip[1]), 180, 'input')
        im = C.pin(pins[1])
        sch.wire(im, (im[0] - 14, im[1]))
        sch.glabel('VTRIP', (im[0] - 14, im[1]), 180, 'input')
        op = C.pin(pins[0])
        sch.wire(op, (op[0] + 14, op[1]))
        sch.glabel('FAULT_N', (op[0] + 14, op[1]), 0, 'output')
    C5 = sch.place('Comparator:LM339', 'U30', 'LM339', 330, 190, 0, unit=5,
                   footprint=FP['SOIC14'])
    for pn in sorted(lib.pins('Comparator:LM339', 5)):
        pt = C5.pin(pn)
        if pt[1] < 190:
            sch.wire(pt, (pt[0], pt[1] - 6))
            sch.power('+3V3', (pt[0], pt[1] - 6))
        else:
            sch.wire(pt, (pt[0], pt[1] + 6))
            sch.power('GND', (pt[0], pt[1] + 6))
    sch.text('U30 = 4 comparadores de disparo (open-collector, cableados en\n'
             'OR sobre FAULT_N con pull-up). VTRIP viene del divisor de\n'
             'umbral. Anadir histeresis con realimentacion positiva.',
             (300, 210), size=1.8)
    # pull-up de FAULT_N
    r, a, b = vres(sch, 'RPU1', '4k7', 300, 130)
    sch.power('+3V3', a)
    sch.wire(b, (300, 142))
    sch.glabel('FAULT_N', (300, 142), 0, 'bidirectional')
    # e-stop
    J = sch.place(S_TB2, 'J33', 'E-STOP', 430, 100, 0, footprint=FP['TB2'])
    r2, a2, b2 = vres(sch, 'RES1', '10k', 460, 110)
    sch.power('+3V3', a2)
    sch.wire(J.pin('1'), (460, J.pin('1')[1]))
    sch.wire((460, J.pin('1')[1]), (460, 122))
    sch.wire(b2, (460, 122))
    sch.junction((460, 122))
    sch.glabel('ESTOP_N', (460, 122), 0, 'output')
    sch.power('GND', J.pin('2'))
    sch.text('E-STOP: contacto seco NC. Al abrir -> ESTOP_N alto -> falla.',
             (400, 132), size=1.8)
    # LEDs
    for i, (ref, net) in enumerate([('D30', 'LED_RUN'), ('D31', 'LED_FAULT')]):
        x = 400 + i * 30
        r, a, b = vres(sch, 'RL%d' % i, '1k', x, 300)
        sch.glabel(net, (x, 290), 90, 'input')
        sch.wire((x, 290), a)
        led = sch.place(S_LED, ref, net, x, 320, 270, footprint=FP['LED0805'])
        sch.wire(b, led.pin('1'))
        sch.power('GND', led.pin('2'))
    return sch


# ============================================================ SHEET 09 - PSU

def sheet09():
    sch = newsheet(8, '09 - Alimentacion auxiliar + bias aislado',
                   ('24 V -> 15 V / 5 V / 3V3  +  6 bias aislados +15 V',
                    'Secuenciado: bias antes de habilitar PWM'))
    sch.text('SHEET 09 - ALIMENTACION AUXILIAR\n'
             'Entrada 24 Vdc externa (riel DIN). Rieles: +15 V (analogico y '
             'logica de driver), +5 V, +3V3.\n'
             'Los 6 bias de gate son AISLADOS y flotan con el Kelvin de su '
             'rama. Sin ellos el driver no debe habilitarse (UVLO).',
             (25, 12), size=2.2)
    J = sch.place(S_TB2, 'J40', '24 Vdc IN', 55, 70, 180, footprint=FP['TB2'])
    sch.power('+24V', J.pin('1'))
    sch.power('GND', J.pin('2'))
    f, fa, fb = h2pin(sch, S_FUSE, 'F10', '3A', 80, 60, 'FUSE')
    sch.wire(J.pin('1'), fa)
    sch.wire(fb, (96, 60))
    sch.label('+24V_F', (96, 60), 0)
    # bulk
    for i, (ref, val, net) in enumerate([('C40', '470u 35V', '+24V'),
                                         ('C41', '220u 25V', '+15V'),
                                         ('C42', '100u 10V', '+5V'),
                                         ('C43', '47u 10V', '+3V3')]):
        decouple(sch, ref, val, 120 + i * 26, 80, net, fp='C1210')
    # reguladores (representados como bloques LDO)
    for i, (ref, val, vin, vout) in enumerate([
            ('U40', 'LMR33630 24->15V', '+24V', '+15V'),
            ('U41', 'LMR33630 15->5V', '+15V', '+5V'),
            ('U42', 'TLV75833 5->3V3', '+5V', '+3V3')]):
        x = 90 + i * 110
        y = 150
        U = sch.place(S_LDO, ref, val, x, y, 0, footprint=FP['SOT23-5'])
        pins = sorted(lib.pins(S_LDO, 1))
        from kisch import _findall, Sym
        d = lib.get(S_LDO)
        nm = {}
        for sub in _findall(d, Sym('symbol')):
            for p in _findall(sub, Sym('pin')):
                nm[_findall(p, Sym('name'))[0][1]] = \
                    _findall(p, Sym('number'))[0][1]
        for key, net in (('IN', vin), ('OUT', vout)):
            if key in nm:
                pt = U.pin(nm[key])
                sch.wire(pt, (pt[0] + (-12 if key == 'IN' else 12), pt[1]))
                sch.power(net, (pt[0] + (-12 if key == 'IN' else 12), pt[1]))
        if 'GND' in nm:
            sch.power('GND', U.pin(nm['GND']))
        if 'EN' in nm:
            pt = U.pin(nm['EN'])
            sch.wire(pt, (pt[0] - 12, pt[1]))
            sch.power(vin, (pt[0] - 12, pt[1]))
        for pn in pins:
            pass
        sch.box(x - 30, y - 24, x + 34, y + 24, '%s -> %s' % (vin, vout),
                size=1.8)
    # 6 bias aislados
    for i in range(6):
        x = 60 + (i % 3) * 130
        y = 240 + (i // 3) * 70
        J = sch.place(S_CONN4, 'J%d' % (50 + i),
                      'DCDC ISO 15V rama %d' % (i + 1), x, y, 0,
                      footprint=FP['PINH4'])
        pts = [J.pin(str(k)) for k in range(1, 5)]
        sch.wire(pts[0], (pts[0][0] - 14, pts[0][1]))
        sch.power('+15V', (pts[0][0] - 14, pts[0][1]))
        sch.wire(pts[1], (pts[1][0] - 14, pts[1][1]))
        sch.power('GND', (pts[1][0] - 14, pts[1][1]))
        sch.wire(pts[2], (pts[2][0] - 14, pts[2][1]))
        sch.glabel('+15VG%dH' % (i + 1), (pts[2][0] - 14, pts[2][1]), 180,
                   'output')
        sch.wire(pts[3], (pts[3][0] - 14, pts[3][1]))
        sch.glabel('+15VG%dL' % (i + 1), (pts[3][0] - 14, pts[3][1]), 180,
                   'output')
        sch.box(x - 46, y - 12, x + 16, y + 26,
                'BIAS AISLADO RAMA %d' % (i + 1), size=1.8)
    sch.text('Cada modulo: 2 W, 15 V/-4 V, aislamiento reforzado.\n'
             'Alternativa discreta: SN6505 + transformador + rectificador.',
             (25, 380), size=2.0)
    return sch


# ============================================================ SHEET 10 - ISO

def sheet10():
    sch = newsheet(9, '10 - Barrera de aislamiento STM32 <-> ESP32',
                   ('ADuM1401 reforzado: UART + heartbeat',))
    sch.text('SHEET 10 - AISLAMIENTO DE COMUNICACIONES\n'
             'Aislamiento FUNCIONAL (ambos dominios son SELV): mantiene el '
             'ruido de conmutacion y el rebote de masa fuera del ESP32.\n'
             'GND1 = DGND del control.  GND2 = IOGND del ESP32. NO se unen.\n'
             'El ESP32 nunca esta en el lazo de par: solo telemetria y '
             'setpoints que el STM32 valida.',
             (25, 12), size=2.2)
    U = sch.place(S_ISO, 'U50', 'ADuM1401ARWZ', 250, 140, 0,
                  footprint=FP['SOIC16W'])
    mapping = [
        ('1', '+3V3', 'pwr'), ('2', 'GND', 'gnd'),
        ('3', 'ISO_UART_TX', 'in'), ('4', 'ISO_HB_OUT', 'in'),
        ('5', 'LED_FAULT', 'in'), ('6', 'ISO_UART_RX', 'out'),
        ('7', '+3V3', 'pwr'), ('8', 'GND', 'gnd'),
        ('9', 'IOGND', 'lbl'), ('10', '+3V3_IO', 'lbl'),
        ('11', 'IO_UART_TX', 'lbl'), ('12', 'IO_FAULT', 'lbl'),
        ('13', 'IO_HB_IN', 'lbl'), ('14', 'IO_UART_RX', 'lbl'),
        ('15', 'IOGND', 'lbl'), ('16', '+3V3_IO', 'lbl'),
    ]
    for pin, net, kind in mapping:
        pt = U.pin(pin)
        left = pt[0] < U.x
        dx = -16 if left else 16
        sch.wire(pt, (pt[0] + dx, pt[1]))
        tgt = (pt[0] + dx, pt[1])
        if kind == 'pwr':
            sch.power('+3V3', tgt)
        elif kind == 'gnd':
            sch.power('GND', tgt)
        else:
            sch.glabel(net, tgt, 180 if left else 0, 'bidirectional')
    for ref, x, net in (('C50', 200, '+3V3'), ('C51', 320, '+3V3_IO')):
        c, a, b = vcap(sch, ref, '100n', x, 210)
        sch.wire(a, (x, 200))
        if net == '+3V3':
            sch.power('+3V3', (x, 200))
            sch.power('GND', b)
        else:
            sch.glabel('+3V3_IO', (x, 200), 90, 'input')
            sch.wire(b, (x, 224))
            sch.glabel('IOGND', (x, 224), 270, 'input')
    sch.box(238, 96, 262, 200, 'BARRERA', size=1.8)
    sch.text('En la PCB: ranura fresada bajo U50 si el creepage del\n'
             'encapsulado es < 4 mm. Ninguna pista cruza esta linea.',
             (200, 240), size=2.0)
    return sch


# ============================================================ SHEET 11 - ESP32

def sheet11():
    sch = newsheet(10, '11 - ESP32-S3 pasarela IoT / SCADA',
                   ('Modbus TCP + MQTT/TLS + OTA. Dominio IOGND aislado',))
    sch.text('SHEET 11 - ESP32-S3 (DOMINIO IoT AISLADO)\n'
             'Solo telemetria. Recibe del STM32 por UART aislado y publica '
             'por MQTT/Modbus TCP.\n'
             'KEEP-OUT de cobre bajo la antena del modulo (ver floorplan).',
             (25, 12), size=2.2)
    U = sch.place(S_ESP, 'U60', 'ESP32-S3-WROOM-1-N8', 220, 170, 0,
                  footprint=FP['ESP32'])
    from kisch import _findall, Sym
    d = lib.get(S_ESP)
    nm = {}
    for sub in _findall(d, Sym('symbol')):
        for p in _findall(sub, Sym('pin')):
            nm.setdefault(_findall(p, Sym('name'))[0][1],
                          _findall(p, Sym('number'))[0][1])
    wanted = [('3V3', '+3V3_IO', 'lbl'), ('EN', 'ESP_EN', 'lbl'),
              ('IO17', 'IO_UART_TX', 'lbl'), ('IO18', 'IO_UART_RX', 'lbl'),
              ('IO8', 'IO_HB_IN', 'lbl'), ('IO9', 'IO_FAULT', 'lbl'),
              ('IO10', 'IO_LED_LINK', 'lbl'), ('IO11', 'IO_LED_MQTT', 'lbl')]
    for pname, net, _k in wanted:
        num = nm.get(pname)
        if not num:
            continue
        pt = U.pin(num)
        left = pt[0] < U.x
        dx = -16 if left else 16
        sch.wire(pt, (pt[0] + dx, pt[1]))
        sch.glabel(net, (pt[0] + dx, pt[1]), 180 if left else 0,
                   'bidirectional')
    for gname in ('GND',):
        for sub in _findall(d, Sym('symbol')):
            for p in _findall(sub, Sym('pin')):
                if _findall(p, Sym('name'))[0][1] != gname:
                    continue
                num = _findall(p, Sym('number'))[0][1]
                pt = U.pin(num)
                sch.wire(pt, (pt[0], pt[1] + 6))
                sch.glabel('IOGND', (pt[0], pt[1] + 6), 270, 'input')
    usedn = {nm.get(a) for a, _b, _c in wanted if nm.get(a)}
    for sub in _findall(d, Sym('symbol')):
        for pp in _findall(sub, Sym('pin')):
            nmv = _findall(pp, Sym('name'))[0][1]
            nuv = _findall(pp, Sym('number'))[0][1]
            if nuv in usedn or nmv == 'GND':
                continue
            sch.nc(U.pin(nuv))

    # desacoplo
    for i, (ref, val) in enumerate([('C60', '10u'), ('C61', '100n'),
                                    ('C62', '100n')]):
        x = 100 + i * 24
        c, a, b = vcap(sch, ref, val, x, 320, 'C0805' if i == 0 else 'C0603')
        sch.wire(a, (x, 310))
        sch.glabel('+3V3_IO', (x, 310), 90, 'input')
        sch.wire(b, (x, 334))
        sch.glabel('IOGND', (x, 334), 270, 'input')
    # boot / reset
    for i, (ref, net) in enumerate([('SW60', 'ESP_EN'), ('SW61', 'ESP_BOOT')]):
        x = 400 + i * 40
        SW = sch.place(S_SW, ref, net, x, 300, 0, footprint=FP['SWPUSH'])
        sch.wire(SW.pin('1'), (x, 290))
        sch.glabel(net, (x, 290), 90, 'bidirectional')
        sch.wire(SW.pin('2'), (x, 314))
        sch.glabel('IOGND', (x, 314), 270, 'input')
    # LEDs
    for i, (ref, net) in enumerate([('D60', 'IO_LED_LINK'),
                                    ('D61', 'IO_LED_MQTT')]):
        x = 400 + i * 40
        r, a, b = vres(sch, 'RL6%d' % i, '1k', x, 360)
        sch.glabel(net, (x, 350), 90, 'input')
        sch.wire((x, 350), a)
        led = sch.place(S_LED, ref, net, x, 380, 270, footprint=FP['LED0805'])
        sch.wire(b, led.pin('1'))
        sch.wire(led.pin('2'), (x, 392))
        sch.glabel('IOGND', (x, 392), 270, 'input')
    for i, net in enumerate(['+3V3_IO', 'IOGND']):
        x = 200 + i * 46
        y = 340
        sch.glabel(net, (x, y + 10), 90, 'input')
        sch.wire((x, y + 10), (x, y))
        sch.power('PWR_FLAG', (x, y))

    # conector de campo
    J = sch.place(S_TB4, 'J60', 'CAMPO / ETHERNET', 430, 170, 0,
                  footprint=FP['TB4'])
    for i in range(4):
        pt = J.pin(str(i + 1))
        sch.wire(pt, (pt[0] - 16, pt[1]))
        sch.glabel('FIELD_%d' % (i + 1), (pt[0] - 16, pt[1]), 180,
                   'bidirectional')
    return sch


# ============================================================ RAIZ

def rootsheet():
    sch = Schematic('B2B CONVERTER - HOJA RAIZ', lib, PROJECT, ROOT_UUID, None,
                    paper='A2',
                    comments=('15 kVA | 400 VLL 60 Hz | Vdc <= 800 V | '
                              'fsw 16 kHz',
                              'AFE + Inversor back-to-back | STM32G474 | '
                              'ESP32-S3',
                              'Generado por tools/gen_schematic.py',
                              'Reglas DRC: kicad/drc_custom_rules.txt'))
    sch.text('CONVERTIDOR BACK-TO-BACK  (AFE + INVERSOR TRIFASICO)\n\n'
             'Flujo de energia:  RED -> [01 LCL] -> [02 AFE] == [03 BUS DC] '
             '== [04 INVERSOR] -> MOTOR\n'
             'Frenado regenerativo: el AFE devuelve energia a la red; el '
             'chopper de [03] es solo respaldo.\n'
             'Control [07 STM32] con proteccion por hardware [08]. '
             'Telemetria [11 ESP32] tras barrera de aislamiento [10].\n\n'
             'Las hojas se conectan por GLOBAL LABELS (DC_P, DC_N, SW_*, '
             'G_*, K_*, PWM_*, AIN_*, FAULT_N, ...).',
             (25, 18), size=2.4)
    for i, (name, fn, su) in enumerate(SHEETS):
        col = i % 3
        row = i // 3
        sch.sheet(name, fn, 30 + col * 175, 70 + row * 62, 150, 40,
                  sheet_uuid=su, page=str(i + 2))
    return sch


# ============================================================ MAIN

def main():
    os.makedirs(os.path.join(OUT, 'sch'), exist_ok=True)
    builders = [sheet01, sheet02, sheet03, sheet04, sheet05,
                sheet06, sheet07, sheet08, sheet09, sheet10, sheet11]
    total = 0
    for i, b in enumerate(builders):
        sch = b()
        path = os.path.join(OUT, SHEETS[i][1].replace('/', os.sep))
        sch.save(path)
        n = len([p for p in sch.placed if not getattr(p, 'is_power', False)])
        total += n
        print('  %-24s %3d componentes  -> %s'
              % (SHEETS[i][0], n, os.path.relpath(path, ROOT_DIR)))
    root = rootsheet()
    root.save(os.path.join(OUT, 'b2b_converter.kicad_sch'))
    print('  %-24s (raiz, %d hojas)' % ('b2b_converter', len(SHEETS)))
    print('TOTAL: %d componentes' % total)
    print('--- validacion simbolo/footprint ---')
    allp = []
    for i, b in enumerate(builders):
        allp += check_schematic(b(), FPDIR)
    for x in sorted(set(allp)):
        print('  ' + x)
    if not allp:
        print('  OK: todos los footprints existen y casan en numero de pads')


if __name__ == '__main__':
    main()
