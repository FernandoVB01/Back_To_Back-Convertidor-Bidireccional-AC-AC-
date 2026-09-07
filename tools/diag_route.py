"""diag_route.py - Por que fallan las redes al rutear."""
import collections
import functools
import os
import sys

import pcbnew
print = functools.partial(print, flush=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PCB = os.path.join(ROOT, 'kicad', 'b2b_converter.kicad_pcb')

BARRIER_Y0, BARRIER_Y1 = 145.0, 151.0
HV_LIMIT_Y = 136.0


def tomm(v):
    return pcbnew.ToMM(v)


board = pcbnew.LoadBoard(PCB)

# --- donde caen los pads de un gate driver ---
print('PADS DE LOS GATE DRIVERS (deben tener logica abajo, gate arriba)')
for fp in board.GetFootprints():
    r = fp.GetReference()
    if r in ('U11', 'U12'):
        print('  %s en y=%.1f  rot=%.0f' % (r, tomm(fp.GetPosition().y),
                                            fp.GetOrientationDegrees()))
        for pad in fp.Pads():
            n = pad.GetNetname()
            if not n:
                continue
            y = tomm(pad.GetPosition().y)
            lado = ('HV(arriba)' if y < BARRIER_Y0 else
                    'LV(abajo)' if y > BARRIER_Y1 else '*** DENTRO ***')
            print('     pad %-3s  y=%7.2f  %-14s  %s'
                  % (pad.GetNumber(), y, lado, n))
        break

# --- clasificar cada red: cruza la barrera o no ---
print()
print('REDES QUE CRUZAN LA BARRERA (imposibles de rutear con pista)')
pads = collections.defaultdict(list)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNetname()
        if n:
            pads[n].append((tomm(pad.GetPosition().y),
                            fp.GetReference(), pad.GetNumber()))

cruzan, dentro, ok = [], [], []
for n, lst in pads.items():
    if len(lst) < 2:
        continue
    ys = [y for y, _, _ in lst]
    hay_hv = any(y < BARRIER_Y0 for y in ys)
    hay_lv = any(y > BARRIER_Y1 for y in ys)
    hay_in = any(BARRIER_Y0 <= y <= BARRIER_Y1 for y in ys)
    if hay_in:
        dentro.append(n)
    elif hay_hv and hay_lv:
        cruzan.append(n)
    else:
        ok.append(n)
for n in sorted(cruzan)[:20]:
    ys = sorted(y for y, _, _ in pads[n])
    print('  %-18s  y: %.1f .. %.1f' % (n, ys[0], ys[-1]))
print('  ... total %d' % len(cruzan))
print()
print('RESUMEN: %d redes cruzan la barrera, %d tienen pads DENTRO de la '
      'franja, %d se pueden rutear en su zona'
      % (len(cruzan), len(dentro), len(ok)))
