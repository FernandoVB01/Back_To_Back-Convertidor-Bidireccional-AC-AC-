# Convertidor Back-to-Back (AFE + Inversor Trifásico) con Telemetría IoT
## Plan Maestro de Implementación — Hardware, PCB (KiCad), Firmware y Bring-up

> Documento raíz. Cada fase tiene su archivo propio en `docs/`. Las reglas de
> diseño de KiCad están en `kicad/`. Léelo en orden; no saltes al ruteo sin
> haber cerrado el dimensionamiento.

---

## 0. Filosofía del proyecto

Estás construyendo un **convertidor back-to-back**: dos puentes trifásicos de
2 niveles que comparten un **bus DC** común.

```
   RED 3~                 BUS DC (hasta 800 V)                 MOTOR 3~
 ┌────────┐   ┌──────┐   ┌───────────────┐   ┌──────┐   ┌────────────┐
 │ 400 V  │───│ LCL  │───│  AFE          │═══│ C_dc │═══│  INVERSOR  │───│ PMSM/IM │
 │ 60 Hz  │   │filtro│   │ (rectificador │   │ bank │   │  (FOC)     │
 └────────┘   └──────┘   │  activo PWM)  │   └──┬───┘   └────────────┘
                         └───────────────┘      │
                                          ┌─────┴──────┐
                                          │ Chopper de │  (resistencia de frenado
                                          │ frenado    │   como respaldo)
                                          └────────────┘
```

- El **AFE (Active Front End)** reemplaza al rectificador de diodos. Controla el
  bus DC, impone **factor de potencia unitario** (o el que ordenes) y, sobre
  todo, permite **devolver energía a la red** durante el frenado regenerativo.
- El **inversor** acciona el motor con **Control Orientado al Campo (FOC)**.
- Cuando el motor frena, la energía cinética vuelve al bus DC → el AFE la
  inyecta a la red. El chopper solo actúa si la red cae o el bus se dispara.

**Dos dominios eléctricos, físicamente separados en la PCB:**

| Dominio | Contenido | Referencia |
|---|---|---|
| **Potencia** | LCL, puentes AFE/inversor, bus DC, precarga, drivers de gate (lado caliente) | PGND, rieles de gate flotantes |
| **Control** | STM32, acondicionamiento analógico, ADC, comparadores de protección | AGND / DGND (unidos en un punto) |
| **IoT** | ESP32, Ethernet/Wi-Fi, conectores de campo | IOGND (aislado del control) |

La **barrera de aislamiento galvánico** cruza la PCB de lado a lado: separa
potencia↔control (seguridad, IEC 61800-5-1) y control↔IoT (funcional, anti-ruido).

---

## 1. Punto de diseño ANCLA

Todos los números de las fases usan esta especificación. **Cámbiala por la tuya
y re-ejecuta las fórmulas** — cada cálculo está parametrizado.

| Parámetro | Símbolo | Valor ancla | Nota |
|---|---|---|---|
| Potencia aparente nominal | S | **15 kVA** | dimensiona magnéticos, semiconductores, cobre |
| Tensión de red (línea-línea) | V_LL | **400 V** RMS | si tu red es 220 V_LL, bus ≈ 400–450 V: reescala todo |
| Frecuencia de red | f_g | **60 Hz** | Ecuador; usa 50 Hz si aplica |
| Tensión de fase | V_ph | 231 V RMS | V_LL/√3 |
| Corriente nominal | I_n | **21.65 A** RMS | S/(√3·V_LL) |
| Corriente de pico nominal | I_pk | 30.6 A | √2·I_n |
| Bus DC nominal | V_dc | **700 V** | referencia de regulación del AFE |
| Bus DC máximo (rating componentes) | V_dc,max | **800 V** | umbral de disparo duro |
| Umbral chopper de frenado | V_dc,chop | **760–780 V** | antes del disparo duro |
| Frecuencia de conmutación | f_sw | **16 kHz** | AFE e inversor; viable con SiC |
| Frecuencia lazo de corriente | f_c | **16 kHz** | 1 ejecución por periodo PWM |
| Frecuencia lazo de velocidad/bus | — | **1–2 kHz** | lazo externo |
| Temperatura ambiente de diseño | T_a | **45 °C** | interior de gabinete |
| Tj objetivo (semiconductores) | T_j | **≤ 125 °C** | derate desde 175 °C |

### Impedancias base (para pu)

```
Z_base = V_LL² / S              = 400² / 15000        = 10.67 Ω
L_base = Z_base / (2π·f_g)      = 10.67 / 376.99      = 28.3 mH
C_base = 1 / (2π·f_g·Z_base)    = 1 / 4021            = 248.7 µF
```

---

## 2. Arquitectura de control (quién manda a quién)

```
                 ┌─────────────────────── STM32G474 (dominio control) ───────────────────────┐
                 │                                                                            │
  Red ─► AFE  ───┤  PLL trifásico (SRF/DSOGI) ─► θ_grid                                        │
                 │  Lazo Vdc (PI, ~1 kHz) ─► Id*        Lazo corriente dq (PI, 16 kHz) ─► SVPWM├─► gate AFE
                 │  Iq* = 0 (FP unitario) / cmd FP                                             │
                 │                                                                            │
  Motor ◄─ INV ──┤  Encoder/observador ─► θ_rotor                                              │
                 │  Lazo velocidad (PI, ~1 kHz) ─► Iq*  Lazo corriente dq (FOC, 16 kHz) ─►SVPWM├─► gate INV
                 │  Id* = 0 (o field weakening)                                                │
                 │                                                                            │
                 │  Máquina de estados · Protecciones HW (BKIN) · ADC sinc. con PWM            │
                 └───────────────┬───────────────────────────────────────────┬────────────────┘
                                 │ UART/SPI AISLADO (telemetría + setpoints no críticos)      │
                 ┌───────────────┴───────────────┐                                            │
                 │  ESP32 (dominio IoT)          │                                            │
                 │  Modbus TCP · MQTT/TLS · OTA  │──► Node-RED (dashboard mant. predictivo)   │
                 └──────────────────────────────┘
```

**Regla de oro:** el ESP32 **nunca** está en un lazo de par/seguridad. Solo lee
telemetría y propone setpoints que el STM32 **valida, limita y puede ignorar**.

---

## 3. Secuencia de desarrollo (orden de ejecución)

| # | Fase | Entregable | Bloqueante para |
|---|---|---|---|
| 1 | **Dimensionamiento y arquitectura de potencia** (`01_...md`) | LCL, banco C_dc, precarga, semiconductores, térmico | todo |
| 2 | **Esquemático y acondicionamiento** (`02_...md`) | Gate drivers, cadena analógica, aislamiento comms | PCB |
| 3 | **Ruteo de PCB y normativas** (`03_...md`) | Stackup, net classes, creepage/clearance, reglas DRC (`kicad/`) | fabricación |
| 4 | **Firmware de control STM32** (`04_...md`) | Timers/SVPWM/dead-time, ADC sinc., FOC + PLL/AFE | bring-up lazo cerrado |
| 5 | **Telemetría IoT y SCADA ESP32** (`05_...md`) | Protocolo STM32↔ESP32, Modbus/MQTT, Node-RED | puesta en servicio |
| 6 | **Protocolo de pruebas y seguridad** (`06_...md`) | Bring-up escalonado, fuentes limitadas, validación lazo abierto | operación |

Regla práctica: **Fases 1–3 en serie. Fase 4 puede arrancar en paralelo a la 3
usando una Nucleo/Discovery. Fase 5 en paralelo a la 4. Fase 6 solo cuando 1–4
estén cerradas y la placa fabricada y poblada por secciones.**

---

## 4. Estructura del proyecto KiCad

### 4.1 Esquemático jerárquico

```
b2b_converter.kicad_sch                 (raíz: interconexión de hojas, net classes)
├── sch/ac_input_lcl.kicad_sch          entrada AC, fusibles, contactor, LCL, snubber
├── sch/afe_bridge.kicad_sch            6× SiC + Kelvin, decoupling de lazo de conmutación
├── sch/dclink_precharge.kicad_sch      banco C_dc, R de balance, precarga (R + contactor), bleeder, chopper
├── sch/inverter_bridge.kicad_sch       6× SiC + Kelvin, decoupling
├── sch/gate_driver.kicad_sch           ← SUBHOJA REUTILIZABLE, instanciada 6× (o 2× por 3 canales)
├── sch/sense_iv.kicad_sch              sensores Hall / amp. aislados I y V, filtros anti-alias
├── sch/mcu_stm32.kicad_sch             STM32G474, cristal, SWD, refs de ADC
├── sch/protection_io.kicad_sch         comparadores OV/OC, lógica BKIN, relés, e-stop, watchdog
├── sch/psu_aux.kicad_sch               SMPS auxiliar (flyback desde bus o desde 24 V), bias aislados de gate
├── sch/isolation_comms.kicad_sch       aisladores digitales UART/SPI, DC-DC aislado isla ESP32
└── sch/esp32_iot.kicad_sch            ESP32-S3, PHY Ethernet opcional, conectores de campo
```

- La subhoja `gate_driver.kicad_sch` se instancia 6 veces con parámetros de
  hoja distintos (nombre de red de gate, de fuente Kelvin, de bias). Un solo
  archivo a mantener.
- Cada hoja lleva su **rótulo de tensión de trabajo** en la carátula.

### 4.2 Net classes (ver `kicad/netclasses.md` y `kicad/drc_custom_rules.txt`)

| Net class | Nets | Tensión trabajo | Ancho mín. pista |
|---|---|---|---|
| `HV_DC` | DC+, DC-, nodos de fase de puente | 800 V DC | por térmico (≥ 2.5 mm en 2 oz) |
| `HV_AC` | L1/L2/L3 red, salidas motor U/V/W | 566 V pk | idem |
| `GATE_HS` | rieles de gate flotantes (alto lado) | 800 V (referido a PGND) | 0.4 mm |
| `GATE_LS` | gate lado bajo | 30 V | 0.4 mm |
| `CTRL` | 3V3 digital STM32 | 3.3 V | 0.2 mm |
| `ANA` | señales de sensores, refs ADC | ±10 V | 0.25 mm, guardadas |
| `IO_ISO` | dominio ESP32 (aislado) | 3.3 V | 0.2 mm |
| `PE` | tierra de protección / chasis | — | ancha, stitching |

### 4.3 Stackup (mínimo recomendado: 4 capas)

| Capa | Uso | Cobre |
|---|---|---|
| L1 (top) | señales de potencia, DC+ (laminado con L4 en zona de puente), gate loops | 70 µm (2 oz) |
| L2 | **PGND** sólido bajo la zona de potencia; AGND sólido bajo la zona analógica (misma capa, un solo net-tie) | 35 µm |
| L3 | plano de alimentación (3V3, 15 V, bias) + islas | 35 µm |
| L4 (bottom) | DC-, retorno de conmutación (laminado con L1), señales de control, plano DGND bajo el MCU | 70 µm (2 oz) |

Para EMI más exigente o mayor densidad: 6 capas (Sig / GND / Pwr / GND / Sig / Sig).

---

## 5. Lista de estándares aplicables

| Estándar | Aplicación en este proyecto |
|---|---|
| **IEC 61800-5-1** | Seguridad de accionamientos (PDS): aislamiento, distancias, descarga del bus (<60 V en 60 s), ensayos dieléctricos |
| **IEC 60664-1** | Coordinación de aislamiento: clearance/creepage vs. tensión, categoría de sobretensión, grado de polución |
| **IPC-2221B** | Tabla 6-1: espaciamientos eléctricos en PCB por tensión (interno/externo, con/sin recubrimiento) |
| **IPC-2152** | Ampacidad de pistas vs. temperatura y sección de cobre |
| **IEEE 519 / IEC 61000-3-2/-3-12** | Límites de armónicos de corriente inyectados a la red (objetivo del filtro LCL y del control del AFE): **THD_i < 5 %** |
| **IEC 61000-6-2 / -6-4** | Inmunidad y emisión EMC en entorno industrial |
| **CISPR 11 / EN 55011** | Emisiones conducidas y radiadas del equipo |

---

## 6. Cómo usar este repositorio

```
docs/
  00_MASTER_PLAN.md          ← estás aquí
  01_potencia_dimensionamiento.md
  02_esquematico_acondicionamiento.md
  03_pcb_ruteo_normativas.md
  04_firmware_control_stm32.md
  05_telemetria_iot_scada.md
  06_bringup_pruebas_seguridad.md
kicad/
  netclasses.md              ← definición de net classes y anchos
  drc_custom_rules.txt       ← reglas custom de KiCad 8 (clearance + creepage)
  stackup.md                 ← detalle del apilado y control de impedancia
```

Cada archivo de fase termina con una **checklist de salida**: no pases a la
siguiente fase hasta marcarla completa.
