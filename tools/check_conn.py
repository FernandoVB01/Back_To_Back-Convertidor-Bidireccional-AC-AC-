"""
check_conn.py - Verificador de conectividad del esquematico generado.

Detecta dos clases de fallo que el ERC de KiCad reporta de forma confusa:
  1. EXTREMOS SUELTOS: un extremo de cable que no toca ningun pin, etiqueta,
     union, no-connect ni otro cable.
  2. SOLAPES: dos segmentos colineales que se superponen. En un esquematico
     esto es un CORTOCIRCUITO silencioso (p.ej. tres fases compartiendo la
     misma columna de ruteo).

Uso:
    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/check_conn.py
"""

import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kisch                                          # noqa: E402
from kisch import parse, _find, _findall, Sym         # noqa: E402

ROOT_DIR = os.path.dirname(HERE)
SYMDIR = r'C:\Program Files\KiCad\9.0\share\kicad\symbols'
_lib = kisch.SymbolCache(SYMDIR)


def _pt(node):
    at = _find(node, Sym('at'))
    return (round(float(at[1]), 3), round(float(at[2]), 3))


def analyze(path):
    with open(path, encoding='utf-8') as f:
        d = parse(f.read())

    pinpts = set()
    for sym in _findall(d, Sym('symbol')):
        lid = _find(sym, Sym('lib_id'))
        if lid is None:
            continue                      # definicion dentro de lib_symbols
        at = _find(sym, Sym('at'))
        X, Y = float(at[1]), float(at[2])
        R = float(at[3]) if len(at) > 3 else 0.0
        unit = _find(sym, Sym('unit'))
        u = int(unit[1]) if unit else 1
        mir = _find(sym, Sym('mirror'))
        a = math.radians(R)
        ca, sa = math.cos(a), math.sin(a)
        for _num, (px, py, _ang) in _lib.pins(lid[1], u).items():
            if mir and mir[1] == 'x':
                py = -py
            elif mir and mir[1] == 'y':
                px = -px
            pinpts.add((round(X + px * ca - py * sa, 3),
                        round(Y - (px * sa + py * ca), 3)))

    wires = []
    for w in _findall(d, Sym('wire')):
        pts = _find(w, Sym('pts'))
        xy = [(round(float(c[1]), 3), round(float(c[2]), 3))
              for c in _findall(pts, Sym('xy'))]
        if len(xy) == 2:
            wires.append(tuple(xy))

    anchors = set(pinpts)
    for tag in ('label', 'global_label', 'hierarchical_label',
                'junction', 'no_connect'):
        for n in _findall(d, Sym(tag)):
            anchors.add(_pt(n))

    ends = collections.Counter()
    for a1, a2 in wires:
        ends[a1] += 1
        ends[a2] += 1

    def on_other_wire(p, skip):
        for i, (b1, b2) in enumerate(wires):
            if i == skip:
                continue
            if abs(b1[0] - b2[0]) < 1e-6 and abs(p[0] - b1[0]) < 1e-6:
                if min(b1[1], b2[1]) - 1e-6 <= p[1] <= max(b1[1], b2[1]) + 1e-6:
                    return True
            if abs(b1[1] - b2[1]) < 1e-6 and abs(p[1] - b1[1]) < 1e-6:
                if min(b1[0], b2[0]) - 1e-6 <= p[0] <= max(b1[0], b2[0]) + 1e-6:
                    return True
        return False

    loose = []
    for i, seg in enumerate(wires):
        for p in seg:
            if p in anchors or ends[p] > 1 or on_other_wire(p, i):
                continue
            loose.append(p)

    overlaps = []
    for i in range(len(wires)):
        (a1, a2) = wires[i]
        for j in range(i + 1, len(wires)):
            (b1, b2) = wires[j]
            # vertical colineal
            if (abs(a1[0] - a2[0]) < 1e-6 and abs(b1[0] - b2[0]) < 1e-6
                    and abs(a1[0] - b1[0]) < 1e-6):
                lo = max(min(a1[1], a2[1]), min(b1[1], b2[1]))
                hi = min(max(a1[1], a2[1]), max(b1[1], b2[1]))
                if hi - lo > 1e-6:
                    overlaps.append(('V x=%.2f' % a1[0], round(lo, 2),
                                     round(hi, 2)))
            # horizontal colineal
            if (abs(a1[1] - a2[1]) < 1e-6 and abs(b1[1] - b2[1]) < 1e-6
                    and abs(a1[1] - b1[1]) < 1e-6):
                lo = max(min(a1[0], a2[0]), min(b1[0], b2[0]))
                hi = min(max(a1[0], a2[0]), max(b1[0], b2[0]))
                if hi - lo > 1e-6:
                    overlaps.append(('H y=%.2f' % a1[1], round(lo, 2),
                                     round(hi, 2)))

    return len(wires), sorted(set(loose)), sorted(set(overlaps))


def main():
    schdir = os.path.join(ROOT_DIR, 'kicad', 'sch')
    total = 0
    for fn in sorted(os.listdir(schdir)):
        if not fn.endswith('.kicad_sch'):
            continue
        n, loose, ov = analyze(os.path.join(schdir, fn))
        total += len(loose) + len(ov)
        if loose or ov:
            print('%-28s %3d cables | sueltos %2d %s | solapes %2d %s'
                  % (fn, n, len(loose), loose[:3], len(ov), ov[:3]))
        else:
            print('%-28s %3d cables | OK' % (fn, n))
    print('TOTAL problemas de conectividad: %d' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
