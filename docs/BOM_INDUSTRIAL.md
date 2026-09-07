# BOM industrial — marcas y referencias reales

> Punto de diseño: **15 kVA · 400 V_LL · 60 Hz · V_dc ≤ 800 V · f_sw 16 kHz**.
> Todas las referencias son de catálogo vigente y de distribución habitual
> (Digi-Key / Mouser / Farnell / RS). Donde hay dos marcas, la primera es la
> recomendada y la segunda el segundo origen (*second source*).

---

## 1. Semiconductores de potencia

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| Q1–Q12 | 12 | SiC MOSFET 1200 V, 40 mΩ, TO-247-**4** (pin Kelvin) | **Wolfspeed** | `C3M0040120K` | **el que hay que montar**. 17.5 W/dispositivo |
| — | — | *2.º origen, pin-compatible* | Infineon | `IMZA120R030M1H` | CoolSiC 1200 V 30 mΩ |
| — | — | *el de la librería KiCad, 75 mΩ* | Wolfspeed | `C3M0075120K` | válido solo hasta ~10 kVA |
| QBRK | 1 | SiC chopper de frenado | Wolfspeed | `C3M0040120K` | mismo encapsulado |
| DBRK | 1 | Diodo SiC Schottky 1200 V / 30 A | Wolfspeed | `C4D20120A` | freewheel del chopper |
| — | 12 | Aislador térmico + tornillería TO-247 | Bergquist / Laird | `SIL-PAD 2000` + M3 | 0.3 °C/W |

## 2. Gate drivers y su alimentación

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| U11–U16 | 6 | Driver aislado doble, DESAT + Miller clamp, CMTI 150 V/ns | **Texas Instruments** | `UCC21750QDWRQ1` | **recomendado**: el CMTI de 150 V/ns cubre los 147 V/ns medidos |
| — | 6 | *alternativa del esquemático actual*, CMTI 100 V/ns | Texas Instruments | `UCC21520DW` | **exige el snubber de 220 pF** (ver §9) |
| — | 6 | *2.º origen* | STMicroelectronics | `STGAP2SMTR` | ecosistema ST, encaja con el STM32 |
| U_BIAS1–6 | 6 | DC-DC aislado 2 W, +15 V / −4 V, 5.2 kV | **Murata** | `MGJ2D152005SC` | bias por rama, referido al Kelvin |
| — | 6 | *2.º origen* | RECOM | `RxxP21505D` | |
| Rg_on | 12 | 10 Ω 1 W 2512, baja inductancia | Vishay | `CRCW251210R0FKEG` | |
| Rg_off | 12 | 3.3 Ω 1 W 2512 | Vishay | `CRCW25123R30FKEG` | |
| D_off | 12 | Diodo rápido 200 V SOD-123 | Nexperia | `BAV21WS` | |
| TVS_gs | 12 | Zener doble +20 / −6 V | Nexperia | `PESD2CAN` / `BZX84C18` | protección de gate |

## 3. Bus DC y precarga

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| C1–C4 | 4 | Condensador DC-link film 150 µF / 900 V DC | **TDK / EPCOS** | `B32778G8157K000` | 600 µF totales, sin equilibrado |
| — | 4 | *2.º origen* | KEMET | `C4AQLBW5150A3NJ` | |
| — | 4 | *2.º origen* | Vishay | `MKP1848S61590JY5` | |
| C5, C6 | 2 | Film HF 2.2 µF / 1 kV, desacoplo de lazo | KEMET | `C4AQOBW5220A3NJ` | pegado a cada rama |
| Cdec | 6 | Film 1 µF / 1 kV, lazo de conmutación | TDK | `B32656S1105K` | **< 10 mm del par de MOSFET** |
| RPC | 1 | Resistencia de precarga 68 Ω, 200 W, pulso ≥ 350 J | **Arcol** | `HS100 68R J` | bobinada, con brida |
| — | 1 | *2.º origen* | Ohmite | `TGHG 68R` | |
| K2 | 1 | Contactor de bypass de precarga, 25 A, bobina 24 VDC | Schneider | `LC1D25BD` | |
| RBLEED | 1 | Bleeder 100 kΩ 3 W | Vishay | `PR03000201003JAC00` | descarga < 60 V en < 60 s |
| RBRK | 1 | Resistencia de frenado 12 Ω, 1.5 kW (externa) | **Danotherm** | `CBH 165 C 12R` | **fuera del gabinete** |

## 4. Filtro LCL y EMC de entrada

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| L1A–C | 3 | Reactancia 1.5 mH / 30 A, lado convertidor | **Block** | `DPU 1.5-30` | núcleo de hierro, montaje en placa |
| — | 3 | *2.º origen* | Schaffner | `RWK 305-30` | |
| L2A–C | 3 | Reactancia 0.6 mH / 30 A, lado red | Block | `DPU 0.6-30` | |
| CFA–C | 3 | Condensador de filtro 10 µF / 500 VAC | **TDK / EPCOS** | `B32924C3106M000` | clase X2, conexión Y |
| RDA–C | 3 | Amortiguamiento **6.8 Ω / 10 W** | Arcol | `HS10 6R8 J` | **valor optimizado por simulación** |
| L_CM1 | 1 | Choke de modo común trifásico 3 mH / 30 A | **Schaffner** | `RN142-30-33` | |
| FIL1 | 1 | Filtro EMC trifásico 30 A, EN 55011 clase A | **Schaffner** | `FN3258-30-33` | entrada de red |
| L_CM2 | 1 | Choke de modo común de salida a motor | Schaffner | `RWK 305-30-KL` | reduce corriente de fuga |
| RV1–3 | 3 | Varistor 300 VAC / 20 mm, clase II | TDK / EPCOS | `B72220S0301K101` | |

## 5. Protección y maniobra

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| F1–F3 | 3 | Fusible ultrarrápido 25 A, 690 V, aR | **Mersen** | `FR14GG69V25` | protección de semiconductores |
| — | 3 | *2.º origen* | Eaton / Bussmann | `FWP-25A14F` | |
| — | 1 | Portafusibles 3P para 14×51 | Mersen | `US14 3P` | carril DIN |
| K1 | 1 | Contactor de línea 3P 25 A, bobina 24 VDC | **Schneider** | `LC1D25BD` | |
| — | 1 | *2.º origen* | Siemens | `3RT2026-1BB40` | |
| QS1 | 1 | Seccionador de carga 32 A con mando en puerta | Schneider | `VBF2` + `KCF1PZ` | enclavamiento de puerta |
| S_ESTOP | 1 | Seta de emergencia, 2 NC, IP66 | **Schneider** | `XALK178G` | contacto seco redundante |
| F10 | 1 | Fusible auxiliar 3 A, 5×20 | Schurter | `0034.3122` | |

## 6. Sensado

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| J10–J15 | 6 | Transductor Hall de lazo cerrado, ±50 A | **LEM** | `LKSR 50-NP` | 3 red + 3 motor |
| — | 6 | *2.º origen* | LEM | `HO 50-P/SP33` | salida en tensión |
| — | 6 | *alternativa: shunt + aislador* | Texas Instruments | `AMC1305M25` + shunt 1 mΩ Vishay `WSLP` | mejor exactitud, más firmware |
| U_V | 7 | Amplificador aislado, entrada alta Z | Texas Instruments | `AMC1311DWV` | Vdc + Vred + Vmotor |
| U20 | 1 | Amp. operacional dual, zero-drift | Texas Instruments | `OPA2320AIDR` | acondicionamiento |
| U_REF | 1 | Referencia 3.000 V, 3 ppm/°C | **Texas Instruments** | `REF5030AIDR` | referencia del ADC |
| RT1, RT2 | 2 | NTC 10 kΩ B3950 con terminal a tornillo | **Vishay** | `NTCALUG03A103G` | disipador y módulo |
| Rburden | 6 | 100 Ω 0.1 % 25 ppm 1206 | Susumu | `RG3216P-101-B-T5` | precisión del sensado |
| Rdiv | 35 | 200 kΩ 0.1 % 25 ppm 1206, 200 V | Vishay | `MMB02070C2003FB200` | divisores de alta tensión |

## 7. Control y comunicaciones

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| U1 | 1 | MCU Cortex-M4F 170 MHz, HRTIM, 5×ADC, CORDIC | **STMicroelectronics** | `STM32G474VET6` | LQFP-100 |
| U50 | 1 | Aislador digital cuádruple 3F/1R, reforzado | **Analog Devices** | `ADuM1401ARWZ` | barrera STM32↔ESP32 |
| — | 1 | *2.º origen* | Texas Instruments | `ISO7741DWR` | |
| U60 | 1 | Módulo Wi-Fi/BT, 8 MB flash | **Espressif** | `ESP32-S3-WROOM-1-N8` | telemetría |
| U30 | 1 | Comparador cuádruple | Texas Instruments | `LM339DR` | cadena de falla |
| — | 1 | *recomendado: comparador rápido* | Texas Instruments | `TLV3604DCKR` | 1.4 ns, mejor para OC |
| U_WDT | 1 | Supervisor con watchdog | Texas Instruments | `TPS3823-33DBVR` | |
| X1 | 1 | Cristal 24 MHz ±10 ppm 3225 | Abracon | `ABM8G-24.000MHZ-4Y-T3` | |
| U40–42 | 3 | Reguladores 24→15→5→3.3 V | Texas Instruments | `LMR33630ADDA`, `TLV75833PDBVR` | |
| PSU1 | 1 | Fuente 24 V / 60 W, carril DIN | **Mean Well** | `DR-60-24` | auxiliar |
| — | 1 | *2.º origen industrial* | Phoenix Contact | `QUINT4-PS/1AC/24DC/2.5` | |

## 8. Borneras, conectores y cableado industrial

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| — | 4 | Bornera de potencia carril DIN 16 mm², 76 A | **Phoenix Contact** | `UK 16 N` (3004362) | L1/L2/L3/PE de red |
| — | 4 | idem para salida a motor | Phoenix Contact | `UK 16 N` | U/V/W/PE |
| — | 2 | Bornera de freno 10 mm² | Phoenix Contact | `UK 10 N` (3005073) | |
| — | 1 | Bornera de tierra a carril | Phoenix Contact | `USLKG 16` (3005044) | PE principal |
| — | 20 | Bornera de control 2.5 mm², resorte | **Weidmüller** | `A2C 2.5` (1991760000) | señales |
| — | 20 | *2.º origen* | Wago | `2002-1201` TOPJOB S | |
| — | 6 | Tapa final + tope de bornera | Phoenix Contact | `D-UK 16`, `CLIPFIX 35` | |
| J_MOT / J1 | 2 | Bornera de PCB 4 vías, 16 A, 5 mm | Phoenix Contact | `MKDSN 1,5/4-5,08` | en placa |
| — | 2 | Prensaestopas M32 metálico, apantallado EMC | **Lapp** | `SKINTOP MS-SC-M32` | red y motor, malla 360° |
| — | 1 | Prensaestopas M25 apantallado | Lapp | `SKINTOP MS-SC-M25` | freno |
| — | 2 | Prensaestopas M20 | Lapp | `SKINTOP ST-M20` | señal |
| — | 1 | Carril DIN 35 mm perforado, 1 m | Phoenix Contact | `NS 35/7,5 PERF` | |
| — | 20 m | Canaleta ranurada 40×60 | Phoenix Contact | `CD 40×60` | |
| — | — | Cable de motor apantallado 4G6 | **Lapp** | `ÖLFLEX SERVO 2YSLCY-JB` | malla al prensaestopas |
| — | — | Cable de señal apantallado 2×0.75 | Lapp | `UNITRONIC LiYCY` | sensores |

## 9. Mecánica, refrigeración y gabinete

| Ref | Cant | Descripción | Marca | Referencia (MPN) | Notas |
|---|:-:|---|---|---|---|
| GAB | 1 | Armario mural chapa 800×600×300, IP66 | **Rittal** | `AE 1180.500` | con placa de montaje |
| — | 1 | *2.º origen* | Hammond | `1418N4L16couplé` / Fibox `ARCA` | |
| VENT | 1 | Ventilador con filtro 180 m³/h, 24 V | **Rittal** | `SK 3241.100` | **obligatorio** (ver §10) |
| SAL | 1 | Rejilla de salida con filtro | Rittal | `SK 3243.100` | |
| DIS | 1 | Disipador perfilado 200 mm, Rth 0.3 °C/W | **Fischer Elektronik** | `SK 92 / 200 SA` | los 12 SiC |
| — | 1 | *2.º origen* | Aavid / Boyd | `0S523/200` | |
| FAN2 | 1 | Ventilador axial 24 V 120 mm sobre disipador | **ebm-papst** | `4114 N/2H8P` | |
| — | 1 | Termostato de gabinete NC 60 °C | Rittal | `SK 3110.000` | alarma térmica |
| — | 4 | Separadores M3 hexagonales 15 mm | Würth | `970150151` | montaje de PCB |

## 10. Hallazgos de la simulación que afectan al BOM

Estos puntos **no** son de catálogo: salen de `sim/` y `spice/`.

1. **`Rd` de amortiguamiento del LCL: 6.8 Ω, no 2.2 Ω.**
   Con 2.2 Ω el pico de resonancia queda en 26 dB (inaceptable). Con 6.8 Ω baja
   a 19 dB por 12 W totales. Barrido completo en `sim/run_all.py`.

2. **`dv/dt` medido en SPICE: 147 V/ns.** Lo fija `I_carga / C_oss`, **no** el
   resistor de gate (verificado barriendo `Rg_off` de 6.8 a 47 Ω: sin efecto).
   Dos salidas válidas:
   - **Driver con más CMTI**: `UCC21750` (150 V/ns) en vez de `UCC21520`
     (100 V/ns). **Es la opción recomendada.**
   - **Snubber RC de 220 pF + 4.7 Ω** por rama: baja el `dv/dt` a 90 V/ns y la
     sobretensión de 817 a 767 V, a costa de 10 W en los 12 dispositivos.
     Referencia: KEMET `C0G 220pF 1kV 1210` + Vishay `CRCW25124R70`.

3. **Sobretensión vs inductancia de lazo** (SPICE, doble pulso a 700 V / 30 A):

   | Lazo | Pico | Margen a 1200 V |
   |---:|---:|---|
   | 5 nH | 745 V | holgado |
   | **20 nH** | **817 V** | **objetivo del diseño** |
   | 60 nH | 923 V | justo |
   | 150 nH | 1170 V | **al límite de rotura** |

   Esto justifica numéricamente la regla de layout del floorplan.

4. **Ventilación forzada obligatoria.** 298 W dentro del gabinete; por
   convección natural el interior llegaría a 65 °C. El `SK 3241.100`
   (180 m³/h) da 95 % de margen sobre los 92 m³/h necesarios.

5. **Con el `C3M0075120K` (75 mΩ) de la librería**, `Rth_s-a` baja a
   0.16 °C/W — inviable con aire. **Hay que montar el `C3M0040120K`.**

---

## 11. Normativa aplicable al conjunto montado

| Norma | Qué exige aquí |
|---|---|
| **IEC 61800-5-1** | Seguridad del accionamiento: aislamiento, distancias, descarga del bus < 60 V en < 60 s, ensayo dieléctrico |
| **IEC 61800-3** | EMC del accionamiento (categoría C2 para entorno industrial) |
| **IEC 60204-1** | Equipo eléctrico de máquinas: seta de emergencia, seccionador con enclavamiento, colores de cable, PE |
| **IEEE 519 / IEC 61000-3-12** | THD de corriente de red < 5 % — validado en simulación: **0.09 %** |
| **IEC 60664-1** | Coordinación de aislamiento (las reglas DRC de `kicad/drc_custom_rules.txt`) |
| **IEC 60529** | Grado de protección IP66 del `AE 1180.500` |
