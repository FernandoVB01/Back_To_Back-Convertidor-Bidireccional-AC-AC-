"""
restore_pro.py - Reinyecta las net classes en b2b_converter.kicad_pro.

Por que existe: pcbnew.SaveBoard() SOBRESCRIBE el .kicad_pro del proyecto y
se lleva por delante las net classes, los anchos de pista y los patrones de
asignacion. Hay que volver a ponerlos despues de generar la PCB.

    python tools/restore_pro.py
"""

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRO = os.path.join(ROOT, 'kicad', 'b2b_converter.kicad_pro')


def cls(name, clearance, track, via_d=0.8, via_dr=0.4,
        color='rgba(0, 0, 0, 0.000)', prio=2147483647):
    return {
        'name': name, 'clearance': clearance, 'track_width': track,
        'via_diameter': via_d, 'via_drill': via_dr,
        'microvia_diameter': 0.3, 'microvia_drill': 0.1,
        'diff_pair_width': 0.2, 'diff_pair_gap': 0.25,
        'diff_pair_via_gap': 0.25, 'bus_width': 12, 'wire_width': 6,
        'line_style': 0, 'pcb_color': color, 'schematic_color': color,
        'priority': prio,
    }


CLASSES = [
    cls('Default', 0.25, 0.3),
    cls('HV_DC',   3.0, 2.5, 1.2, 0.6, 'rgba(220, 40, 40, 1.000)', 10),
    cls('HV_AC',   3.0, 2.5, 1.2, 0.6, 'rgba(240, 120, 20, 1.000)', 11),
    cls('GATE_HS', 0.3, 0.5, 0.8, 0.4, 'rgba(200, 60, 200, 1.000)', 20),
    cls('GATE_LS', 0.25, 0.5, 0.8, 0.4, 'rgba(160, 60, 200, 1.000)', 21),
    cls('ANA',     0.2, 0.25, 0.6, 0.3, 'rgba(40, 160, 80, 1.000)', 30),
    cls('CTRL',    0.2, 0.25, 0.6, 0.3, 'rgba(40, 120, 220, 1.000)', 31),
    cls('IO_ISO',  0.2, 0.25, 0.6, 0.3, 'rgba(20, 180, 200, 1.000)', 32),
    cls('PE',      0.3, 1.0, 1.0, 0.5, 'rgba(120, 200, 60, 1.000)', 40),
]

PATTERNS = [
    ('HV_DC', 'DC_P'), ('HV_DC', 'DC_N'), ('HV_DC', 'DC_RAW'),
    ('HV_DC', 'SW_*'),
    ('HV_AC', 'GRID_*'), ('HV_AC', 'AFE_*'), ('HV_AC', 'LCL_*'),
    ('HV_AC', 'MOT_*'),
    ('GATE_HS', 'G_H*'), ('GATE_HS', 'K_H*'),
    ('GATE_LS', 'G_L*'), ('GATE_LS', 'K_L*'),
    ('ANA', 'AIN_*'), ('ANA', 'VREF*'), ('ANA', 'NTC*'),
    ('CTRL', 'PWM_*'),
    ('IO_ISO', 'IO_*'), ('IO_ISO', 'IOGND'), ('IO_ISO', '+3V3_IO'),
    ('PE', 'PE'),
]


def main():
    if not os.path.isfile(PRO):
        print('no existe %s (genera antes la PCB)' % PRO)
        return 1
    with io.open(PRO, encoding='utf-8') as f:
        d = json.load(f)

    ns = d.setdefault('net_settings', {})
    ns['classes'] = CLASSES
    ns['netclass_patterns'] = [{'netclass': c, 'pattern': p}
                               for c, p in PATTERNS]

    bd = d.setdefault('board', {}).setdefault('design_settings', {})
    bd['track_widths'] = [0.0, 0.25, 0.4, 0.8, 1.5, 2.5, 4.0, 6.0]
    bd['via_dimensions'] = [
        {'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.6, 'drill': 0.3},
        {'diameter': 0.8, 'drill': 0.4}, {'diameter': 1.2, 'drill': 0.6}]
    bd.setdefault('rules', {}).update({
        'min_clearance': 0.2, 'min_track_width': 0.2,
        'min_copper_edge_clearance': 0.5})

    d.setdefault('text_variables', {}).update({
        'PROJECT': 'B2B Converter AFE+Inversor',
        'SPEC': '15 kVA / 400 VLL 60 Hz / Vdc<=800 V / fsw 16 kHz'})

    with io.open(PRO, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print('kicad_pro restaurado: %d net classes, %d patrones'
          % (len(CLASSES), len(PATTERNS)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
