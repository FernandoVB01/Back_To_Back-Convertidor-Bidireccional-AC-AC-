# Plan de Captura del Esquemático — sheet por sheet

> Objetivo: convertir la captura del esquemático en **entrada de datos**, no en
> diseño. Cada sheet lista *refdes → valor → footprint → símbolo KiCad → conexiones*.
> Abre `kicad/b2b_converter.kicad_pro` en KiCad 8, entra a cada subhoja y coloca.
>
> Cálculos y justificación numérica: `docs/01_potencia_dimensionamiento.md`.
> Punto de diseño ancla: **15 kVA · 400 V_LL · 60 Hz · V_dc ≤ 800 V · f_sw 16 kHz**.

---

## Convenciones de nets globales (etiquetas jerárquicas)

| Net | Clase | Dominio | Descripción |
|---|---|---|---|
| `GRID_L1/L2/L3` | HV_AC | potencia | fases de red tras fusible+contactor |
| `LCL_A/B/C` | HV_AC | potencia | nodo intermedio LCL (entre L1conv y Cf) |
| `SW_A/B/C` | HV_DC | potencia | nodos de conmutación AFE |
| `SW_U/V/W` | HV_DC | potencia | nodos de conmutación inversor |
| `MOT_U/V/W` | HV_AC | potencia | salida a motor tras choke |
| `DC_P` / `DC_N` | HV_DC | potencia | bus DC + / − |
| `DC_MID` | HV_DC | potencia | punto medio del banco (solo opción electrolítica) |
| `G_H1..6` `G_L1..6` | GATE_HS/LS | gate | gate alto/bajo de cada rama (1–3 AFE, 4–6 INV) |
| `KELVIN_H1..6` `KELVIN_L1..6` | GATE_HS/LS | gate | retorno Kelvin source |
| `PWM_H1..6` `PWM_L1..6` | CTRL | control | PWM lógicos desde STM32 |
| `FLT_1..6` | CTRL | control | fallo DESAT aislado por rama |
| `AIN_IAFE_A/B/C` `AIN_IMOT_U/V/W` | ANA | control | corrientes acondicionadas a ADC |
| `AIN_VDC` `AIN_VGRID_A/B/C` `AIN_VMOT_*` | ANA | control | tensiones acondicionadas a ADC |
| `AIN_NTC1/2` | ANA | control | termistores disipador/módulo |
| `VREF_ADC` | ANA | control | referencia buffered del ADC (3.000 V) |
| `/FAULT` | CTRL | control | línea de fallo agregada → BKIN |
| `EN_PWR` | CTRL | control | habilitación global de PWM |
| `K1_DRV` `K2_DRV` `FAN_DRV` | Default | control | mando de bobinas (low-side) |
| `ISO_UART_TX/RX` `ISO_HB_A/B` | CTRL↔IO_ISO | barrera | enlace STM32↔ESP32 aislado |
| `+15V` `+5V` `+3V3` `+3V3_ANA` `-15V` | Default/ANA | aux | rieles |
| `+15Vg1..6` `-4Vg1..6` `GNDg1..6` | flotante | gate | bias aislado por rama |
| `PE` | PE | — | tierra de protección / chasis |

**Reglas ERC que vas a activar** (Schematic Setup → Electrical Rules):
- Pin analógico de entrada del ADC = `passive`/`input`; marca `no-connect` explícito en todo pin no usado.
- Etiqueta jerárquica sin par en la raíz = error (para no dejar nets colgadas entre hojas).

---

## SHEET 01 — Entrada AC + Filtro LCL  (`sch/ac_input_lcl.kicad_sch`)

### Cálculo del LCL (resumen; detalle en 01_potencia_dimensionamiento.md)

```
I_n      = S / (√3·V_LL)              = 15000/(1.732·400)      = 21.65 A RMS
Z_base   = V_LL²/S                    = 10.67 Ω
L_base   = Z_base/(2π·60)             = 28.3 mH
C_base   = 1/(2π·60·Z_base)           = 248.7 µF

L1_conv  = V_dc/(8·ΔI_pp·f_sw)  con ΔI_pp = 0.15·I_pk = 4.6 A
         = 700/(8·4.6·16000)         ≈ 1.5 mH   (0.053 pu, dentro de 3–8 %)

Cf       = 0.04·C_base ≈ 10 µF (Y)   → Q_reactiva ≈ 4 % de S   (límite típico 5 %)

L2_grid: se fija ubicando la resonancia. Objetivo f_res ≈ 2.4 kHz:
   f_res = (1/2π)·√[(L1+L2)/(L1·L2·Cf)]
   con L1 = 1.5 mH, Cf = 10 µF, f_res = 2400 Hz  →  L2 ≈ 0.6 mH  (r = L2/L1 = 0.4)
   Restricción:  10·f_g (600 Hz)  <  f_res  <  0.5·f_sw (8000 Hz)   ✔

Atenuación de rizado a f_sw (grid vs. conv):
   k_a = 1/|1 − ω_sw²·L1·Cf·(1+r)/r ...|  ≈ 0.02   → grid ripple ≈ 2 % del de convertidor  ✔

Amortiguamiento (R serie con Cf):
   R_d = 1/(3·ω_res·Cf) = 1/(3·2π·2400·10e-6) ≈ 2.2 Ω     (empezar 2.2 Ω / 10 W, optimizar)
```

### Componentes

| Ref | Valor | Footprint | Símbolo KiCad | Notas |
|---|---|---|---|---|
| J1 | Bornera 4 vías 800 V/32 A | `TerminalBlock:TerminalBlock_Phoenix_...5.08mm` | `Connector:Screw_Terminal_01x04` | L1,L2,L3,PE |
| F1–F3 | Fusible 25 A aR/gG | `Fuse:Fuse_Bel_0ADAC` o portafusible DIN externo | `Device:Fuse` | uno por fase |
| RV1–RV3 | MOV 20D471K (300 VAC/470 V clamp) | `RV_Disc_D20mm_W5.0mm_P10mm` | `Device:Varistor` | fase-fase o fase-PE, clase II |
| K1 | Contactor 3P 25 A, bobina 24 VDC | huella de relé de potencia o bornas a contactor externo | `Relay:...` o `Connector` | mando `K1_DRV` desde sheet 08 |
| L_CM1 | Choke modo común 3~ 3–5 mH | huella toroide / módulo | `Device:L` (x3 acoplados) o símbolo choke 3ph | filtro EMC de entrada |
| CX1–CX2 | 0.47 µF X2 275 VAC | `C_Rect_L26.0mm_W6.0mm_P22.50mm_...` | `Device:C` | modo diferencial |
| CY1–CY3 | 4.7 nF Y2 | `C_Disc_D9.0mm_...` | `Device:C` | a `PE` |
| L1A/L1B/L1C | **1.5 mH** / 30 A / núcleo de polvo o ferrita con gap | huella de inductor de potencia bobinado / bornas a inductor externo | `Device:L` | lado convertidor (uno por fase) |
| CFA/CFB/CFC | **10 µF** film 3~ (o 3× monofásico) 500 VAC | `C_Rect_...P37.5mm` | `Device:C` | conexión Y, punto común flotante o a `PE` según diseño |
| RDA/RDB/RDC | **2.2 Ω / 10 W** | `R_Axial_Power_L25.0mm...` | `Device:R` | serie con cada Cf (damping pasivo) |
| L2A/L2B/L2C | **0.6 mH** / 30 A | huella inductor / bornas | `Device:L` | lado red (uno por fase) |
| TP1–TP6 | test points | `TestPoint:TestPoint_Pad_D2.0mm` | `Connector:TestPoint` | GRID_Lx y LCL_x para scope diferencial |

### Conexiones

```
J1.L1 ─ F1 ─ K1.A1 ── GRID_L1 ── L_CM1 ── L1A ── LCL_A ── (RDA+CFA a nodo Y) ── L2A ── SW_A?  NO:
```
Ojo al orden físico del LCL: **red → L2_grid → (Cf+Rd al centro) → L1_conv → puente**.
Corrige así:

```
J1.L1 ─F1─ K1 ── GRID_L1 ─ L_CM1 ─ L2A ─ LCL_A ─┬─ L1A ─ SW_A (a sheet 02, gate del medio-puente A)
                                                 └─ RDA ─ CFA ─ NODO_Y
(idéntico para B, C ; NODO_Y común de los tres Cf; conectar NODO_Y a PE por 1 punto o dejar flotante)
J1.PE ── PE  (barra de tierra, a chasis por espárrago)
```
Etiquetas jerárquicas de salida: `SW_A/B/C` **no** — el nodo que va al puente es
la corriente de línea del AFE; nómbralo `AFE_A/B/C` para no confundir con el nodo
de conmutación interno del puente. Ajusta: **salida de sheet 01 = `AFE_A/B/C`**.
Sensado: deriva `AIN_VGRID_A/B/C` desde `GRID_Lx` (a sheet 06) y coloca 3
transductores de corriente sobre `AFE_A/B/C` → `AIN_IAFE_A/B/C`.

---

## SHEET 02 — Puente AFE  (`sch/afe_bridge.kicad_sch`)

### Selección de interruptor (resumen; detalle en 01_...md §3)

| | IGBT 1200 V | **SiC MOSFET 1200 V** ← elegido |
|---|---|---|
| f_sw práctica | 8–12 kHz | 16–48 kHz |
| Pérdida conmutación | alta (cola) | baja |
| Tamaño LCL / magnéticos | mayor | menor |
| Coste | menor | mayor |
| Recomendación 15 kW regenerativo | — | **SiC discreto TO-247-4** |

```
Conducción por MOSFET (inversor, aprox):
   I_S,rms ≈ I_ph,pk·√(1/8 + m·cosφ/(3π)) = 30.6·√(0.125+0.081) ≈ 13.9 A
   R_dson(125°C) ≈ 1.5·40 mΩ = 60 mΩ
   P_cond ≈ 13.9²·0.060 ≈ 11.6 W  por dispositivo

Conmutación:  E_on+E_off ≈ 0.13 mJ @ 700 V / 15 A (escalado de datasheet)
   P_sw ≈ 0.13e-3·16000 ≈ 2.1 W ;  + Qrr cuerpo ≈ 1 W  →  ≈ 3 W

Total ≈ 15 W/dispositivo · 12 = 180 W semis.  η global ≈ 97–98 %.
```

### Componentes (rama tipo, ×3: A, B, C — refdes Q1..Q6)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| Q1,Q3,Q5 | SiC MOSFET 1200 V / 40 mΩ (alto) | `Package_TO_SOT_THT:TO-247-4_...` (pin Kelvin) | `Transistor_FET:...` genérico N-MOS 4pin o símbolo propio | drain→`DC_P` |
| Q2,Q4,Q6 | SiC MOSFET 1200 V / 40 mΩ (bajo) | idem | idem | source→`DC_N` (vía Kelvin sense aparte) |
| Cdec1_A..C | 1 µF / 1 kV C0G o film | `C_Rect_L18...` o `C_1210_...` (varios en //) | `Device:C` | **DC_P–DC_N pegado a cada rama, < 10 mm** |
| Rsn_A..C + Csn_A..C | 10 Ω 2 W + 1 nF 1 kV | `R_Axial...` + `C_Disc...` | `Device:R`,`Device:C` | snubber RC opcional drain-source lado bajo (poblar tras bench) |
| Rg no aquí | — | — | — | los Rg viven en sheet 05 (junto al driver) |
| TP_SWA..C | — | `TestPoint` | — | nodo de conmutación para scope dv/dt |

### Conexiones por rama A (repetir B con Q3/Q4/SW_B, C con Q5/Q6/SW_C)

```
DC_P ─┬─ Q1.D
      └─ Cdec1_A ─ DC_N
Q1.S ─┬─ Q2.D ─── SW_A ─── (a sheet 01: nodo AFE_A, tras L1A)
      └─ (KELVIN_H1 al sheet 05, sense de source alto)
Q2.S ─┬─ DC_N
      └─ (KELVIN_L1 al sheet 05)
Q1.G ── G_H1 (sheet 05)      Q2.G ── G_L1 (sheet 05)
Transductor de corriente sobre SW_A o sobre AFE_A → AIN_IAFE_A (sheet 06)
```

> **Regla de layout que ya condiciona la captura:** agrupa `Q1,Q2,Cdec1_A` como
> bloque; el par `DC_P/DC_N` entra por un lado y sale `SW_A` por el opuesto. En
> PCB esto es el *lazo de conmutación* — objetivo < 20 nH.

---

## SHEET 03 — Bus DC + Precarga + Chopper  (`sch/dclink_precharge.kicad_sch`)

### Cálculo (detalle en 01_...md §2)

```
Rizado de corriente del capacitor (inversor, peor caso):
   I_C,rms ≈ 0.55·I_o,rms ≈ 0.55·21.65 ≈ 12 A RMS @ f_sw + baja frecuencia
   → banco debe soportar ≥ 15–20 A RMS de rizado

Capacitancia por transitorio de frenado (700 V → 780 V antes del chopper,
   tiempo de respuesta del lazo de bus ≈ 1.5 ms a 15 kW regen):
   E = P·t = 15000·1.5e-3 = 22.5 J
   ½·C·(780² − 700²) = 22.5  →  C ≈ 380 µF   (mínimo)

Elección:  C_bus objetivo 470–700 µF.
   OPCIÓN A (film, recomendada SiC):  4× 150 µF / 900 Vdc = 600 µF, sin balanceo, ESL baja
   OPCIÓN B (electrolítico):  2S3P de 470 µF/450 V ≈ 705 µF ; R_balance por cap:
        I_bal = 10 mA → R = 400 V / 0.01 = 40 kΩ → usar 33 kΩ / 5 W
        τ_descarga = 33k·470µF = 15.5 s → <60 V en ~2τ ≈ 31 s  ✔ (IEC 61800-5-1)
   + 2× 2.2 µF / 1 kV film para HF sea cual sea la opción.

Precarga (soft-start):
   V_pk_natural = √2·400 = 566 V (a través de diodos de cuerpo del AFE)
   I_inrush ≤ 8 A  →  R_pc = 566 / 8 = 70.75 Ω  →  68 Ω
   τ = R_pc·C_bus = 68·700e-6 = 47.6 ms ;  95 % en 3τ ≈ 143 ms ;  99 % en 5τ ≈ 238 ms
   Energía en R_pc por carga = ½·C·V_pk² = ½·700e-6·566² ≈ 112 J
   Pico de potencia = 566²/68 ≈ 4.7 kW (instantáneo, decae con τ)
   → resistencia bobinada con rating de pulso ≥ 3·112 J y térmico repetitivo.
   Cierre de K2 (bypass) a V_dc ≥ 510 V  o  t = 300 ms  (lo que ocurra primero);
   FALLO si V_dc no sube en 1 s (cap en corto)  o  sube demasiado lento (K2 abierto / ESR alta).

Chopper de frenado (respaldo):  umbral 760–780 V ;  R_brk externa dimensionada por
   potencia de frenado media requerida (bornera + disipador propio).
```

### Componentes

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| C1–C4 (opc. A) | 150 µF / 900 Vdc film DC-link | `Capacitor_THT:CP_Radial_...` grande / bornas | `Device:C_Polarized` o `Device:C` | `DC_P`–`DC_N` |
| C1–C6 (opc. B) | 470 µF / 450 V snap-in | `CP_Radial_D35.0mm_P10.00mm` | `Device:C_Polarized` | 2 en serie (`DC_P`–`DC_MID`–`DC_N`) ×3 ramas |
| Rb1–Rb6 (opc. B) | 33 kΩ / 5 W | `R_Axial_Power_L38...` | `Device:R` | 1 por cap, balanceo |
| C5,C6 | 2.2 µF / 1 kV film | `C_Rect_L26...` | `Device:C` | decoupling HF del bus |
| Rpc | 68 Ω / pulso ≥ 350 J (2×33 Ω 100 W en serie) | bornas a resistencia externa | `Device:R` | precarga |
| K2 | Contactor/relé 1P 20 A 24 VDC | relé de potencia o bornas | `Relay:...` | bypass de Rpc, mando `K2_DRV` |
| Rbleed | 100 kΩ / 3 W (o bleeder activo) | `R_Axial_Power_L38...` | `Device:R` | descarga permanente + LED |
| D_bleed_LED + R | LED rojo + 220 kΩ | — | `Device:LED`,`Device:R` | indicador "BUS LIVE" |
| Qbrk | SiC/IGBT 1200 V ≥ 30 A | `TO-247-3` | `Transistor_FET`/`IGBT` | chopper |
| Dbrk | diodo SiC 1200 V ≥ 30 A | `TO-247-2` | `Device:D` | free-wheel de R_brk |
| Jbrk | bornera 2 vías | `Screw_Terminal_01x02` | `Connector` | a resistencia de frenado externa |
| Rsh_dc / div | divisor 5×200 kΩ 0.1 % | `R_1206` ×5 en serie | `Device:R` | a amp aislado (sheet 06): `AIN_VDC` |

### Conexiones

```
(desde sheet 02 diodos de cuerpo) rectificado ── Rpc ──┬── DC_P (banco)
K2 en paralelo con Rpc (bypass)                          │
                                        C1..Cn ═════════ DC_P / DC_N
Qbrk.D ── DC_P ;  Qbrk.S ── Jbrk.1 ;  Jbrk.2 ── DC_N ;  Dbrk entre Jbrk.1 y DC_P
Rbleed entre DC_P y DC_N (siempre) ;  LED "BUS LIVE" en serie con su R
Divisor DC_P→...→DC_N, toma media a sheet 06
DC_P / DC_N como etiquetas jerárquicas hacia sheet 02 y sheet 04 (bus laminado en PCB)
Gate de Qbrk ← PWM_BRK (sheet 07)  con su propio driver simple (puede ir en sheet 05 como 7ª instancia reducida)
```

---

## SHEET 04 — Puente Inversor  (`sch/inverter_bridge.kicad_sch`)

Idéntico a **SHEET 02** en topología y componentes, con:

| Rama | Alto | Bajo | Nodo | Gate | Corriente |
|---|---|---|---|---|---|
| U | Q7 | Q8 | `SW_U` | `G_H4`/`G_L4` | `AIN_IMOT_U` |
| V | Q9 | Q10 | `SW_V` | `G_H5`/`G_L5` | `AIN_IMOT_V` |
| W | Q11 | Q12 | `SW_W` | `G_H6`/`G_L6` | `AIN_IMOT_W` |

Añadidos propios del lado motor:

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| L_CM2 | choke modo común de salida 3~ (opcional) | toroide / módulo | choke 3ph | reduce corriente de fuga por cable de motor |
| Rcl+Ccl (×3) | clamp dv/dt de cable (RC) | `R_Axial`,`C_Disc` | `Device:R/C` | poblar según largo de cable |
| J_MOT | bornera 4 vías (U,V,W,PE) | `Screw_Terminal_01x04` grande | `Connector` | 360° shield clamp del cable |
| RT1,RT2 | NTC 10 kΩ B3950 | `R_Axial` / cable | `Device:Thermistor` | 1 en disipador, 1 en módulo → `AIN_NTC1/2` (sheet 06) |

```
DC_P/DC_N (de sheet 03) ═══ ramas Q7..Q12 ═══
SW_U/V/W ── L_CM2 ── (Rcl/Ccl) ── MOT_U/V/W ── J_MOT
J_MOT.PE ── PE
```

---

## SHEET 05 — Gate Driver aislado (instancia ×6)  (`sch/gate_driver.kicad_sch`)

### Diseño (detalle en 02_esquematico_acondicionamiento.md §1)

- **Aislador**: driver reforzado con CMTI > 100 V/ns, DESAT y CLAMP integrados.
  Candidatos: `UCC21750` (TI), `STGAP2S`/`STGAP3S` (ST, encaja con ecosistema STM32),
  `1EDI3021AS` (Infineon).
- **Bias por lado**: +15 V / −4 V. Generación: `SN6505B` + transformador push-pull
  + rectificador + LDO, **o** módulo (`MGJ2D152005`, `RP-1515D`...). 2 W por lado.
- **Rg**: `Rg_on ≈ 10 Ω`, `Rg_off ≈ 3.3 Ω` (separados con diodo de conmutación).
  Empezar ahí, ajustar en bench midiendo dv/dt y sobreimpulso Vgs.
- **Active Miller Clamp**: pin CLAMP → gate, traza < 10 mm, activa cuando Vgs < 2 V.
- **DESAT**: diodo(s) serie HV (`US1M`/`STTH1L06` ×2) a VDS, `C_blank ≈ 330 pF`
  (→ t_blank ≈ 1–2 µs), umbral ~7–9 V. Falla → turn-off suave (STO) + `FLT` latcheado.
- **Kelvin source** del 4º pin del SiC directo al pin de referencia del driver.
- Clamp gate-source: TVS/Zener `+20 / −6 V`. Decoupling `100 nF + 1 µF` en el driver
  y otro `100 nF + 1 µF` junto al SiC.

### Componentes por instancia (parámetros de hoja: `n` = 1..6)

| Ref | Valor | Footprint | Símbolo | Conecta |
|---|---|---|---|---|
| U_GDn | driver aislado reforzado | `Package_SO:SOIC-16W_...` (según parte) | símbolo del fabricante | ver abajo |
| U_BIASn | módulo DC-DC aislado 15/−4 V 2 W | huella del módulo | `Converter_DCDC:...` | `+15V`/`GND` in, `+15Vgn`/`-4Vgn`/`GNDgn` out |
| Rg_on_Hn / Rg_on_Ln | 10 Ω 1 W | `R_2512` | `Device:R` | driver OUT_H → `G_Hn` (idem L) |
| Rg_off_Hn / Rg_off_Ln | 3.3 Ω 1 W | `R_2512` | `Device:R` | rama de apagado con `D_off` |
| D_off_Hn/Ln | diodo rápido 200 V | `D_SOD-123` | `Device:D` | paralelo a Rg_on |
| D_desatHn/Ln | 2× `STTH1L06` (600 V) | `D_SMA` | `Device:D` | pin DESAT → `SW_x`/`DC_N` |
| C_blankHn/Ln | 330 pF 100 V | `C_0603` | `Device:C` | pin DESAT → source |
| TVS_gsHn/Ln | `+20/−6 V` | `D_SOD-323` | `Device:D_Zener_Dual` | gate ↔ Kelvin |
| C_bias in/out | 100 nF + 1 µF ×2 lados | `C_0603`,`C_0805` | `Device:C` | VCC/VEE del driver |
| U_isoFLTn (si el driver no lo trae) | 1 ch aislador | `SOT-23-6` | — | `FLT` interno → `FLT_n` (dominio CTRL) |

### Conexiones (por instancia n)

```
Dominio CTRL (izquierda del aislador):
   PWM_Hn ── U_GDn.INA        PWM_Ln ── U_GDn.INB (o driver dual de 1 canal ×2)
   EN_PWR ── U_GDn.EN
   U_GDn.FLT ── FLT_n         (a sheet 08, agregación de fallo)
   +5V / +3V3 ── U_GDn.VCCI   ;  DGND ── U_GDn.GNDI

Barrera (creepage 8 mm en PCB, ranura si el paquete no llega)

Dominio potencia (derecha):
   +15Vgn ── U_GDn.VDD ;  -4Vgn ── U_GDn.VEE ;  GNDgn ── U_GDn.VSS (= KELVIN de esa rama)
   U_GDn.OUT_H ─ Rg_on_Hn ∥ (Rg_off_Hn+D) ─ G_Hn
   U_GDn.CLAMP_H ── G_Hn (traza corta)
   U_GDn.DESAT_H ─ D_desatHn ─ SW_x   (alto: a nodo de conmutación de su rama)
   idem lado bajo con DC_N como referencia de DESAT
```

> Instanciación en KiCad: coloca el sheet `gate_driver.kicad_sch` **6 veces** en
> `05` (o crea `05` como contenedor con 6 sub-sheets del mismo archivo). Usa
> *sheet fields* o etiquetas jerárquicas parametrizadas (`G_H${n}`) — KiCad 8
> no sustituye variables en labels, así que la vía práctica es **6 copias del
> archivo** `gate_driver_1.kicad_sch`..`_6.kicad_sch` con los labels ya numerados,
> o una hoja plana con los 6 bloques. Recomendado: hoja plana `05` con 6 bloques
> (más fácil de revisar el ruteo después).

---

## SHEET 06 — Sensado I/V + AFE analógico  (`sch/sense_iv.kicad_sch`)

### Diseño (detalle en 02_...md §2)

**Corriente (6 canales)** — elige una vía y úsala en todos:
- (a) **Hall closed-loop** (`LEM LA 25-NP`, `LKSR 15-NP`, `HO 25-P`): salida en
  corriente → `R_burden` 0.1 % 25 ppm → ±V. Aislamiento inherente.
- (b) **Sigma-delta aislado** (`AMC1305M25` / `AMC1035`) + shunt Kelvin 1–2 mΩ →
  al `DFSDM`/`ADC-SD` del STM32. Mejor rechazo y precisión, más firmware.

Cadena tras el sensor: amp diferencial / nivel (`OPA2320`, `ADA4522-2` zero-drift
para exactitud DC) → offset a `VREF_ADC/2` (1.5 V) → filtro **Sallen-Key 2º orden
Butterworth**, `f_c ≈ 12–16 kHz`, retardo de grupo < 1 µs.

**Tensión (7 canales: V_dc + 3 red + 3 motor)**:
- Amp aislado de alta impedancia (`AMC1311`, entrada ±2 V) con divisor resistivo,
  o sigma-delta. Divisor de bus: `5× 200 kΩ` (1 MΩ) → 800 V ≈ 1.6 mA, 0.13 W/R,
  usar `1206`/`2010` con rating de tensión.

**Referencia ADC**: `REF5030` (3.000 V) buffered → `VREF_ADC`, en estrella al pin
`VREF+` del STM32, con `10 µF + 100 nF` dedicados. Ratiométrico donde se pueda.

### Componentes (por canal de corriente, ×6; refdes con sufijo de canal)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U_Ixx | Hall LA 25-NP (o AMC1305) | huella LEM / `SOIC-16` | fabricante | primario en serie con `AFE_x`/`SW_x` |
| Rb_xx | burden 100 Ω 0.1 % 25 ppm | `R_1206` | `Device:R` | solo Hall |
| U_AIxx | OPA2320 / ADA4522-2 | `SOIC-8` | `Amplifier_Operational:OPA2320` | dif + offset |
| Rf/Ri xx | red de ganancia 0.1 % | `R_0603` | `Device:R` | ganancia a fondo de escala 3.0 V |
| SK filtro | R,R,C,C Butterworth fc≈14 kHz | `R_0603`,`C_0603 C0G` | `Device:R/C` | 2º orden |
| C_aa | 1 nF C0G a la entrada del ADC | `C_0603` | `Device:C` | + `33 Ω` serie |
| Out | — | — | — | `AIN_IAFE_A/B/C`, `AIN_IMOT_U/V/W` |

### Componentes (tensión, por canal ×7)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| Rdiv_xx (×5) | 200 kΩ 0.1 % | `R_1206` | `Device:R` | cadena serie |
| U_Vxx | AMC1311 | `SOIC-8` | fabricante | entrada ±2 V |
| U_Vbuf_xx | OPA320 | `SOT-23-5` | `Amplifier_Operational` | buffer salida aislador |
| SK filtro | fc≈14 kHz | — | — | igual que corriente |
| Out | — | — | — | `AIN_VDC`, `AIN_VGRID_A/B/C`, `AIN_VMOT_U/V/W` |

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U_REF | REF5030AIDR | `SOIC-8` | `Reference_Voltage:REF5030` | 3.000 V |
| U_REFBUF | OPA320 | `SOT-23-5` | — | buffer de fuerza |
| C_ref | 10 µF + 100 nF | `C_0805`,`C_0603` | `Device:C` | |
| RT1,RT2 in | 2× NTC (de sheet 04) | — | `Device:Thermistor` | pull-up a +3V3_ANA → `AIN_NTC1/2` |
| NT1 | **Net-tie AGND↔? no aquí** | — | — | el net-tie va en sheet 07 |

### Comparadores de protección (van a sheet 08)

| Señal | Fuente | Umbral | Destino |
|---|---|---|---|
| OC_IAFE_x / OC_IMOT_x | salida de cada Hall (antes del filtro) | 1.8× I_pk ≈ 55 A | ventana → `/FAULT` |
| OV_DC | `AIN_VDC` sin filtrar | 800 V | comparador → `/FAULT` |
| OT | `AIN_NTC1` | equivalente 95 °C | comparador → `/FAULT` |

---

## SHEET 07 — STM32G474  (`sch/mcu_stm32.kicad_sch`)

### Componentes

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U1 | STM32G474VET6 | `Package_QFP:LQFP-100_14x14mm_P0.5mm` | `MCU_ST_STM32G4:STM32G474VETx` | |
| Y1 | 24 MHz HSE | `Crystal_SMD_3225-4Pin` | `Device:Crystal` | + 2× 18 pF |
| C_vdd | 10× 100 nF + 2× 4.7 µF | `C_0402`/`C_0805` | `Device:C` | 1 por par VDD/VSS |
| C_vcap | 2× 2.2 µF | `C_0603` | `Device:C` | pines VCAP |
| U2 | LDO 3V3 bajo ruido (`TLV75533`) | `SOT-23-5` | `Regulator_Linear` | `+3V3` |
| U3 | LDO 3V3 analógico (`ADM7154`) | `SOT-23` | — | `+3V3_ANA` desde `+5V` |
| FB1 | ferrita 600 Ω | `L_0603` | `Device:FerriteBead` | `+3V3`→`+3V3_ANA` (si no LDO propio) |
| J_SWD | 10 pin Cortex Debug | `PinHeader_2x05_P1.27mm` | `Connector_Generic` | SWD + SWO + NRST |
| NT1 | Net-Tie 2 | `NetTie-2_SMD_Pad0.5mm` | `Device:Net-Tie_2` | **AGND ↔ DGND** bajo VREF− |
| NT2 | Net-Tie 2 | `NetTie-2_SMD_Pad1.0mm` | `Device:Net-Tie_2` | **DGND ↔ PGND** en retorno de DC_N sense |
| SW1 | pulsador NRST | `SW_SPST_...` | `Switch` | |

### Mapa de pines (propuesta — verifícalo en STM32CubeMX contra tu paquete)

| Función | Periférico | Pines (LQFP100) | Net |
|---|---|---|---|
| PWM inversor U/V/W + comp. | TIM1_CH1/1N/2/2N/3/3N | PE9/PE8/PE11/PE10/PE13/PE12 | `PWM_H4..6` / `PWM_L4..6` |
| PWM AFE A/B/C + comp. | TIM8_CH1/1N/2/2N/3/3N | PC6/PA7/PC7/PB0/PC8/PB1 | `PWM_H1..3` / `PWM_L1..3` |
| Trigger ADC (centro PWM) | TIM1_CH4 / TIM8_CH4 | interno | — |
| Break (fallo HW) | TIM1_BKIN / BKIN2, TIM8_BKIN | PA6 / PE15 / PA0 | `/FAULT` (+ redundante) |
| ADC corrientes motor | ADC1_IN / ADC2_IN | PA0.. (elige) | `AIN_IMOT_U/V/W` |
| ADC corrientes red | ADC3/ADC4 | PB.. | `AIN_IAFE_A/B/C` |
| ADC V_dc, V_grid, V_mot, NTC | ADC5 + otros | — | `AIN_VDC`,`AIN_VGRID_*`,`AIN_VMOT_*`,`AIN_NTC1/2` |
| Encoder motor | TIM3_CH1/CH2 | PA6/PA7 (o PB4/PB5) | `ENC_A/ENC_B` (+ `ENC_Z`) |
| Enlace ESP32 | USART2_TX/RX | PA2/PA3 | `ISO_UART_TX/RX` (a sheet 10) |
| Heartbeat | GPIO EXTI | PB12/PB13 | `ISO_HB_A/ISO_HB_B` |
| Mando relés | GPIO | PD.. | `K1_DRV`,`K2_DRV`,`FAN_DRV` (a sheet 08) |
| Watchdog externo | GPIO | PD.. | `WDI` (a sheet 08) |
| Habilitación PWM global | GPIO | PD.. | `EN_PWR` (a sheet 05/08) |
| Chopper | TIM (1 ch) o GPIO+comp | PB.. | `PWM_BRK` |
| VREF+ | — | pin 22 (VREF+) | `VREF_ADC` |

### Reglas de tierra (esto define el ruteo — cierra sheet 07 con esto claro)

```
PGND  = retorno de potencia (DC-link, sources, Cf). Cobre pesado, zona laminada.
AGND  = referencia de sensores, op-amps, VREF. Vertido propio bajo la zona analógica.
DGND  = digital del STM32 y periferia lógica. Vertido bajo el MCU.
IOGND = isla del ESP32. AISLADA (sin net-tie a DGND).

Uniones (una sola por par):
   AGND ↔ DGND  en NT1, físicamente bajo el pin VREF− / punto de estrella del ADC.
   DGND ↔ PGND  en NT2, en el punto donde el sense de DC_N entra al acondicionamiento.
Ninguna señal cruza un "gap" entre vertidos. Sin plano partido bajo pistas.
```

---

## SHEET 08 — Protección HW + I/O  (`sch/protection_io.kicad_sch`)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U_CMP1..3 | comparador rápido ×4 (`TLV3604`, `LM339`) | `SOIC-14` | `Comparator:LM339` | OC/OV/OT con ventana + histéresis |
| U_OR1 | AND/OR lógico (`74LVC1G332`, `74LVC08`) | `SOT-23` | `74xGxxx` | agrega `OC*`,`OV`,`OT`,`FLT_1..6`,`UVLO`,`ESTOP` → `/FAULT` |
| U_LATCH | SR latch (`74LVC1G74` o discretos) | `SOT-23` | — | latch de `/FAULT`; RESET por SW2 |
| SW2 | pulsador RESET FALLA | `SW_Push` | `Switch` | |
| U_WDT | watchdog externo (`TPS3823`, `MAX6369`) | `SOT-23-5` | — | `WDI` del STM32; timeout → `/FAULT` + abre K1 |
| Q_K1..Q_FAN | MOSFET low-side (`AO3400`) + `D_fw` | `SOT-23` | `Q_NMOS` + `Device:D` | bobinas K1/K2/FAN/freno |
| J_ESTOP | bornera 2 vías contacto seco | `Screw_Terminal_01x02` | `Connector` | redundante, optoacoplado |
| U_ESTOPopto | `TLP293` ×2 | `SOIC-4` | `Isolator:` | e-stop → lógica + corte de K1 |
| D_LED_* | PWR/RUN/FAULT | `LED_0805` | `Device:LED` | + R |

```
Entradas a U_OR1:  OC_IAFE_A/B/C, OC_IMOT_U/V/W, OV_DC, OT, FLT_1..6, UVLO_BIAS, ESTOP_n
Salida:            /FAULT ─┬─ TIM1.BKIN / TIM1.BKIN2 / TIM8.BKIN   (PWM OFF por hardware)
                           ├─ U_LATCH.S    (queda enclavado)
                           └─ Q_K1 OFF     (abre contactor de línea)
RESET (SW2) sólo limpia el latch si /FAULT ya está inactivo (causa despejada).
WDI: pulso del STM32 cada < T_wdt; si falta → mismo camino que /FAULT.
```

---

## SHEET 09 — Aux + Bias  (`sch/psu_aux.kicad_sch`)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| J_AUX | bornera 24 Vdc | `Screw_Terminal_01x02` | `Connector` | fuente DIN externa |
| D_rev, TVS, F_aux | prot. entrada | — | `Device:D`,`Device:D_TVS`,`Device:Fuse` | reverse + surge + fusible |
| U_BUCK15 | 24→15 V (`LMR33630`) | `HSOP-8` | `Regulator_Switching` | `+15V` |
| U_BUCK5 | 24→5 V | `SOT-23` / módulo | — | `+5V` |
| U_LDO33 | 5→3V3 | `SOT-23-5` | `Regulator_Linear` | `+3V3` limpio |
| U_INV15 | 15→−15 V (`LM27762`/charge pump) | `WSON` | — | `-15V` si el AFE analógico lo pide |
| U_BIAS1..6 | DC-DC aislado 15 V→ +15/−4 V 2 W | huella módulo o `SN6505+trafo` | `Converter_DCDC` | `+15Vg n`,`-4Vg n`,`GNDg n` |
| U_ISO_ESP | DC-DC aislado 5→3V3 1 W | huella módulo | — | isla `+3V3_IO` / `IOGND` |
| U_SUP | supervisor / secuenciador (`TPS3808`) | `SOT-23` | — | habilita `EN_PWR` sólo con `+15V` y bias OK |
| C_bulk | 2× 470 µF/35 V + cerámicos | `CP_Radial` | `Device:C_Polarized` | en 24 V y 15 V |

```
Secuencia POR:  +15V y +15Vg1..6 estables  →  U_SUP libera  →  EN_PWR alto permitido.
Si cae cualquier bias de gate → UVLO_BIAS → /FAULT (sheet 08).
```

---

## SHEET 10 — Aislamiento Comms  (`sch/isolation_comms.kicad_sch`)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U_ISO1 | `ISO7741` (4 ch, 2F/2R config.) | `SOIC-16W` | `Isolator:ISO7741` | UART TX/RX + 2 líneas heartbeat |
| C_iso | 100 nF + 10 µF ×2 lados | `C_0603`,`C_0805` | `Device:C` | en VCC1/VCC2 pegados |
| J_DBG | header 4 pin | `PinHeader_1x04` | `Connector` | acceso al enlace para debug |
| (ranura) | fresado Edge.Cuts bajo U_ISO1 | — | — | si creepage de paquete < 4 mm |

```
Lado CTRL:  VCC1 ← +3V3 ; GND1 ← DGND ; INA ← ISO_UART_TX ; OUTB → ISO_UART_RX ;
            heartbeat: OUT/IN ↔ ISO_HB_A/B
Lado IO:    VCC2 ← +3V3_IO ; GND2 ← IOGND ; señales espejo al ESP32 (sheet 11)
SIN net-tie GND1↔GND2.
```

---

## SHEET 11 — ESP32-S3 IoT  (`sch/esp32_iot.kicad_sch`)

| Ref | Valor | Footprint | Símbolo | Notas |
|---|---|---|---|---|
| U_ESP | ESP32-S3-WROOM-1-N8 | `RF_Module:ESP32-S3-WROOM-1` | mismo | keep-out de antena |
| C_esp | 10 µF + 100 nF ×varios | `C_0805/0603` | `Device:C` | en 3V3 del módulo |
| U_USB | USB-C + `CH340`/nativo | `USB_C_Receptacle...` | `Connector` | consola / flash / OTA |
| SW_EN, SW_BOOT | pulsadores | `SW_Push` | `Switch` | + RC en EN |
| U_PHY (opc.) | `LAN8720A` + RJ45 magjack | `QFN-24`, `RJ45` | `lan8720` | Modbus TCP por Ethernet |
| J_FIELD | bornera para señales de campo aisladas | `Screw_Terminal` | `Connector` | DI/DO opcionales de planta |
| D_LED_IO | link / MQTT / fault-mirror | `LED_0805` | `Device:LED` | |

```
Alimentación: +3V3_IO / IOGND (de sheet 09/10).  O USB-C.  O PoE externo.
Enlace: UART aislado desde sheet 10.  RMII al PHY si se usa Ethernet.
Todo IOGND. Nada cruza a DGND salvo por U_ISO1.
```

---

## Checklist de salida de la captura (antes de pasar a PCB)

- [ ] ERC sin errores (warnings revisados uno a uno).
- [ ] Todas las etiquetas jerárquicas tienen par (sin nets colgando entre hojas).
- [ ] Cada net asignada a su net class correcta (revisar en Schematic Setup).
- [ ] `NT1` (AGND↔DGND) y `NT2` (DGND↔PGND) presentes y únicos. `IOGND` sin net-tie.
- [ ] BOM exportada; footprints asignados al 100 % (CvPcb) y verificados en 3D.
- [ ] Símbolos de fabricante (drivers, aisladores, ESP32, STM32) validados pin a pin
      contra el datasheet.
- [ ] Anotación final hecha (`Tools → Annotate`, sequential por hoja).
