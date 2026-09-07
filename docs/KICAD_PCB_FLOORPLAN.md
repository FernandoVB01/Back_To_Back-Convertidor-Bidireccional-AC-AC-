# PCB — Stackup, Floorplan, Zonas y Orden de Ruteo

> Se ejecuta **dentro de Pcbnew** tras cerrar la captura y el ERC. Este documento
> es el guion. El ruteo fino lo hacemos por bloques y lo reviso yo antes de
> fabricar. No mandes a fábrica sin DRC limpio + revisión 3D + verificación de
> creepage con footprints reales.

---

## 1. Stackup (Board Setup → Physical Stackup)

**4 capas, 1.6 mm, cobre 70 µm (2 oz) en externas, 35 µm en internas.**

| Capa | Uso | Cobre |
|---|---|---|
| **F.Cu** | Potencia lado A: `DC_P` en zona de puentes (laminado con B.Cu), nodos `SW_*`, lazos de gate, componentes de potencia | 70 µm |
| **In1.Cu** | `PGND` sólido bajo toda la zona de potencia. En la zona de control, mismo plano físico usado como `AGND` (separados por hueco, unidos sólo en `NT1`). | 35 µm |
| **In2.Cu** | Planos de alimentación troceados: `+15V`, `+5V`, `+3V3`, `+3V3_ANA`, islas de `+15Vg1..6`. Bajo el MCU: `DGND`. | 35 µm |
| **B.Cu** | Potencia lado B: `DC_N` en zona de puentes (laminado con F.Cu), retorno de conmutación. En zona control: señales + `DGND`/`IOGND`. | 70 µm |

- Dieléctrico F↔In1: **fino (≈ 0.2 mm)** en la zona de potencia para bajar la
  inductancia del bus laminado `DC_P`(F) / `DC_N`(B) — si el fabricante lo permite
  por sub-zona, si no, todo a 0.2–0.3 mm y compénsalo con núcleo grueso In1↔In2.
- Control de impedancia: sólo importa en RMII del PHY (50 Ω single-end) y USB
  (90 Ω dif). Define esas dos net classes de impedancia si usas Ethernet/USB.
- Para > 20 kW o EMC exigente: subir a **6 capas** (Sig / GND / Pwr / GND / Sig / Sig).

---

## 2. Floorplan (partición física — flujo de energía en una sola dirección)

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  ZONA HV (roja)                                    │  ZONA LV (azul/verde)     │
  │                                                    │                           │
  │  [J1 red] → [F1-3] → [K1] → [EMC/CM] → [LCL:       │                           │
  │   L2,Cf,Rd,L1]  ─────────────►  [AFE: Q1..Q6       │   ┌── BARRERA ─────────┐  │
  │                                  + Cdec + snubber] │   │ opto/aisladores    │  │
  │                                        │           │   │ + trafos de gate   │  │
  │                                   [SW_A/B/C]       │   │ (05, 10)           │  │
  │                                        │           │   └────────────────────┘  │
  │   [Precarga Rpc+K2] ── [BANCO C_dc] ═══╪═══════╗   │  [06 AFE analógico]       │
  │   [Chopper Qbrk+Jbrk] ──────────────── DC_P/DC_N   │  [Vref] [07 STM32]        │
  │                                        │           │  [08 Protección HW]       │
  │                                  [INV: Q7..Q12     │  [09 Aux + bias]          │
  │                                   + Cdec] ────────►│  ── BARRERA FUNCIONAL ──  │
  │                                   [SW_U/V/W]       │  [10 ISO] [11 ESP32]      │
  │                                        │           │  [antena keep-out]        │
  │                                  [L_CM2] → [J_MOT] │  [J_DBG][USB-C][RJ45]     │
  └──────────────────────────────────────────────────────────────────────────────┘
     Disipador común a lo largo del borde inferior de la ZONA HV (AFE + INV + chopper)
     con NTC en 2 puntos.  Ventilador soplando a lo largo del disipador.
```

Principios:
1. **Energía fluye de izquierda a derecha** (red→LCL→AFE→bus→INV→motor). Nada
   regresa cruzando bloques ya "usados".
2. **Una sola barrera de seguridad** recta que cruza la placa entre ZONA HV y
   ZONA LV. Los drivers (05) y los aisladores de comms (10) son los únicos
   componentes que la pisan. Dibuja `Rule Area "ISO_BARRIER"` en In1/In2/B.Cu a
   lo largo de ella → la regla 9 del DRC prohíbe cobre dentro.
3. **Segunda barrera, funcional**, entre dominio CTRL y dominio IoT (ESP32). 4 mm.
4. Banco `C_dc` **entre** AFE e INV, lo más cerca posible de ambos puentes; el bus
   `DC_P/DC_N` como par laminado F/B, sin interrupciones.
5. Sección analógica (06 + Vref + entradas de ADC del 07) **agrupada y lejos** de
   `SW_*`, de los magnéticos y del ESP32/RF.
6. Conectores de campo (red, motor, freno, 24 V) en **bordes opuestos**: red y
   motor no comparten borde.

---

## 3. Zonas de cobre (Add Zone)

| Zona | Capa | Net | Prioridad | Límite |
|---|---|---|---|---|
| Bus + | F.Cu | `DC_P` | 60 | sólo dentro de ZONA HV, sobre banco y puentes |
| Bus − | B.Cu | `DC_N` | 60 | espejo exacto de `DC_P` (laminado) |
| PGND potencia | In1.Cu | `PGND` | 50 | toda la ZONA HV; hueco de aislamiento hacia AGND |
| AGND analógico | In1.Cu | `AGND` | 50 | sólo bajo sección 06 + Vref + pines ADC; se une a PGND vía `NT1` únicamente |
| DGND | In2.Cu / B.Cu | `DGND` | 45 | bajo STM32 y lógica |
| IOGND | In2.Cu / B.Cu | `IOGND` | 45 | sólo bajo dominio ESP32; **sin** unión a DGND |
| +15V / +5V / +3V3 / +3V3_ANA | In2.Cu | resp. | 40 | islas, no solapan |
| +15Vg1..6 | In2.Cu | resp. | 40 | isla flotante por rama, sobre cada driver |
| PE / CHASSIS | F.Cu + B.Cu | `PE` | 30 | anillo de guarda en el borde, stitching, a espárragos de montaje |

- **Ninguna** pista de señal cruza el hueco entre `PGND` y `AGND`, ni entre islas
  de alimentación. Si una señal debe cruzar, su retorno cruza con ella (misma
  ranura, mismo punto).
- Stitching de vías `PGND`↔`In1` cada ~5 mm en la zona de potencia.
- Y-caps (`CY`) de `PGND` y `DGND` a `PE` junto a la barrera, para el retorno de
  corriente de modo común.

---

## 4. Reglas de ruteo por bloque (alta dv/dt · di/dt)

### 4.1 Lazo de conmutación (AFE e INV) — lo primero que se rutea

- Orden de colocación por rama: `DC_P (F) → Qx_alto → Qx_bajo → DC_N (B)` con
  `Cdec (1 µF/1 kV)` justo cruzando `DC_P/DC_N` **a < 10 mm** del par de MOSFET.
- Objetivo `L_lazo < 20 nH`. Sobretensión estimada:
  `V_pico = V_dc + L_lazo · di/dt`; con `di/dt ≈ 20 A / 20 ns = 1e9 A/s` y 20 nH →
  **+20 V** sobre 800 V → OK bajo 1200 V. Mide en bench con sonda diferencial HV.
- `DC_P` y `DC_N` **solapados en F/B** en toda la trayectoria (cancelación de campo).
- Varias vías en paralelo (≥ 4, ⌀ 0.6/1.2) en cada transición de `DC_P`/`DC_N`.

### 4.2 Nodo de conmutación `SW_*`

- Cobre **sólo lo necesario** por ampacidad/térmico; es el agresor de dv/dt.
- Lejos de: sección analógica, lazos de gate de *otras* ramas, barrera de aislam.
- **No** inundar `PGND` hasta el borde de `SW_*`: dejar hueco + anillo de guarda
  `PGND` a distancia (reduce inyección capacitiva).

### 4.3 Lazo de gate

- `G_Hx` + `Rg` + `KELVIN_Hx` como **par apretado** (adyacentes en capa, o F sobre
  In1-guard), área de lazo **< 1 cm²**.
- `Rg` y clamp de Miller **en el pie del MOSFET**, no en el driver.
- Bias del driver (`+15Vg/-4Vg`) con `1 µF + 100 nF` en el pin y otro par en el SiC.
- Driver a **< 15 mm** del MOSFET.

### 4.4 Bus laminado y banco

- `C_dc` repartido: los de HF (`2.2 µF film`) pegados a cada puente; el grueso en
  el centro. Todas las conexiones al bus por el par laminado, sin "stubs".

### 4.5 Analógico

- Pistas de sensor como **diferenciales guardadas**, sobre `AGND` continuo.
- Cruzar pistas de potencia **a 90°** y en capa distinta.
- `Vref` en **estrella** al pin del ADC; `10 µF+100 nF` dedicados.
- Filtro anti-alias y `33 Ω + 1 nF` **en el pin del ADC**.

### 4.6 EMI de entrada/salida

- CM choke de entrada + X/Y caps junto a `J1`. CM choke de salida junto a `J_MOT`.
- Shield del cable de motor con **abrazadera 360°** a `PE` en el conector.
- Anillo de guarda `PE` en todo el borde, stitching cada ~10 mm, a los 4+
  espárragos de montaje (contacto metálico con el gabinete).

---

## 5. Orden de ruteo (secuencia recomendada en Pcbnew)

1. Colocar contornos: `Edge.Cuts` de la placa + `Rule Area "ISO_BARRIER"` + keep-out
   de antena ESP32 + agujeros de montaje (M3/M4, uno por esquina + centro de la
   zona de potencia bajo el disipador).
2. Colocar los **12 MOSFET + Cdec + banco C_dc + bus** y rutear **4.1** (lazos de
   conmutación) y **4.4** (bus laminado). Correr DRC.
3. Colocar los **6 drivers** sobre la barrera y rutear **4.3** (gate) + bias.
4. Colocar **LCL, EMC, precarga, chopper, borneras HV** y rutear la potencia AC.
5. Colocar **sección analógica (06) + Vref** y rutear **4.5**. Verter `AGND`.
6. Colocar **STM32 (07)** y rutear PWM→drivers, ADC←analógico, BKIN←`/FAULT`.
   Colocar `NT1`, `NT2`.
7. Colocar **protección (08)** y rutear cadena de fallo + mando de relés.
8. Colocar **aux/bias (09)** y planos de alimentación (In2).
9. Colocar **ISO comms (10) + ESP32 (11)** y rutear enlace aislado + Ethernet/USB.
   Verter `IOGND`, barrera funcional 4 mm.
10. Vertidos finales (`DC_P`,`DC_N`,`PGND`,`DGND`,`PE`), stitching, teardrops.
11. **DRC completo** (con reglas custom) → 0 errores. Revisar cada warning.
12. Vista 3D: comprobar choque de cuerpos, courtyards, altura bajo disipador,
    y **medir a ojo el creepage real** entre cobre HV y cobre LV con footprints
    reales (KiCad 8 lo reporta, pero confírmalo en los puntos críticos).
13. Fabricación: Gerbers X2, mapa de taladros, `.drl`, IPC-2581/ODB++ si tu
    fábrica lo acepta; nota de stackup y cobre 2 oz explícita.

---

## 6. Checklist de salida de PCB (antes de fabricar)

- [ ] DRC con `kicad/drc_custom_rules.txt` cargadas: **0 errores**.
- [ ] `ISO_BARRIER` sin cobre; creepage HV↔LV ≥ 8 mm medido en 3+ puntos peores.
- [ ] `DC_P`/`DC_N` laminados y sin interrupción; `L_lazo` estimada < 20 nH.
- [ ] `NT1` (AGND↔DGND) y `NT2` (DGND↔PGND) únicos; `IOGND` aislado.
- [ ] Todos los `SW_*` alejados de analógico y barrera; guarda `PGND` con hueco.
- [ ] Lazos de gate < 1 cm²; `Rg`/clamp en el pie del MOSFET.
- [ ] Disipador: Rth_s-a objetivo ≤ 0.3 °C/W con ventilador; NTC en 2 puntos.
- [ ] Anillo `PE` + stitching + abrazadera de shield de motor.
- [ ] Fiduciales (3), test points de bring-up accesibles (ver `06_bringup...md`).
- [ ] Silk: rótulo "⚠ HV — 800 V — DESCARGAR ANTES DE MANIPULAR" y LED BUS-LIVE.
