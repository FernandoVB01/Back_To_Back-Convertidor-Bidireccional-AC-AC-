# Cómo ejecutar todas las simulaciones

> Hay **cuatro simuladores** distintos en este proyecto y cada uno responde a
> una pregunta diferente. Aquí está qué corre cada uno, cómo lanzarlo y qué
> deberías ver.

---

## Resumen: los cuatro simuladores

| # | Simulador | Responde a | Tarda |
|---|---|---|---|
| 1 | **Python** (`sim/`) | ¿El convertidor completo funciona? ¿Regenera de verdad? | 4 s |
| 2 | **LTspice** (`spice/`) | ¿Cuánta sobretensión mete el layout? ¿Cuál es el dv/dt real? | 2 min |
| 3 | **ngspice dentro de KiCad** (`kicad/sim/`) | Lo mismo, pero sobre el esquema dibujado | interactivo |
| 4 | **SIL del firmware** (`fw/verify/`) | ¿El código de control calcula bien? | 1 s |

**Todo de golpe:**

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

---

## 1. Simulación del sistema completo (Python)

La más importante: red → filtro LCL → AFE con PLL → bus DC → inversor con FOC
→ motor PMSM, con un **evento de frenado regenerativo**.

```powershell
.\run.ps1 sim
```
o directamente:
```powershell
python sim\run_all.py
```

**Qué produce**
- `docs/INFORME_VALIDACION.md` — las 31 comprobaciones con sus números
- `sim/out/01_lcl_bode.png` — respuesta del filtro LCL
- `sim/out/02_lazos_bode.png` — Bode de los lazos con el retardo de 1.5·Ts
- `sim/out/03_precarga.png` — transitorio de precarga e inrush
- `sim/out/04_b2b_temporal.png` — **la simulación completa**
- `sim/out/05_fase_regeneracion.png` — tensión vs corriente de red

**Qué mirar en `04_b2b_temporal.png`** (de arriba abajo):
1. El bus DC clavado en **700 V**, sin acercarse ni al chopper (770) ni al disparo (800)
2. El motor acelerando a 250 rad/s; a t = 0.35 s se ordena frenar
3. La potencia de red cruzando a **negativo (−11 kW)** → está devolviendo a la red
4. `Id` cambiando de signo mientras `Iq` sigue en 0 → **factor de potencia unitario**

Debe terminar en **`31/31 OK`**. Si alguna falla, el informe dice cuál y por qué.

### Cambiar el punto de diseño

Todo sale de `sim/b2b_params.py`. Cambia ahí la potencia, la tensión de red,
`f_sw`, los valores del LCL… y vuelve a lanzar. Se regeneran también el SPICE,
el `b2b_config.h` del firmware, el esquemático y el gabinete.

---

## 2. SPICE en LTspice

Lo que el modelo promediado no puede dar: el transitorio de conmutación real
con las **inductancias parásitas del layout**.

```powershell
.\run.ps1 spice
```
o:
```powershell
python spice\gen_spice.py
```

**Qué produce**
- `sim/out/06_spice_halfbridge.png` — sobretensión según la inductancia de lazo
- `sim/out/07_spice_lcl.png` — contraste del LCL: analítico vs SPICE
- `sim/out/08_spice_precarga.png` — precarga
- `spice/net/*.net` — los netlists, que **se pueden abrir a mano en LTspice**

**El resultado clave** (doble pulso a 700 V / 30 A):

| Inductancia de lazo | Pico en el nodo de conmutación |
|---:|---:|
| 5 nH | 753 V |
| **20 nH** (objetivo del floorplan) | **823 V** |
| 60 nH | 929 V |
| 150 nH | 1136 V ← al borde de romper el SiC de 1200 V |

Eso es lo que justifica numéricamente la regla de "lazo apretado".

### Abrirlos a mano en LTspice

```powershell
& "$env:LOCALAPPDATA\Programs\ADI\LTspice\LTspice.exe" spice\net\hb_20nH.net
```
Una vez abierto: **Simulate → Run**, y click en un nodo para graficarlo.

---

## 3. ngspice dentro de KiCad

Los mismos circuitos, pero dibujados como esquema de KiCad.

```powershell
python tools\gen_kicad_sim.py
```

Genera tres esquemas en `kicad/sim/`:

| Archivo | Análisis | Qué comprueba |
|---|---|---|
| `lcl_ac.kicad_sch` | `.ac dec 400 10 200k` | Resonancia en 2431 Hz, pico amortiguado de 19 dB |
| `halfbridge.kicad_sch` | `.tran 0.02n 5.2u` | Sobretensión según la parásita del lazo |
| `fw_bridge.kicad_sch` | `.tran 100n 187u` | Puente gobernado por el **PWM real del firmware** |

**Para simularlos:**
1. Abre el `.kicad_sch` en KiCad (doble clic)
2. **Inspeccionar → Simulador**
3. Botón **Ejecutar**
4. **Añadir señales** y elige qué graficar: `I(RL2)` en el LCL, `V(sw)` en el medio puente

El comando de análisis va escrito como texto en la propia hoja; puedes
editarlo ahí mismo.

### El interesante: `fw_bridge`

Sus seis fuentes de puerta **no son ondas inventadas**: son los flancos que
calcula el código de control real (SVPWM por inyección de secuencia cero) con
el dead-time de 500 ns del TIM1. KiCad **no ejecuta firmware** — no tiene
modelo de núcleo ARM — pero aquí su salida real gobierna el circuito.
Ver `docs/SIMULAR_FIRMWARE.md`.

### Verificación cruzada automática

```powershell
python tools\verify_kicad_sim.py
```
Exporta el netlist SPICE desde el esquema de KiCad, lo ejecuta y lo compara
con el modelo analítico. El LCL debe coincidir en **menos de 1 dB**.

---

## 4. SIL del firmware

Comprueba que la matemática de control es correcta y que las constantes del
firmware están sincronizadas con la simulación.

```powershell
.\run.ps1 fw
```
o:
```powershell
python fw\config\gen_config.py    # genera b2b_config.h desde b2b_params.py
python fw\verify\control_ref.py   # ejecuta la transliteración del C
```

**Qué deberías ver**
```
f_sw pedida = 16000.0 Hz   ARR = 5312   ->  f_sw real = 16001.51 Hz
dead-time pedido = 500 ns  DTG = 85 (0x55)  ->  real = 500.0 ns
SVPWM a modulacion lineal maxima -> duties 0.9330 0.0670 0.0670
```

Esos *duties* de 0.933/0.067 son exactamente el límite lineal del SVPWM
(±√3/4). Si salen otros, la modulación está mal.

---

## 5. El gabinete

```powershell
.\run.ps1 mech
```
Genera `mech/out/gabinete_frontal.png` y `gabinete_lateral.png`, y calcula la
ventilación: **298 W internos → hace falta ventilación forzada** (por
convección natural el interior llegaría a 65 °C).

---

## Si algo falla

**`ModuleNotFoundError: numpy`** → lanzaste con el Python de KiCad. Usa
`python` (Anaconda).

**`ModuleNotFoundError: pcbnew`** → al revés: usa
`"C:\Program Files\KiCad\9.0\bin\python.exe"`.

**`LTspice no encontrado`** → comprueba la ruta con `.\run.ps1 check`. Solo
afecta a la etapa `spice`; el resto funciona sin él.

**El `.raw` ocupa 100 MB** → normal en el puente trifásico: con 6 SiC
conmutando, LTspice refina el paso hasta el femtosegundo. Los esquemas de
`kicad/sim/` llevan una directiva `.save` para limitarlo.

**Comprobar el entorno entero:**
```powershell
.\run.ps1 check
```
