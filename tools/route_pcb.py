"""
route_pcb.py - Ruteador para la PCB del convertidor B2B.

Estrategia en tres pasadas, de menos a mas riesgo:

  1. VIAS A PLANO. Los pads SMD de redes con zona (GND, IOGND, DC_P, DC_N)
     no tocan su plano: estan en una capa exterior y el plano esta dentro.
     Se les pone una via al lado con un rabillo. Los THT ya atraviesan.

  2. POTENCIA Y PUERTAS. Nodos de conmutacion y lazos de gate, con el ancho
     que exige su net class y respetando su clearance (3 mm en HV).

  3. SENALES. Ruteador L/Z con deteccion de colision. Lo que no consigue
     rutear se deja en el ratsnest para hacerlo a mano; NO se fuerza.

Reglas duras que el ruteador nunca viola:
  - no se entra en el area de exclusion ISO_BARRIER
  - se respeta el clearance de la net class (HV_DC/HV_AC = 3 mm)
  - no se cruza la frontera entre zona HV y zona LV

    "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" tools/route_pcb.py
"""

import math
import os
import sys

import functools
import pcbnew

print = functools.partial(print, flush=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, 'kicad', 'b2b_converter.kicad_pcb')

# ---------------------------------------------------------------- geometria
BARRIER_Y0, BARRIER_Y1 = 145.0, 151.0
HV_LIMIT_Y = 136.0        # por encima: zona HV.  Por debajo de 160: zona LV
LV_START_Y = 160.0

SIG_LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
ZONE_NETS = ('GND', 'IOGND', 'DC_P', 'DC_N', 'PGND', 'PE')

# ancho y clearance por clase (mm)
CLASS_RULES = {
    'HV_DC':   (2.5, 3.0),
    'HV_AC':   (2.5, 3.0),
    'GATE_HS': (0.5, 0.3),
    'GATE_LS': (0.5, 0.25),
    'ANA':     (0.25, 0.2),
    'CTRL':    (0.25, 0.2),
    'IO_ISO':  (0.25, 0.2),
    'PE':      (1.0, 0.3),
    'Default': (0.3, 0.25),
}


def mm(v):
    return pcbnew.FromMM(float(v))


def tomm(v):
    return pcbnew.ToMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def rules_for(netname):
    """Ancho y clearance segun el nombre de red (mismos patrones que el .pro)."""
    n = netname.upper()
    if n in ('DC_P', 'DC_N', 'DC_RAW') or n.startswith('SW_'):
        return CLASS_RULES['HV_DC']
    if (n.startswith('GRID_') or n.startswith('AFE_') or n.startswith('LCL_')
            or n.startswith('MOT_')):
        return CLASS_RULES['HV_AC']
    if n.startswith('G_H') or n.startswith('K_H'):
        return CLASS_RULES['GATE_HS']
    if n.startswith('G_L') or n.startswith('K_L') or n.startswith('G_BRK'):
        return CLASS_RULES['GATE_LS']
    if n.startswith('AIN_') or n.startswith('VREF') or n.startswith('NTC'):
        return CLASS_RULES['ANA']
    if n.startswith('IO_') or n in ('IOGND', '+3V3_IO'):
        return CLASS_RULES['IO_ISO']
    if n.endswith('PE') or n == 'PE':
        return CLASS_RULES['PE']
    if n.startswith('PWM_') or n.startswith('ISO_') or n.startswith('FAULT'):
        return CLASS_RULES['CTRL']
    return CLASS_RULES['Default']


def is_hv(netname):
    w, c = rules_for(netname)
    return c >= 3.0


# ---------------------------------------------------------------- obstaculos
class Obstacles:
    """Segmentos y pads ocupados, por capa. Test de distancia segmento-segmento."""

    def __init__(self):
        self.segs = {}          # layer -> [(x1,y1,x2,y2,halfwidth,net)]
        self.rects = {}         # layer -> [(x0,y0,x1,y1,net)]
        self.holes = []         # (x, y, radio, net)  -- atraviesan TODO

    def add_hole(self, x, y, r, net):
        self.holes.append((x, y, r, net))

    def hole_ok(self, x, y, r, net, clearance):
        for (hx, hy, hr, hnet) in self.holes:
            if hnet == net:
                continue
            if math.hypot(x - hx, y - hy) < r + hr + max(clearance, 0.25):
                return False
        return True

    def add_seg(self, layer, p0, p1, width, net):
        self.segs.setdefault(layer, []).append(
            (p0[0], p0[1], p1[0], p1[1], width / 2.0, net))

    def add_rect(self, layer, cx, cy, w, h, net):
        self.rects.setdefault(layer, []).append(
            (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, net))

    @staticmethod
    def _seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
        def d_pt_seg(px, py, x1, y1, x2, y2):
            vx, vy = x2 - x1, y2 - y1
            L2 = vx * vx + vy * vy
            if L2 < 1e-12:
                return math.hypot(px - x1, py - y1)
            t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L2))
            return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))
        # si se cruzan, distancia 0
        d1 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
        d2 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        d3 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
        d4 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
        if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
            return 0.0
        return min(d_pt_seg(ax, ay, cx, cy, dx, dy),
                   d_pt_seg(bx, by, cx, cy, dx, dy),
                   d_pt_seg(cx, cy, ax, ay, bx, by),
                   d_pt_seg(dx, dy, ax, ay, bx, by))

    def clear(self, layer, p0, p1, width, net, clearance):
        """True si el segmento cabe sin violar clearance."""
        hw = width / 2.0
        for (x1, y1, x2, y2, ohw, onet) in self.segs.get(layer, []):
            if onet == net:
                continue
            need = hw + ohw + max(clearance, rules_for(onet)[1])
            if self._seg_dist(p0[0], p0[1], p1[0], p1[1],
                              x1, y1, x2, y2) < need:
                return False
        for (rx0, ry0, rx1, ry1, onet) in self.rects.get(layer, []):
            if onet == net:
                continue
            need = hw + max(clearance, rules_for(onet)[1])
            # distancia segmento-rectangulo (aprox por los 4 lados)
            for (ex0, ey0, ex1, ey1) in ((rx0, ry0, rx1, ry0),
                                         (rx1, ry0, rx1, ry1),
                                         (rx1, ry1, rx0, ry1),
                                         (rx0, ry1, rx0, ry0)):
                if self._seg_dist(p0[0], p0[1], p1[0], p1[1],
                                  ex0, ey0, ex1, ey1) < need:
                    return False
        return True


def crosses_barrier(p0, p1):
    """Prohibido atravesar la franja de aislamiento o saltar de zona HV a LV."""
    for y in (p0[1], p1[1]):
        if BARRIER_Y0 - 0.5 <= y <= BARRIER_Y1 + 0.5:
            return True
    if (p0[1] < BARRIER_Y0) != (p1[1] < BARRIER_Y0):
        return True
    if (p0[1] < HV_LIMIT_Y) != (p1[1] < HV_LIMIT_Y):
        if min(p0[1], p1[1]) < HV_LIMIT_Y < max(p0[1], p1[1]):
            return True
    return False


# ---------------------------------------------------------------- utilidades
def add_track(board, p0, p1, layer, width, netcode):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(V(p0[0], p0[1]))
    t.SetEnd(V(p1[0], p1[1]))
    t.SetLayer(layer)
    t.SetWidth(mm(width))
    t.SetNetCode(netcode)
    board.Add(t)
    return t


def add_via(board, p, netcode, diam=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(p[0], p[1]))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    # En KiCad 9 SetWidth() exige capa; SetFrontWidth fija el diametro
    v.SetFrontWidth(mm(diam))
    v.SetDrill(mm(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(netcode)
    board.Add(v)
    return v


def pad_info(pad):
    p = pad.GetPosition()
    sz = pad.GetSize()
    return (tomm(p.x), tomm(p.y),
            tomm(sz.x), tomm(sz.y),
            pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD)


def mst(points):
    """Arbol de expansion minimo (Prim) sobre una lista de puntos."""
    n = len(points)
    if n < 2:
        return []
    used = [0]
    rest = list(range(1, n))
    edges = []
    while rest:
        best = None
        for a in used:
            for b in rest:
                d = math.dist(points[a], points[b])
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, a, b = best
        edges.append((a, b))
        used.append(b)
        rest.remove(b)
    return edges


# ---------------------------------------------------------------- main
def main():
    board = pcbnew.LoadBoard(PCB)
    board.BuildConnectivity()

    # --- inventario de obstaculos: todos los pads ---
    obs = Obstacles()
    padsbynet = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            x, y, w, h, smd = pad_info(pad)
            net = pad.GetNetname()
            for L in SIG_LAYERS:
                if pad.IsOnLayer(L):
                    obs.add_rect(L, x, y, w, h, net)
            if net:
                padsbynet.setdefault(net, []).append(
                    dict(x=x, y=y, w=w, h=h, smd=smd,
                         code=pad.GetNetCode(),
                         layer=(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu)
                                else pcbnew.B_Cu),
                         ref=fp.GetReference(), num=pad.GetNumber()))

    n_via, n_trk, n_fail = 0, 0, 0
    fallidas = []

    # ============================================================
    # PASADA 1: vias de los pads SMD a su plano
    # ============================================================
    for net in ZONE_NETS:
        for p in padsbynet.get(net, []):
            if not p['smd']:
                continue                       # THT ya atraviesa las capas
            # via pegada al pad, desplazada hacia fuera
            # via pequena: en un LQFP-100 (pitch 0.5 mm) una de 0.8 mm no cabe
            vd, vdr = (0.6, 0.3) if min(p['w'], p['h']) < 0.6 else (0.8, 0.4)
            colocado = False
            cand = []
            for k in (0.55, 0.8, 1.1, 1.5):
                off = max(p['w'], p['h']) / 2.0 + vd / 2.0 + k
                cand += [(0, off), (0, -off), (off, 0), (-off, 0),
                         (off * 0.7, off * 0.7), (-off * 0.7, off * 0.7),
                         (off * 0.7, -off * 0.7), (-off * 0.7, -off * 0.7)]
            for (dx, dy) in cand:
                q = (p['x'] + dx, p['y'] + dy)
                if BARRIER_Y0 - 1 <= q[1] <= BARRIER_Y1 + 1:
                    continue
                wdt, clr = rules_for(net)
                wdt = min(wdt, 0.4)
                if not obs.clear(p['layer'], (p['x'], p['y']), q, wdt, net, clr):
                    continue
                if not obs.hole_ok(q[0], q[1], vd / 2.0, net, clr):
                    continue
                add_track(board, (p['x'], p['y']), q, p['layer'], wdt,
                          p['code'])
                add_via(board, q, p['code'], vd, vdr)
                obs.add_hole(q[0], q[1], vd / 2.0, net)
                obs.add_seg(p['layer'], (p['x'], p['y']), q, wdt, net)
                obs.add_rect(p['layer'], q[0], q[1], vd + 0.1, vd + 0.1, net)
                n_via += 1
                n_trk += 1
                colocado = True
                break
            if not colocado:
                n_fail += 1
                fallidas.append('%s.%s (%s)' % (p['ref'], p['num'], net))
    print('Pasada 1  vias a plano ............ %4d colocadas, %d sin sitio'
          % (n_via, n_fail))

    # ============================================================
    # PASADAS 2 y 3: redes con pista
    # ============================================================
    if os.environ.get('ROUTE_SIGNALS', '0') != '1':
        print('Pasadas 2-3  OMITIDAS (exporta ROUTE_SIGNALS=1 para forzarlas)')
        print('   El ruteador L/Z introducia cortocircuitos en la zona LV.')
        print('   Las senales se rutean con el ruteador interactivo de KiCad.')
        zl = pcbnew.ZONES()
        for z in board.Zones():
            if not z.GetIsRuleArea():
                zl.append(z)
        pcbnew.ZONE_FILLER(board).Fill(zl)
        pcbnew.SaveBoard(PCB, board)
        b2 = pcbnew.LoadBoard(PCB)
        b2.BuildConnectivity()
        print('Pistas anadidas: %d   Vias: %d' % (n_trk, n_via))
        print('Ratsnest restante: %d'
              % b2.GetConnectivity().GetUnconnectedCount(True))
        return 0

    # potencia primero: ocupa el sitio bueno antes que las senales
    def prio(net):
        w, c = rules_for(net)
        return (-c, -w)

    objetivo = [n for n in padsbynet
                if n not in ZONE_NETS and len(padsbynet[n]) >= 2]
    objetivo.sort(key=prio)

    rut, parcial = 0, 0
    for net in objetivo:
        pads = padsbynet[net]
        pts = [(p['x'], p['y']) for p in pads]
        width, clr = rules_for(net)
        code = pads[0]['code']
        hecho_net = 0
        for (a, b) in mst(pts):
            pa, pb = pts[a], pts[b]
            if crosses_barrier(pa, pb):
                continue
            la = pads[a]['layer']
            lb = pads[b]['layer']
            ok = False
            # candidatos: recto, L (dos sentidos), Z (con 3 offsets)
            cands = [[pa, pb],
                     [pa, (pb[0], pa[1]), pb],
                     [pa, (pa[0], pb[1]), pb]]
            for frac in (0.2, 0.35, 0.5, 0.65, 0.8):
                xm = pa[0] + (pb[0] - pa[0]) * frac
                ym = pa[1] + (pb[1] - pa[1]) * frac
                cands.append([pa, (xm, pa[1]), (xm, pb[1]), pb])
                cands.append([pa, (pa[0], ym), (pb[0], ym), pb])
            capas = [la] if la == lb else [la, lb]
            otras = [L for L in SIG_LAYERS if L not in capas]
            for layer in capas + otras:
                for path in cands:
                    if any(crosses_barrier(path[i], path[i + 1])
                           for i in range(len(path) - 1)):
                        continue
                    if all(obs.clear(layer, path[i], path[i + 1], width,
                                     net, clr)
                           for i in range(len(path) - 1)):
                        for i in range(len(path) - 1):
                            if math.dist(path[i], path[i + 1]) < 1e-6:
                                continue
                            add_track(board, path[i], path[i + 1], layer,
                                      width, code)
                            obs.add_seg(layer, path[i], path[i + 1], width,
                                        net)
                            n_trk += 1
                        if layer != la:
                            add_via(board, pa, code)
                        if layer != lb:
                            add_via(board, pb, code)
                        ok = True
                        break
                if ok:
                    break
            if ok:
                hecho_net += 1
        total_edges = max(1, len(pts) - 1)
        if hecho_net == total_edges:
            rut += 1
        elif hecho_net:
            parcial += 1
        else:
            fallidas.append(net)

    print('Pasadas 2-3  redes ................ %4d completas, %d parciales, '
          '%d sin rutear' % (rut, parcial, len(objetivo) - rut - parcial))
    print('Pistas anadidas: %d   Vias: %d' % (n_trk, n_via))

    # --- rellenar zonas de nuevo (las pistas cambian el vertido) ---
    zl = pcbnew.ZONES()
    for z in board.Zones():
        if not z.GetIsRuleArea():
            zl.append(z)
    pcbnew.ZONE_FILLER(board).Fill(zl)

    pcbnew.SaveBoard(PCB, board)
    board2 = pcbnew.LoadBoard(PCB)
    board2.BuildConnectivity()
    print('Ratsnest restante: %d'
          % board2.GetConnectivity().GetUnconnectedCount(True))
    if fallidas:
        print('Sin rutear (%d): %s%s'
              % (len(fallidas), ', '.join(fallidas[:12]),
                 ' ...' if len(fallidas) > 12 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
