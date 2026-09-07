"""
kisch.py - Generador de esquematicos KiCad 9 (.kicad_sch) por script.

Estrategia:
  - Se PARSEAN los simbolos reales de las librerias instaladas de KiCad, de modo
    que las posiciones de pin son exactas y los graficos son los oficiales.
  - Se emite el .kicad_sch en formato v20250114 (KiCad 9).
  - Las conexiones entre hojas se hacen con GLOBAL LABELS (no requieren sheet
    pins en la raiz -> mucho mas simple y ERC-limpio).

Uso:
    lib = SymbolCache(r"C:\\Program Files\\KiCad\\9.0\\share\\kicad\\symbols")
    sch = Schematic("01 - AC Input", lib, project="b2b_converter",
                    root_uuid=ROOT, sheet_uuid=SH01)
    r = sch.place("Device:R", "R1", "2R2", 100, 100, footprint="...")
    sch.wire(r.pin("1"), (100, 90))
    sch.glabel("GRID_L1", 100, 90, shape="bidirectional")
    sch.save("out/ac_input.kicad_sch")
"""

import math
import os
import re
import uuid as _uuid

# --------------------------------------------------------------------------
# 1. S-expression parser / serializer
# --------------------------------------------------------------------------


class Sym(str):
    """Atomo s-expr SIN comillas (p.ej. yes, no, line, passive)."""
    __slots__ = ()


_TOKEN = re.compile(r'''\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))''')


def parse(text):
    """Parsea texto s-expr y devuelve el primer nodo (lista anidada)."""
    pos = 0
    stack = []
    root = None
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):                      # (
            new = []
            if stack:
                stack[-1].append(new)
            stack.append(new)
        elif m.group(2):                    # )
            done = stack.pop()
            if not stack:
                root = done
                break
        elif m.group(3) is not None:        # "string"
            s = (m.group(3).replace('\\n', '\n')
                 .replace('\\"', '"').replace('\\\\', '\\'))
            stack[-1].append(s)
        else:                               # bare atom
            stack[-1].append(Sym(m.group(4)))
    return root


def _esc(s):
    return (s.replace('\\', '\\\\')
             .replace('"', '\\"')
             .replace('\n', '\\n'))


def dumps(node, level=0):
    """Serializa un nodo a texto con indentacion por tabuladores."""
    pad = '\t' * level
    if isinstance(node, Sym):
        return node
    if isinstance(node, str):
        return '"%s"' % _esc(node)
    if isinstance(node, (int, float)):
        return _fmtnum(node)
    # lista
    if not node:
        return '()'
    head = node[0]
    # si todos los hijos son atomos -> una sola linea
    if all(not isinstance(c, list) for c in node):
        return '(' + ' '.join(dumps(c) for c in node) + ')'
    out = ['(' + dumps(head)]
    for child in node[1:]:
        if isinstance(child, list):
            out.append('\n' + pad + '\t' + dumps(child, level + 1))
        else:
            out.append(' ' + dumps(child))
    out.append('\n' + pad + ')')
    return ''.join(out)


def _fmtnum(v):
    if isinstance(v, int):
        return str(v)
    r = round(float(v), 4)
    if r == int(r):
        return str(int(r))
    return ('%.4f' % r).rstrip('0').rstrip('.')


def N(v):
    """Numero como atomo bare."""
    return Sym(_fmtnum(v))


def uid():
    return str(_uuid.uuid4())


# --------------------------------------------------------------------------
# 2. Carga de simbolos desde las librerias instaladas
# --------------------------------------------------------------------------


def _find(node, tag):
    for c in node:
        if isinstance(c, list) and c and c[0] == tag:
            return c
    return None


def _findall(node, tag):
    return [c for c in node
            if isinstance(c, list) and c and c[0] == tag]


class SymbolCache:
    """Carga y cachea definiciones de simbolo de las librerias .kicad_sym."""

    def __init__(self, *libdirs):
        self.libdirs = [d for d in libdirs if os.path.isdir(d)]
        self._files = {}    # libname -> parsed lib
        self._syms = {}     # "Lib:Name" -> definicion aplanada

    def _lib(self, libname):
        if libname not in self._files:
            path = None
            for d in self.libdirs:
                p = os.path.join(d, libname + '.kicad_sym')
                if os.path.isfile(p):
                    path = p
                    break
            if path is None:
                raise FileNotFoundError('libreria no encontrada: ' + libname)
            with open(path, 'r', encoding='utf-8') as f:
                self._files[libname] = parse(f.read())
        return self._files[libname]

    def _raw(self, libname, symname):
        lib = self._lib(libname)
        for s in _findall(lib, Sym('symbol')):
            if len(s) > 1 and s[1] == symname:
                return s
        raise KeyError('simbolo %s no existe en %s' % (symname, libname))

    def get(self, lib_id):
        """Devuelve la definicion del simbolo lista para lib_symbols."""
        if lib_id in self._syms:
            return self._syms[lib_id]
        libname, symname = lib_id.split(':', 1)
        raw = self._raw(libname, symname)
        flat = self._flatten(libname, symname, raw)
        flat = [x for x in flat]
        flat[1] = lib_id                      # renombrar a "Lib:Name"
        self._syms[lib_id] = flat
        return flat

    def _flatten(self, libname, symname, raw):
        """Resuelve (extends "base") copiando graficos/pines del padre."""
        ext = _find(raw, Sym('extends'))
        if ext is None:
            return raw
        base = self._raw(libname, ext[1])
        base = self._flatten(libname, ext[1], base)
        # partir de la base, sustituir propiedades por las del hijo
        out = [base[0], symname]
        child_props = {p[1]: p for p in _findall(raw, Sym('property'))}
        seen = set()
        for c in base[2:]:
            if isinstance(c, list) and c[0] == Sym('property'):
                name = c[1]
                if name in child_props:
                    out.append(child_props[name])
                    seen.add(name)
                else:
                    out.append(c)
            elif isinstance(c, list) and c[0] == Sym('extends'):
                continue
            elif isinstance(c, list) and c[0] == Sym('symbol'):
                # renombrar sub-simbolos: BASE_0_1 -> CHILD_0_1
                sub = [x for x in c]
                sub[1] = symname + c[1][len(ext[1]):]
                out.append(sub)
            else:
                out.append(c)
        for name, p in child_props.items():
            if name not in seen:
                out.append(p)
        return out

    def pins(self, lib_id, unit=1):
        """dict numero_pin -> (x, y, angulo) en coordenadas de libreria."""
        d = self.get(lib_id)
        res = {}
        for sub in _findall(d, Sym('symbol')):
            m = re.search(r'_(\d+)_(\d+)$', sub[1])
            u = int(m.group(1)) if m else 0
            if u not in (0, unit):
                continue
            for p in _findall(sub, Sym('pin')):
                at = _find(p, Sym('at'))
                num = _find(p, Sym('number'))
                if at is None or num is None:
                    continue
                res[str(num[1])] = (float(at[1]), float(at[2]),
                                    float(at[3]) if len(at) > 3 else 0.0)
        return res

    def units(self, lib_id):
        """Numero de unidades del simbolo (1 si no es multi-unit)."""
        d = self.get(lib_id)
        mx = 1
        for sub in _findall(d, Sym('symbol')):
            m = re.search(r'_(\d+)_(\d+)$', sub[1])
            if m:
                mx = max(mx, int(m.group(1)))
        return mx

    def prop(self, lib_id, name, default=''):
        d = self.get(lib_id)
        for p in _findall(d, Sym('property')):
            if p[1] == name:
                return p[2]
        return default


# --------------------------------------------------------------------------
# 3. Instancia de simbolo colocada
# --------------------------------------------------------------------------


GRID = 1.27


def snap(pt):
    """Identidad. El snap rompia la union cable-pin en simbolos cuyos pines
    no caen en multiplos de 1.27 mm; la conectividad exacta manda sobre el
    aviso cosmetico de rejilla."""
    return (round(float(pt[0]), 4), round(float(pt[1]), 4))


class Placed:
    def __init__(self, sch, lib_id, ref, value, x, y, rot, unit, mirror):
        self.sch = sch
        self.lib_id = lib_id
        self.ref = ref
        self.value = value
        self.x = round(float(x), 4)
        self.y = round(float(y), 4)
        self.rot = int(rot) % 360
        self.unit = unit
        self.mirror = mirror
        self.uuid = uid()

    def pin(self, number):
        """Coordenada de esquema del punto de conexion de un pin."""
        pins = self.sch.lib.pins(self.lib_id, self.unit)
        key = str(number)
        if key not in pins:
            raise KeyError('%s (%s) no tiene pin %s. Tiene: %s'
                           % (self.ref, self.lib_id, key,
                              ','.join(sorted(pins))))
        px, py, _ = pins[key]
        if self.mirror == 'x':
            py = -py
        elif self.mirror == 'y':
            px = -px
        a = math.radians(self.rot)
        ca, sa = math.cos(a), math.sin(a)
        rx = px * ca - py * sa
        ry = px * sa + py * ca
        # libreria Y-arriba  ->  esquema Y-abajo
        return (round(self.x + rx, 4), round(self.y - ry, 4))

    def pinnames(self):
        return sorted(self.sch.lib.pins(self.lib_id, self.unit))


# --------------------------------------------------------------------------
# 4. Constructor de hoja de esquema
# --------------------------------------------------------------------------

_SHAPES = {'input', 'output', 'bidirectional', 'tri_state', 'passive'}


class Schematic:
    def __init__(self, title, lib, project, root_uuid, sheet_uuid=None,
                 paper='A2', rev='A', company='SistemasControl_PAPUH',
                 comments=()):
        self.title = title
        self.lib = lib
        self.project = project
        self.root_uuid = root_uuid
        self.sheet_uuid = sheet_uuid      # None => es la hoja raiz
        self.paper = paper
        self.rev = rev
        self.company = company
        self.comments = list(comments)
        # En una hoja RAIZ, su propio uuid TIENE que ser el mismo que la raiz
        # de las rutas de (instances). Si no, KiCad considera el esquema no
        # anotado y no asigna nombres de red: la netlist sale con _NO_NET_.
        self.uuid = root_uuid if sheet_uuid is None else uid()
        self.items = []          # nodos ya serializables
        self.placed = []         # Placed
        self.used_libs = []      # lib_ids en orden
        self._nc = []

    # ---- colocacion -----------------------------------------------------
    def place(self, lib_id, ref, value, x, y, rot=0, unit=1, mirror=None,
              footprint='', datasheet='~', hide_value=False, fields=None):
        if lib_id not in self.used_libs:
            self.lib.get(lib_id)          # valida que exista
            self.used_libs.append(lib_id)
        p = Placed(self, lib_id, ref, value, x, y, rot, unit, mirror)
        p.footprint = footprint
        p.datasheet = datasheet
        p.hide_value = hide_value
        p.fields = fields or {}
        self.placed.append(p)
        return p

    # ---- conectividad ---------------------------------------------------
    def wire(self, a, b, first='v'):
        """Cable entre dos puntos. Si no estan alineados, rutea en L."""
        ax, ay = snap(a)
        bx, by = snap(b)
        if abs(ax - bx) < 1e-6 and abs(ay - by) < 1e-6:
            return
        if abs(ax - bx) > 1e-6 and abs(ay - by) > 1e-6:
            mid = (ax, by) if first == 'v' else (bx, ay)
            self._seg(a, mid)
            self._seg(mid, b)
            return
        self._seg(a, b)

    def _seg(self, a, b):
        ax, ay = a
        bx, by = b
        if abs(ax - bx) < 1e-6 and abs(ay - by) < 1e-6:
            return
        key = tuple(sorted([(round(ax, 3), round(ay, 3)),
                            (round(bx, 3), round(by, 3))]))
        if not hasattr(self, '_segs'):
            self._segs = set()
        if key in self._segs:
            return                       # segmento duplicado: se descarta
        self._segs.add(key)
        self.items.append([
            Sym('wire'),
            [Sym('pts'), [Sym('xy'), N(ax), N(ay)], [Sym('xy'), N(bx), N(by)]],
            [Sym('stroke'), [Sym('width'), N(0)], [Sym('type'), Sym('default')]],
            [Sym('uuid'), uid()],
        ])

    def wire_l(self, a, b, first='h'):
        """Cable en L entre dos puntos."""
        ax, ay = a
        bx, by = b
        mid = (bx, ay) if first == 'h' else (ax, by)
        self.wire(a, mid)
        self.wire(mid, b)
        return mid

    def bus_h(self, y, x0, x1):
        self.wire((x0, y), (x1, y))

    def junction(self, pt):
        pt = snap(pt)
        self.items.append([
            Sym('junction'), [Sym('at'), N(pt[0]), N(pt[1])],
            [Sym('diameter'), N(0)],
            [Sym('color'), N(0), N(0), N(0), N(0)],
            [Sym('uuid'), uid()],
        ])

    def nc(self, pt):
        """Marca no-connect (silencia ERC en pines sin usar)."""
        pt = snap(pt)
        self.items.append([
            Sym('no_connect'), [Sym('at'), N(pt[0]), N(pt[1])],
            [Sym('uuid'), uid()],
        ])

    # ---- etiquetas ------------------------------------------------------
    def label(self, name, pt, rot=0, size=1.27):
        pt = snap(pt)
        self.items.append([
            Sym('label'), name,
            [Sym('at'), N(pt[0]), N(pt[1]), N(rot)],
            [Sym('fields_autoplaced'), Sym('yes')],
            [Sym('effects'),
             [Sym('font'), [Sym('size'), N(size), N(size)]],
             [Sym('justify'), Sym('left'), Sym('bottom')]],
            [Sym('uuid'), uid()],
        ])

    def glabel(self, name, pt, rot=0, shape='bidirectional', size=1.27):
        """Global label: conecta entre hojas sin necesidad de sheet pins."""
        if shape not in _SHAPES:
            raise ValueError('shape invalido: ' + shape)
        pt = snap(pt)
        just = Sym('left') if rot in (0, 90) else Sym('right')
        self.items.append([
            Sym('global_label'), name,
            [Sym('shape'), Sym(shape)],
            [Sym('at'), N(pt[0]), N(pt[1]), N(rot)],
            [Sym('fields_autoplaced'), Sym('yes')],
            [Sym('effects'),
             [Sym('font'), [Sym('size'), N(size), N(size)]],
             [Sym('justify'), just]],
            [Sym('uuid'), uid()],
            [Sym('property'), 'Intersheetrefs', '${INTERSHEET_REFS}',
             [Sym('at'), N(pt[0]), N(pt[1]), N(0)],
             [Sym('effects'), [Sym('font'), [Sym('size'), N(1.27), N(1.27)]],
              [Sym('hide'), Sym('yes')]]],
        ])

    def text(self, body, pt, size=1.6, rot=0):
        self.items.append([
            Sym('text'), body,
            [Sym('exclude_from_sim'), Sym('no')],
            [Sym('at'), N(pt[0]), N(pt[1]), N(rot)],
            [Sym('effects'),
             [Sym('font'), [Sym('size'), N(size), N(size)]],
             [Sym('justify'), Sym('left'), Sym('top')]],
            [Sym('uuid'), uid()],
        ])

    def box(self, x0, y0, x1, y1, note=None, size=1.6):
        self.items.append([
            Sym('rectangle'),
            [Sym('start'), N(x0), N(y0)],
            [Sym('end'), N(x1), N(y1)],
            [Sym('stroke'), [Sym('width'), N(0.2)], [Sym('type'), Sym('dash')]],
            [Sym('fill'), [Sym('type'), Sym('none')]],
            [Sym('uuid'), uid()],
        ])
        if note:
            self.text(note, (x0 + 1.27, y0 + 1.27), size=size)

    # ---- hojas jerarquicas (solo en la raiz) ----------------------------
    def sheet(self, name, filename, x, y, w=75, h=26, sheet_uuid=None,
              page='2'):
        su = sheet_uuid or uid()
        self.items.append([
            Sym('sheet'),
            [Sym('at'), N(x), N(y)],
            [Sym('size'), N(w), N(h)],
            [Sym('fields_autoplaced'), Sym('yes')],
            [Sym('stroke'), [Sym('width'), N(0.1524)],
             [Sym('type'), Sym('solid')]],
            [Sym('fill'), [Sym('color'), N(0), N(0), N(0), N(0)]],
            [Sym('uuid'), su],
            [Sym('property'), 'Sheetname', name,
             [Sym('at'), N(x), N(y - 0.7), N(0)],
             [Sym('effects'), [Sym('font'), [Sym('size'), N(1.27), N(1.27)]],
              [Sym('justify'), Sym('left'), Sym('bottom')]]],
            [Sym('property'), 'Sheetfile', filename,
             [Sym('at'), N(x), N(y + h + 0.7), N(0)],
             [Sym('effects'), [Sym('font'), [Sym('size'), N(1.27), N(1.27)]],
              [Sym('justify'), Sym('left'), Sym('top')]]],
            [Sym('instances'),
             [Sym('project'), self.project,
              [Sym('path'), '/' + self.root_uuid, [Sym('page'), page]]]],
        ])
        return su

    # ---- helpers de alimentacion ---------------------------------------
    def power(self, netname, pt, rot=0, ref=None):
        """Coloca un simbolo de la libreria 'power' con su pin en pt."""
        lib_id = 'power:' + netname
        if lib_id not in self.used_libs:
            self.lib.get(lib_id)
            self.used_libs.append(lib_id)
        pins = self.lib.pins(lib_id, 1)
        pnum = sorted(pins)[0]
        px, py, _ = pins[pnum]
        a = math.radians(rot)
        ca, sa = math.cos(a), math.sin(a)
        rx = px * ca - py * sa
        ry = px * sa + py * ca
        pt = snap(pt)
        ox = round(pt[0] - rx, 4)
        oy = round(pt[1] + ry, 4)
        self._pwr_n = getattr(self, '_pwr_n', 0) + 1
        p = Placed(self, lib_id, ref or ('#PWR%03d' % self._pwr_n),
                   netname, ox, oy, rot, 1, None)
        p.footprint = ''
        p.datasheet = ''
        p.hide_value = True
        p.fields = {}
        p.is_power = True
        self.placed.append(p)
        return p

    # ---- serializacion --------------------------------------------------
    def _symbol_instance(self, p):
        is_pwr = getattr(p, 'is_power', False)
        # posicion de los campos de texto
        fx, fy = p.x, p.y - 5.08
        vx, vy = p.x, p.y + 5.08
        props = [
            ('Reference', p.ref, fx, fy, False),
            ('Value', p.value, vx, vy, p.hide_value),
            ('Footprint', p.footprint, p.x, p.y, True),
            ('Datasheet', p.datasheet, p.x, p.y, True),
            ('Description', '', p.x, p.y, True),
        ]
        for k, v in p.fields.items():
            props.append((k, v, p.x, p.y, True))
        node = [
            Sym('symbol'),
            [Sym('lib_id'), p.lib_id],
            [Sym('at'), N(p.x), N(p.y), N(p.rot)],
        ]
        if p.mirror:
            node.append([Sym('mirror'), Sym(p.mirror)])
        node += [
            [Sym('unit'), N(p.unit)],
            [Sym('exclude_from_sim'), Sym('no')],
            [Sym('in_bom'), Sym('no') if is_pwr else Sym('yes')],
            [Sym('on_board'), Sym('no') if is_pwr else Sym('yes')],
            [Sym('dnp'), Sym('no')],
            [Sym('fields_autoplaced'), Sym('yes')],
            [Sym('uuid'), p.uuid],
        ]
        for name, val, x, y, hide in props:
            eff = [Sym('effects'),
                   [Sym('font'), [Sym('size'), N(1.27), N(1.27)]]]
            if hide:
                eff.append([Sym('hide'), Sym('yes')])
            node.append([Sym('property'), name, val,
                         [Sym('at'), N(x), N(y), N(0)], eff])
        for pn in sorted(self.lib.pins(p.lib_id, p.unit)):
            node.append([Sym('pin'), str(pn), [Sym('uuid'), uid()]])
        path = '/' + self.root_uuid
        if self.sheet_uuid:
            path += '/' + self.sheet_uuid
        node.append([Sym('instances'),
                     [Sym('project'), self.project,
                      [Sym('path'), path,
                       [Sym('reference'), p.ref], [Sym('unit'), N(p.unit)]]]])
        return node

    def build(self):
        tb = [Sym('title_block'),
              [Sym('title'), self.title],
              [Sym('date'), '2026-09-05'],
              [Sym('rev'), self.rev],
              [Sym('company'), self.company]]
        for i, c in enumerate(self.comments[:4], start=1):
            tb.append([Sym('comment'), N(i), c])

        libsyms = [Sym('lib_symbols')]
        for lid in self.used_libs:
            libsyms.append(self.lib.get(lid))

        root = [
            Sym('kicad_sch'),
            [Sym('version'), Sym('20250114')],
            [Sym('generator'), 'kisch.py'],
            [Sym('generator_version'), '9.0'],
            [Sym('uuid'), self.uuid],
            [Sym('paper'), self.paper],
            tb,
            libsyms,
        ]
        root += self.items
        for p in self.placed:
            root.append(self._symbol_instance(p))
        root.append([Sym('sheet_instances'),
                     [Sym('path'), '/', [Sym('page'), '1']]])
        root.append([Sym('embedded_fonts'), Sym('no')])
        return root

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(dumps(self.build()))
            f.write('\n')
        return path


# --------------------------------------------------------------------------
# 5. Validacion simbolo <-> footprint
# --------------------------------------------------------------------------

_FPCACHE = {}


def fp_pads(fpdir, fpid):
    """Numero de pads unicos de un footprint instalado. None si no existe."""
    if fpid in _FPCACHE:
        return _FPCACHE[fpid]
    res = None
    if ':' in fpid:
        libname, name = fpid.split(':', 1)
        path = os.path.join(fpdir, libname + '.pretty', name + '.kicad_mod')
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
            nums = set(re.findall(r'\(pad\s+"([^"]+)"', txt))
            nums.discard('')
            res = len(nums)
    _FPCACHE[fpid] = res
    return res


def check_schematic(sch, fpdir):
    """Comprueba footprints inexistentes y desajuste de pines/pads."""
    problems = []
    seen = {}
    for p in sch.placed:
        if getattr(p, 'is_power', False) or not p.footprint:
            continue
        seen.setdefault((p.lib_id, p.footprint), []).append(p.ref)
    for (lib_id, fpid), refs in sorted(seen.items()):
        pads = fp_pads(fpdir, fpid)
        if pads is None:
            problems.append('FOOTPRINT INEXISTENTE  %-52s  (%s)'
                            % (fpid, ','.join(refs[:4])))
            continue
        units = sch.lib.units(lib_id)
        npins = sum(len(sch.lib.pins(lib_id, u)) for u in range(1, units + 1))
        if units > 1:
            npins = len(set(
                k for u in range(1, units + 1)
                for k in sch.lib.pins(lib_id, u)))
        if npins != pads:
            problems.append('PINES != PADS  %-34s %2d pin  vs  %-46s %2d pad'
                            % (lib_id, npins, fpid, pads))
    return problems
