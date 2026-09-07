# Ruteo de la PCB — qué se intentó, qué funcionó y qué no

> Documento honesto sobre el intento de auto-ruteo. **Resumen: no se ruteó.**
> Se encontró y corrigió un error grave de colocación, y el auto-ruteador
> propio se descartó por no cumplir el listón de seguridad.

---

## 1. El hallazgo importante: los gate drivers estaban mal orientados

Al analizar qué redes se podían rutear apareció un **error real de diseño**,
no del ruteador.

El `UCC21520DW` es un SOIC-16W con la **lógica en los pines 1-8** y la
**potencia en los pines 9-16**. Es decir: la barrera de aislamiento del
encapsulado va **entre sus dos filas de pines**.

Estaban colocados con `rot=0`, lo que dejaba:

| Pad | Red | Dónde caía |
|---|---|---|
| 1, 2 | `PWM_H1`, `PWM_L1` (lógica) | y = 143.6 → **lado HV** |
| 8, 9 | `+5V`, `K_L1` (potencia) | y = 152.4 → lado LV |
| 3,4,5,11,14 | varias | **dentro de la franja de aislamiento** |

Con esa orientación, `PWM_H1` tenía que ir desde el lado HV del driver hasta
el STM32 en la zona LV: **cruzando la barrera de aislamiento**. No es una
incomodidad de ruteo, es una violación de aislamiento.

**Corrección: `rot=90`.** Deja la lógica (1-8) abajo en zona LV y la potencia
(9-16) arriba en HV, con las dos filas separadas 9.3 mm — la franja de 6 mm
queda limpia entre ellas, sin ningún pad dentro.

Efecto medido:

| | Antes | Después |
|---|---:|---:|
| Redes que cruzan la barrera | 29 | **19** |
| Pads dentro de la franja | 16 | **1** |
| Redes ruteables en su zona | 57 | **82** |

Este solo hallazgo justifica el ejercicio.

## 2. El auto-ruteador propio: descartado

`tools/route_pcb.py` implementa tres pasadas (vías a plano, potencia, señales)
con un ruteador L/Z y detección de colisión por distancia segmento-segmento.
Resultados de la mejor versión:

| | |
|---|---:|
| Ratsnest inicial | 326 |
| Ratsnest tras rutear | 157 |
| Redes completas | 15 de 98 |
| Pistas / vías | 215 / 80 |

**Pero el DRC lo tumbó:**

| Violación introducida | Cantidad |
|---|---:|
| `shorting_items` (cortocircuitos reales) | **37** |
| `clearance` | 106 |
| `holes_co_located` (vías solapadas) | 52 |
| `solder_mask_bridge` | 47 |

**37 cortocircuitos en una placa de 800 V es inaceptable.** Se revirtió.

### Por qué falla

El modelo de obstáculos del ruteador solo conoce pads y sus propias pistas.
No conoce:
- las zonas de cobre rellenadas,
- las reglas DRC reales por clase de red,
- los taladros como objetos que atraviesan **todas** las capas,
- las máscaras de soldadura.

Un ruteador L/Z sin *rip-up and retry* no sirve para la densidad del lado LV
(0603 a 4 mm de paso alrededor de un LQFP-100). Las pasadas 2-3 quedan
**desactivadas por defecto**; para forzarlas: `ROUTE_SIGNALS=1`.

## 3. Estado real de la placa que se entrega

**Colocada, con zonas de cobre, SIN pistas.**

```
Componentes ....... 227      Redes ............. 130
Ratsnest .......... 325      Pistas ............ 0
```

DRC actual: 772 violaciones. Desglose honesto:

| Tipo | N.º | Por qué |
|---|---:|---|
| `unconnected_items` | 325 | **no hay pistas**: es lo esperado |
| `clearance` | 198 | pads **sin red** dentro de las zonas HV (consecuencia de lo anterior) |
| `silk_over_copper` / `silk_overlap` | 199+199 | cosmético: referencias sobre cobre |
| `items_not_allowed` | 71 | pads que aún caen en el área `ISO_BARRIER` |
| `courtyards_overlap` | 46 | colocación automática demasiado densa |
| `solder_mask_bridge` | 27 | deriva de lo anterior |

Un bug real corregido por el camino: la zona de masa de la zona HV se vertía
como **`PGND`, red que no existe en la netlist** (el net-tie NT2 la une a
`GND`). Quedaba como cobre huérfano sin red. Ahora se vierte en `GND`.

## 4. Cómo rutear esto de verdad

Por orden de recomendación:

**a) Ruteador interactivo de KiCad** (lo que haría un diseñador).
Carga primero las reglas: *Configuración de la placa → Reglas custom* →
pegar `kicad/drc_custom_rules.txt`. Luego seguir el orden de
`docs/KICAD_PCB_FLOORPLAN.md` §5: **primero los lazos de conmutación**, que
son los que fijan el EMI de toda la placa.

**b) Freerouting** (autorouter libre, Java ya está instalado en la máquina).
Requiere exportar Specctra DSN desde Pcbnew (*Archivo → Exportar → Specctra
DSN*; `kicad-cli` no lo soporta) y descargar el `.jar`. No se hizo aquí
porque implica descargar y ejecutar software de terceros.

**c) Arreglar el ruteador propio.** Habría que sustituir el L/Z por un
ruteador de laberinto (A* sobre rejilla) con rip-up, y consultar el motor DRC
real de KiCad en vez de un modelo de obstáculos propio. Es un proyecto en sí.

## 5. Antes de rutear, conviene arreglar

1. **`items_not_allowed` (71)**: quedan pads en la franja `ISO_BARRIER`.
   Afinar la colocación de los módulos de bias aislados.
2. **Los 6 DC-DC de bias (`+15VG1H..6H`)**: son secundarios aislados y deben
   ir **a caballo de la barrera** junto a su driver, no en la zona LV. Con la
   huella genérica de 4 pines no encajan: hay que usar la del `MGJ2D152005SC`
   real, que tiene la separación de pines correcta.
3. **`courtyards_overlap` (46)**: separar más en la colocación automática.
