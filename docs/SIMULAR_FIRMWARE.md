# Simular el firmware: qué se puede y qué no

> Respuesta directa a "¿se puede cargar el firmware en Proteus / KiCad y
> simularlo?". La conclusión honesta primero, y luego lo que sí funciona.

---

## 1. Proteus — sí co-simula firmware, pero no éste

Proteus VSM **sí** ejecuta un `.hex`/`.elf` dentro de un modelo de MCU y lo
co-simula con el circuito. Eso es real y es su mayor virtud. **Pero para este
proyecto no sirve**, por tres razones concretas:

**a) No existe el modelo del STM32G474.** Comprobado en tu instalación
(`Proteus 8 Professional`), sus librerías de núcleo ARM contienen exactamente:

| Librería | Dispositivos soportados |
|---|---|
| `CM3_STM32.LIB` | STM32F103 C4/C6/C8, R4/R6, T4/T6 |
| `CM4_STM32.LIB` | STM32F401 CB/CC/CD/CE, RB/RC/RD/RE, VB/VC/VD/VE |

No hay familia G. Ni una referencia.

**b) Aunque lo hubiera, este diseño vive de periféricos que VSM no modela con
fidelidad**: salidas complementarias del timer avanzado con **inserción de
dead-time por hardware**, entradas `BKIN` de parada, y **conversiones
inyectadas del ADC disparadas por el timer en el centro del PWM**. Proteus
modela bien el núcleo; los rincones del periférico avanzado son justo donde
sus modelos flaquean — y esos rincones *son* el diseño.

**c) Escala de tiempo.** Co-simular el lazo de 16 kHz durante los 0.6 s del
ensayo de frenado son ~10 000 periodos de PWM con paso analógico
sub-microsegundo. Eso en Proteus son horas o días, y la parte analógica de un
convertidor de 15 kVA no es su fuerte.

## 2. KiCad — no ejecuta firmware, punto

El simulador de KiCad es **ngspice**: un simulador de circuito puro. No tiene
modelo de núcleo ARM ni forma de ejecutar código. Eso no va a cambiar.

## 3. Lo que sí se hace (y es lo que hace la industria)

En control de motores nadie valida el firmware metiendo el MCU en un
simulador de circuito. Se hace en tres capas, y las tres están montadas aquí:

### Capa 1 — SIL: el algoritmo real contra la planta validada

`fw/verify/control_ref.py` es la **transliteración literal** de
`fw/Core/Inc/b2b_control.h`: mismo PI con anti-windup, misma Clarke/Park,
mismo SVPWM por inyección de secuencia cero, mismo PLL normalizado.

Y no duplica constantes: **lee los `#define` directamente de
`b2b_config.h`**, que a su vez lo genera `fw/config/gen_config.py` desde
`sim/b2b_params.py`. Cadena completa:

```
sim/b2b_params.py  ──►  gen_config.py  ──►  b2b_config.h  ──►  firmware C
       │                                          │
       └──► simulación validada                   └──► control_ref.py (SIL)
```

Si cambias un parámetro, todo se regenera y nada se desincroniza.

### Capa 2 — el PWM real del firmware dentro del circuito de KiCad

`kicad/sim/fw_bridge.kicad_sch` es un puente trifásico SiC completo cuyas seis
fuentes de puerta **no son formas de onda inventadas**: son los flancos que
produce el código de control real, incluyendo el dead-time de 500 ns que
inserta el `TIM1`. Los genera `tools/gen_kicad_sim.py` llamando a
`control_ref.py` y volcando el resultado como fuentes `VPWL`.

O sea: el firmware no *se ejecuta* dentro de KiCad, pero **su salida real sí
gobierna el circuito**. Para validar la capa de modulación (que es lo que
querrías comprobar en Proteus) esto da más información y corre en segundos.

### Capa 3 — HIL, cuando exista la placa

Con el hardware fabricado: PWM a un puente de baja tensión, cargas RL, sondas
diferenciales. Es el paso 5 del `docs/06_bringup...` (pendiente de escribir).

## 4. Los tres esquemas simulables en KiCad

En `kicad/sim/`. Se abren y se simulan con **Inspeccionar → Simulador**.

| Archivo | Análisis | Qué comprueba |
|---|---|---|
| `lcl_ac.kicad_sch` | `.ac dec 400 10 200k` | Resonancia del LCL en 2431 Hz y pico amortiguado de 19 dB |
| `halfbridge.kicad_sch` | `.tran 0.02n 5.2u` | Sobretensión de conmutación según la inductancia del lazo |
| `fw_bridge.kicad_sch` | `.tran 20n 375u` | Puente gobernado por el PWM real del firmware |

`sic.lib` lleva el modelo VDMOS del SiC (aproximado: sirve para evaluar
parásitas de layout, no para pérdidas exactas).

### Verificación cruzada

`tools/verify_kicad_sim.py` cierra el círculo:

```
esquema de KiCad  →  kicad-cli exporta netlist SPICE  →  se ejecuta
                  →  se compara con el modelo analítico validado
```

Tres modelos independientes (analítico, LTspice y el circuito dibujado en
KiCad) tienen que dar lo mismo. Si divergen, hay un error en alguno.

## 5. Si aun así quieres ver co-simulación en Proteus

Es legítimo como demostrador didáctico. El camino honesto sería un
**STM32F401** (sí soportado) corriendo una versión *reducida* del control:
generación de SVPWM con dead-time sobre un puente trifásico de baja tensión.

Dos avisos: **(a)** valida la lógica de modulación, no el firmware del G474 —
los periféricos son distintos; **(b)** el formato de proyecto de Proteus
(`.pdsprj`) es binario propietario y no lo puedo generar: tendrías que montar
el esquema a mano, yo te daría el firmware del F401 y la lista de conexiones.

Dímelo si lo quieres y lo preparo.
