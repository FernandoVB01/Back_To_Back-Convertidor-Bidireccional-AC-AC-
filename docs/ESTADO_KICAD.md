# Estado del proyecto KiCad — qué está hecho y qué falta

> Generado por scripts. Todo se reconstruye con **un comando**:
> `.\tools\build_all.ps1`

---

## 1. Cómo está construido

El esquemático **no** se dibujó a mano: lo genera `tools/gen_schematic.py`,
que **parsea las librerías de símbolos reales de tu KiCad 9** y copia las
definiciones oficiales dentro de cada `.kicad_sch`. Por eso las posiciones de
pin son exactas y los gráficos son los de la librería estándar.

```
tools/
  kisch.py          parser/serializador de s-expresiones + constructor de esquemas
                    + validador símbolo↔footprint (pines vs pads)
  gen_schematic.py  el DISEÑO: 11 hojas, 227 componentes, todas las conexiones
  check_conn.py     verificador propio: extremos de cable sueltos y solapes
                    (los solapes colineales son cortocircuitos silenciosos que
                     el ERC no nombra de forma clara)
  gen_pcb.py        construye la PCB con la API pcbnew: footprints, redes,
                    contorno, zonas de cobre, keepout de barrera
  build_all.ps1     cadena completa
```

Toolchain detectada: **KiCad 9.0.2**, Python 3.11.5 embebido, `kicad-cli`.

---

## 2. Qué existe ahora

### Esquemático — `kicad/b2b_converter.kicad_sch` + `kicad/sch/*`

| Hoja | Componentes | Contenido real capturado |
|---|---:|---|
| 01 Entrada AC + LCL | 26 | Bornera 3~+PE, 3 fusibles, choke CM, LCL completo (L2 0.6 mH · Cf 10 µF · Rd 2.2 Ω · L1 1.5 mH), banco MOV, X/Y caps |
| 02 Puente AFE | 9 | 6× SiC `C3M0075120K` (TO-247-**4**, con pin Kelvin) + 3 condensadores de lazo 1 µF/1 kV |
| 03 Bus DC | 18 | 4× 150 µF/900 V, precarga 68 Ω + bypass, bleeder + LED "BUS LIVE", divisor de 1 MΩ, chopper de frenado + diodo + bornera |
| 04 Puente inversor | 12 | 6× SiC, decoupling, bornera de motor U/V/W/PE, 2 NTC |
| 05 Gate drivers | 54 | **6× `UCC21520DW`** aislados, Rg_on 10 Ω / Rg_off 3.3 Ω con diodo por canal, resistencia de dead-time, desacoplos |
| 06 Sensado I/V | 41 | 6 cadenas de corriente (Hall → burden 0.1 % → anti-alias RC de 2 polos), buffer de Vdc con LM358, referencia de ADC, divisores de NTC |
| 07 STM32 | 20 | `STM32G474VET6` LQFP-100 con mapa de pines completo (TIM1/TIM8, ADC, BKIN, encoder, UART aislado), cristal, SWD, **NT1/NT2 net-ties de tierra** |
| 08 Protección | 17 | 4 comparadores `LM339` → `FAULT_N`, drivers de bobina K1/K2/ventilador con flyback, e-stop, LEDs |
| 09 Aux + bias | 15 | Entrada 24 V protegida, 3 reguladores, **6 módulos DC-DC aislados** para bias de gate, banco de `PWR_FLAG` |
| 10 Aislamiento | 3 | `ADuM1401` reforzado: UART + heartbeat, desacoplos a ambos lados |
| 11 ESP32 | 11 | `ESP32-S3-WROOM-1`, botones EN/BOOT, LEDs, conector de campo |

**227 componentes · 130 redes.** Las hojas se conectan por *global labels*.

### PCB — `kicad/b2b_converter.kicad_pcb`

- **340 × 240 mm, 4 capas.** 227 footprints colocados, 130 redes asignadas.
- Floorplan con flujo de energía izquierda→derecha:
  `01 LCL → 02 AFE → 03 BUS DC → 04 INVERSOR → motor`.
- **Barrera de aislamiento** como `Rule Area` llamada `ISO_BARRIER` (franja de
  6 mm sin cobre en las 4 capas). Los 6 gate drivers están colocados **a
  caballo** de ella — la barrera atraviesa el encapsulado, que es lo correcto.
- Zonas de cobre rellenadas: `DC_P` (F.Cu) y `DC_N` (B.Cu) **solapadas** sobre
  el banco → bus laminado; `PGND` en In1 sobre la zona HV; `GND` en In1/In2/B
  sobre la zona LV; **`IOGND` como isla aparte** para el ESP32.
- Colocación explícita de la etapa de potencia: los 12 SiC en dos filas
  alineadas al borde del disipador, banco DC en 2×2 en el centro.
- 6 agujeros M4, contorno, serigrafía con rótulos de zona y el aviso de HV.

### Salidas

```
export/b2b_esquematicos.pdf    los 12 planos (raíz + 11 hojas)
export/svg/*.svg               una hoja por archivo
export/erc.rpt, drc.rpt        informes
render/b2b_top.png             render 3D cenital
render/b2b_iso.png             render 3D en perspectiva
render/b2b_bottom.png          cara inferior
```

---

## 3. Qué FALTA (honestamente)

| Pendiente | Estado | Comentario |
|---|---|---|
| **Ruteo de pistas** | **0 %** | 326 `unconnected_items` en DRC. Es lo esperado: no hay ni una pista. Se rutea en Pcbnew siguiendo `docs/KICAD_PCB_FLOORPLAN.md` §5 |
| `items_not_allowed` (81) | pendiente | Pads que aún caen dentro de `ISO_BARRIER`. Ajustar posición fina de los drivers |
| `courtyards_overlap` (30) | pendiente | Colocación automática demasiado densa en algunas zonas |
| `solder_mask_bridge` (12) | pendiente | Deriva de lo anterior |
| Avisos de serigrafía (398) | cosmético | Texto de referencia sobre cobre/solapado |
| `endpoint_off_grid` (~1050) | cosmético | Los pines conectan **exactos**; solo no caen en múltiplos de 1.27 mm. Se prioriza conectividad correcta sobre la rejilla |
| Símbolos de fabricante | parcial | Se usan piezas reales de la librería estándar. Para producción hay que sustituir los genéricos (Hall, DC-DC aislados, reguladores) por los del fabricante |
| Verificación de creepage con footprints reales | pendiente | Las reglas están en `kicad/drc_custom_rules.txt`; hay que cargarlas en Board Setup y medir en los puntos peores |

### Nota de ingeniería sobre el MOSFET

La librería trae `C3M0075120K` (1200 V, **75 mΩ**). Con esa pieza a 15 kVA:

```
P_cond = 13.9² × (75 mΩ × 1.5) ≈ 21.7 W  →  ~25 W/dispositivo con conmutación
12 dispositivos ≈ 300 W  →  Rth_s-a ≤ 0.19 °C/W  (exige buen aire forzado)
```

Para el build real usa el **`C3M0040120K` (40 mΩ)**: mismo TO-247-4, mismos
pines, ~15 W/dispositivo y `Rth_s-a ≤ 0.37 °C/W`. Solo hay que cambiar el
campo *Value* — el símbolo y el footprint no cambian.

---

## 4. Siguiente paso recomendado

1. Abre `kicad/b2b_converter.kicad_pro` en KiCad 9 y revisa los planos.
2. Board Setup → **Custom Rules** → pega `kicad/drc_custom_rules.txt`.
3. Rutea por bloques en el orden de `docs/KICAD_PCB_FLOORPLAN.md` §5, empezando
   por los **lazos de conmutación** (lo que fija el EMI de toda la placa).
4. Cualquier cambio de diseño hazlo en `tools/gen_schematic.py` y re-ejecuta
   `build_all.ps1` — así el esquemático y la PCB no se desincronizan.
