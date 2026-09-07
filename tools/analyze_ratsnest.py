"""
analyze_ratsnest.py - Que falta por rutear, por red y por clase.

Antes de rutear hay que saber que se rutea. Los pads que caen dentro de una
zona rellenada de su misma red YA estan conectados: no hay que tirarles pista.

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/analyze_ratsnest.py
"""

import collections
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, 'kicad', 'b2b_converter.kicad_pcb')


def mm(v):
    return pcbnew.ToMM(v)


def main():
    board = pcbnew.LoadBoard(PCB)
    board.BuildConnectivity()
    conn = board.GetConnectivity()

    # zonas rellenadas por red
    zonenets = collections.Counter()
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        zonenets[z.GetNetname()] += 1

    # pads por red
    padsper = collections.defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n:
                padsper[n].append((fp.GetReference(), pad.GetNumber()))

    ratsnest = conn.GetUnconnectedCount(True)
    print('Items sin conectar (ratsnest): %d' % ratsnest)
    print('Zonas rellenadas: %s'
          % ', '.join('%s x%d' % (k, v) for k, v in sorted(zonenets.items())))
    print()

    filas = []
    for net, pads in padsper.items():
        if len(pads) < 2:
            continue
        tiene_zona = net in zonenets
        filas.append((len(pads), net, tiene_zona))
    filas.sort(reverse=True)

    tot_pads_zona = sum(n for n, _, z in filas if z)
    tot_pads_ruta = sum(n for n, _, z in filas if not z)
    print('%-26s %5s  %s' % ('RED', 'PADS', 'como se conecta'))
    print('-' * 66)
    for n, net, z in filas[:28]:
        print('%-26s %5d  %s' % (net[:26], n,
                                 'ZONA (ya conectada)' if z
                                 else 'hay que rutear pista'))
    if len(filas) > 28:
        print('... y %d redes mas' % (len(filas) - 28))
    print('-' * 66)
    print('Pads en redes con zona ....... %4d  (no requieren pista)'
          % tot_pads_zona)
    print('Pads en redes a rutear ....... %4d' % tot_pads_ruta)
    print('Redes a rutear ............... %4d'
          % sum(1 for _, _, z in filas if not z))

    # longitud de pista existente
    ntracks = sum(1 for t in board.GetTracks()
                  if t.GetClass() == 'PCB_TRACK')
    nvias = sum(1 for t in board.GetTracks() if t.GetClass() == 'PCB_VIA')
    print()
    print('Pistas existentes: %d   Vias: %d' % (ntracks, nvias))
    return 0


if __name__ == '__main__':
    sys.exit(main())
