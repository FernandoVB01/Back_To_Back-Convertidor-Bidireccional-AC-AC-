"""
run_all.py - Ejecuta toda la validacion y emite docs/INFORME_VALIDACION.md

    python sim/run_all.py
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import b2b_params as P            # noqa: E402
import sim_design as D            # noqa: E402
import sim_timedomain as T        # noqa: E402

DOC = os.path.join(ROOT, 'docs', 'INFORME_VALIDACION.md')


def fmt(v):
    if isinstance(v, tuple):
        return '%.4g .. %.4g' % v
    if isinstance(v, float):
        if abs(v) >= 1000 or (abs(v) < 0.01 and v != 0):
            return '%.4g' % v
        return '%.3f' % v
    return str(v)


def tabla(checks):
    out = ['| | Comprobacion | Valor | Limite | Nota |',
           '|:-:|---|---:|---:|---|']
    for c in checks:
        mark = 'OK' if c['ok'] else 'FALLA'
        out.append('| **%s** | %s | %s %s | %s | %s |'
                   % (mark, c['name'], fmt(c['value']), c['unit'],
                      fmt(c['limit']), c.get('note', '')))
    return '\n'.join(out)


def main():
    t0 = time.time()
    print(P.resumen())
    print()

    print('[1/5] Filtro LCL ...')
    c_lcl = D.analiza_lcl()

    print('[2/5] Lazos de control ...')
    c_loop, gains = D.analiza_lazos()

    print('[3/5] Termico ...')
    c_th, th = D.analiza_termico()
    c_th_alt, th_alt = D.analiza_termico(P.RDSON_ALT_25, P.SIC_ALT_NAME)

    print('[4/5] Precarga ...')
    c_pc = D.analiza_precarga()

    print('[5/5] Simulacion temporal del convertidor completo ...')
    rec = T.run()
    c_td = T.evalua(rec)
    T.grafica(rec)

    grupos = [('1. Filtro LCL y calidad de red', c_lcl),
              ('2. Estabilidad de los lazos de control', c_loop),
              ('3. Termico (C3M0075120K, el de la libreria)', c_th),
              ('3b. Termico (C3M0040120K, el recomendado)', c_th_alt),
              ('4. Precarga del bus', c_pc),
              ('5. Simulacion temporal + frenado regenerativo', c_td)]

    total = sum(len(g[1]) for g in grupos)
    fails = [c for _, g in grupos for c in g if not c['ok']]

    body = []
    body.append('# Informe de validacion del convertidor back-to-back\n')
    body.append('> Generado por `sim/run_all.py`. No editar a mano: '
                'cambia `sim/b2b_params.py` y vuelve a ejecutarlo.\n')
    body.append('```\n%s\n```\n' % P.resumen())
    body.append('## Resultado global\n')
    body.append('**%d de %d comprobaciones OK.**%s\n'
                % (total - len(fails), total,
                   '' if not fails else '  Fallan: '
                   + ', '.join(c['name'] for c in fails)))
    for titulo, checks in grupos:
        body.append('\n## %s\n' % titulo)
        body.append(tabla(checks))
        body.append('')

    body.append('\n## Ganancias resultantes (llevar al firmware)\n')
    body.append('```c')
    body.append('/* Lazo de corriente del AFE y del inversor, %.0f kHz */'
                % (P.F_SW / 1000))
    body.append('#define KP_I     %.6ff' % gains['Kp_i'])
    body.append('#define KI_I     %.6ff' % gains['Ki_i'])
    body.append('/* Lazo externo de tension de bus */')
    body.append('#define KP_VDC   %.6ff' % gains['Kp_v'])
    body.append('#define KI_VDC   %.6ff' % gains['Ki_v'])
    body.append('#define TS       %.9ff  /* %.2f us */'
                % (P.T_S, P.T_S * 1e6))
    body.append('```\n')

    body.append('\n## Figuras\n')
    for f, cap in [('01_lcl_bode.png', 'Respuesta del filtro LCL: resonancia, '
                    'amortiguamiento y atenuacion a f_sw.'),
                   ('02_lazos_bode.png', 'Bode de lazo abierto de los lazos '
                    'de corriente y de bus, con el retardo de 1.5 Ts.'),
                   ('03_precarga.png', 'Transitorio de precarga: tension de '
                    'bus e inrush.'),
                   ('04_b2b_temporal.png', 'Simulacion completa: bus, motor, '
                    'flujo de potencia y corriente dq de red.'),
                   ('05_fase_regeneracion.png', 'Prueba del frenado '
                    'regenerativo: la corriente de red se invierte.')]:
        body.append('### %s\n' % cap)
        body.append('![%s](../sim/out/%s)\n' % (cap, f))

    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    with open(DOC, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(body))

    print()
    for titulo, checks in grupos:
        print('--- %s' % titulo)
        for c in checks:
            print('  [%-5s] %-46s %10s %s'
                  % ('OK' if c['ok'] else 'FALLA', c['name'],
                     fmt(c['value']), c['unit']))
    print('\n%d/%d OK   (%.1f s)' % (total - len(fails), total,
                                     time.time() - t0))
    print('Informe: %s' % os.path.relpath(DOC, ROOT))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
