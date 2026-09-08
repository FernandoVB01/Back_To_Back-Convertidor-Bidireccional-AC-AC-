# Convertidor Back-to-Back (AFE + Inversor) — 15 kVA / 800 V

Convertidor trifásico regenerativo completo: rectificador activo (AFE) +
inversor con control vectorial, bus DC común, control en **STM32G474** y
telemetría en **ESP32-S3**. Diseño en KiCad 9, validado por simulación.

**Punto de diseño:** 15 kVA · 400 V_LL · 60 Hz · V_dc ≤ 800 V · f_sw 16 kHz.

---

## Cómo lo ejecuto

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Eso hace **todo** en orden. Tarda unos minutos (lo más lento es LTspice).

Por etapas, si solo quieres una parte:

```powershell
.\run.ps1 check    # comprobar que están las herramientas (empieza por aquí)
.\run.ps1 sim      # simulación y validación   -> docs/INFORME_VALIDACION.md
.\run.ps1 spice    # LTspice                   -> sim/out/06..08*.png
.\run.ps1 fw       # firmware: genera b2b_config.h
.\run.ps1 kicad    # esquemático + PCB + render 3D
.\run.ps1 mech     # gabinete
```

### ⚠ Lo único que hay que entender: hay DOS Python

No son intercambiables. `run.ps1` elige el correcto en cada paso, pero si
lanzas algo a mano tienes que saberlo:

| Python | Dónde | Para qué |
|---|---|---|
| **El de KiCad** | `C:\Program Files\KiCad\9.0\bin\python.exe` | `tools/gen_schematic.py`, `gen_pcb.py`, `check_conn.py`, `restore_pro.py` — necesitan el módulo `pcbnew` |
| **Anaconda** | `python` (en el PATH) | `sim/`, `spice/`, `mech/`, `fw/`, `tools/gen_kicad_sim.py`, `verify_kicad_sim.py` — necesitan numpy/scipy/matplotlib |

Si un script falla con `ModuleNotFoundError: pcbnew` o
`ModuleNotFoundError: numpy`, es que lo has lanzado con el Python equivocado.

### Requisitos

- **KiCad 9.0** en `C:\Program Files\KiCad\9.0` (trae su Python y `kicad-cli`)
- **Anaconda** con numpy, scipy, matplotlib
- **LTspice** (ADI) en `%LOCALAPPDATA%\Programs\ADI\LTspice\` — solo para la
  etapa `spice`; el resto funciona sin él

---

## Qué hay en cada carpeta

```
kicad/      PROYECTO KICAD  <- abre b2b_converter.kicad_pro
  sch/        11 subhojas del esquemático
  sim/        esquemas simulables con ngspice (Inspeccionar > Simulador)
sim/        simulación y validación en Python (la fuente de la verdad)
spice/      netlists de LTspice (se abren también a mano en LTspice)
fw/         firmware del STM32G474
mech/       gabinete industrial
tools/      los generadores (nada de esto se editó a mano)
docs/       toda la documentación
render/     renders 3D de la PCB
export/     PDF de los planos, informes de ERC y DRC
```

## Por dónde empezar a leer

| Documento | Qué te cuenta |
|---|---|
| [docs/INFORME_VALIDACION.md](docs/INFORME_VALIDACION.md) | Las 31 comprobaciones del diseño, con los números |
| [docs/ESTADO_KICAD.md](docs/ESTADO_KICAD.md) | Qué está hecho en la PCB y qué falta |
| [docs/BOM_INDUSTRIAL.md](docs/BOM_INDUSTRIAL.md) | Componentes con marca y referencia real |
| [docs/COMO_SIMULAR.md](docs/COMO_SIMULAR.md) | **Cómo lanzar las 4 simulaciones y qué mirar en cada una** |
| [docs/RUTEO_ESTADO.md](docs/RUTEO_ESTADO.md) | Estado del ruteo y los bugs que destapó |
| [docs/SIMULAR_FIRMWARE.md](docs/SIMULAR_FIRMWARE.md) | Por qué Proteus no sirve aquí y qué se hace en su lugar |
| [docs/00_MASTER_PLAN.md](docs/00_MASTER_PLAN.md) | Arquitectura y las 6 fases del proyecto |
| [docs/KICAD_PCB_FLOORPLAN.md](docs/KICAD_PCB_FLOORPLAN.md) | Stackup, floorplan y orden de ruteo |

---

## La regla de oro del proyecto

**Todo sale de `sim/b2b_params.py`.** Ese archivo es la única fuente de
parámetros:

```
sim/b2b_params.py
   ├──► sim/run_all.py        ──► validación (31 comprobaciones)
   ├──► spice/gen_spice.py    ──► SPICE
   ├──► fw/config/gen_config.py ──► b2b_config.h ──► firmware C
   │                                     └──► control_ref.py (verificación)
   ├──► tools/gen_schematic.py ──► esquemático KiCad
   └──► mech/gen_gabinete.py  ──► gabinete
```

Si cambias un parámetro ahí y ejecutas `.\run.ps1`, se regenera todo y nada
se desincroniza. **No edites a mano el esquemático ni `b2b_config.h`**: los
sobrescribe el generador.

## Estado

- Esquemático: **227 componentes**, 0 cables sueltos. Bus DC corregido:
  `DC_P` pasó de 4 a **22 pads** (los rieles solo conectaban la última rama)
- PCB: 340×240 mm, 4 capas, footprints colocados y zonas rellenadas
- **Ruteo de pistas: 0 %** — ver [docs/RUTEO_ESTADO.md](docs/RUTEO_ESTADO.md): el auto-ruteador propio se descartó por introducir cortocircuitos
- Validación: **31/31 comprobaciones OK**
- Firmware: matemática de control y configuración listas; falta la capa HAL
