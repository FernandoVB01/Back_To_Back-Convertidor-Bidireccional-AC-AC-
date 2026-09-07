# ============================================================
#  run.ps1 - Lanzador unico del proyecto convertidor B2B
#
#  Uso:
#     .\run.ps1              todo, en orden
#     .\run.ps1 sim          solo simulacion y validacion
#     .\run.ps1 kicad        solo esquematico + PCB + render 3D
#     .\run.ps1 spice        solo LTspice
#     .\run.ps1 fw           solo firmware (header + comprobacion)
#     .\run.ps1 mech         solo gabinete
#     .\run.ps1 check        comprobar el entorno y salir
#
#  OJO: este proyecto usa DOS Python distintos y no son intercambiables.
#    - El de KiCad  -> tiene el modulo pcbnew   (gen_pcb, gen_schematic)
#    - Anaconda     -> tiene numpy/scipy/matplotlib (sim, spice, mech, fw)
#  El script elige el correcto en cada paso; no lo hagas a mano.
# ============================================================

param([string]$Etapa = 'all')

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# ---------------------------------------------------------- herramientas
$KIBIN   = 'C:\Program Files\KiCad\9.0\bin'
$KIPY    = Join-Path $KIBIN 'python.exe'          # el que trae pcbnew
$KICLI   = Join-Path $KIBIN 'kicad-cli.exe'
$LTSPICE = Join-Path $env:LOCALAPPDATA 'Programs\ADI\LTspice\LTspice.exe'
$PY      = 'python'                                # Anaconda (numpy/scipy/mpl)

function Titulo($t) {
    Write-Host ''
    Write-Host ('=' * 68) -ForegroundColor DarkCyan
    Write-Host "  $t" -ForegroundColor Cyan
    Write-Host ('=' * 68) -ForegroundColor DarkCyan
}

function Comprobar {
    Titulo 'Comprobacion del entorno'
    $ok = $true
    foreach ($h in @(@{n='KiCad python (pcbnew)'; p=$KIPY},
                     @{n='kicad-cli';            p=$KICLI},
                     @{n='LTspice';              p=$LTSPICE})) {
        if (Test-Path $h.p) { Write-Host ("  OK    " + $h.n) -ForegroundColor Green }
        else { Write-Host ("  FALTA " + $h.n + "  -> " + $h.p) -ForegroundColor Red; $ok = $false }
    }
    # Anaconda + paquetes
    try {
        $v = & $PY -c "import numpy,scipy,matplotlib;print(numpy.__version__)" 2>&1
        Write-Host "  OK    Anaconda python + numpy $v" -ForegroundColor Green
    } catch {
        Write-Host "  FALTA python con numpy/scipy/matplotlib" -ForegroundColor Red; $ok = $false
    }
    try {
        & $KIPY -c "import pcbnew" 2>&1 | Out-Null
        Write-Host "  OK    modulo pcbnew" -ForegroundColor Green
    } catch {
        Write-Host "  FALTA modulo pcbnew" -ForegroundColor Red; $ok = $false
    }
    if (-not $ok) { throw 'Faltan herramientas: revisa las rutas de arriba.' }
    return $ok
}

# ---------------------------------------------------------- etapas
function Etapa-Sim {
    Titulo '1/5  SIMULACION Y VALIDACION  (Anaconda)'
    Write-Host 'Genera: docs/INFORME_VALIDACION.md + sim/out/01..05*.png'
    & $PY sim\run_all.py
}

function Etapa-Spice {
    Titulo '2/5  SPICE EN LTSPICE  (Anaconda + LTspice)'
    Write-Host 'Genera: spice/net/*.net + sim/out/06..08*.png'
    & $PY spice\gen_spice.py
}

function Etapa-Fw {
    Titulo '3/5  FIRMWARE  (Anaconda)'
    Write-Host 'Genera b2b_config.h desde sim/b2b_params.py'
    & $PY fw\config\gen_config.py
    Write-Host ''
    Write-Host 'Comprobacion de la transliteracion C -> Python:'
    & $PY fw\verify\control_ref.py
}

function Etapa-Kicad {
    Titulo '4/5  KICAD: ESQUEMATICO + PCB + RENDER 3D'
    New-Item -ItemType Directory -Force render, export | Out-Null

    Write-Host '-- esquematico (python de KiCad) --' -ForegroundColor Yellow
    & $KIPY tools\gen_schematic.py
    Write-Host '-- conectividad --' -ForegroundColor Yellow
    & $KIPY tools\check_conn.py
    Write-Host '-- ERC --' -ForegroundColor Yellow
    & $KICLI sch erc --output export\erc.rpt --severity-all kicad\b2b_converter.kicad_sch |
        Select-String 'encontr|violation'
    Write-Host '-- netlist --' -ForegroundColor Yellow
    & $KICLI sch export netlist --output kicad\b2b_converter.net kicad\b2b_converter.kicad_sch |
        Select-Object -Last 1
    Write-Host '-- PCB --' -ForegroundColor Yellow
    & $KIPY tools\gen_pcb.py
    Write-Host '-- restaurar net classes (SaveBoard las borra) --' -ForegroundColor Yellow
    & $KIPY tools\restore_pro.py
    Write-Host '-- DRC --' -ForegroundColor Yellow
    & $KICLI pcb drc --output export\drc.rpt --severity-all kicad\b2b_converter.kicad_pcb |
        Select-String 'encontr|violation'
    Write-Host '-- planos PDF + render 3D --' -ForegroundColor Yellow
    & $KICLI sch export pdf --output export\b2b_esquematicos.pdf kicad\b2b_converter.kicad_sch |
        Select-Object -Last 1
    & $KICLI pcb render --output render\b2b_top.png --width 1700 --height 1250 `
        --side top --quality high kicad\b2b_converter.kicad_pcb | Select-Object -Last 1
    & $KICLI pcb render --output render\b2b_iso.png --width 1700 --height 1250 `
        --preset follow_pcb_editor --perspective --quality high `
        kicad\b2b_converter.kicad_pcb | Select-Object -Last 1

    Write-Host '-- esquemas simulables en KiCad --' -ForegroundColor Yellow
    & $PY tools\gen_kicad_sim.py
}

function Etapa-Mech {
    Titulo '5/5  GABINETE  (Anaconda)'
    & $PY mech\gen_gabinete.py
}

function Resumen {
    Titulo 'SALIDAS'
    $m = @(
        @{f='docs\INFORME_VALIDACION.md'; d='informe de validacion (31 comprobaciones)'},
        @{f='docs\BOM_INDUSTRIAL.md';     d='BOM con marcas y referencias'},
        @{f='render\b2b_iso.png';         d='render 3D de la PCB'},
        @{f='export\b2b_esquematicos.pdf';d='los 12 planos electricos'},
        @{f='sim\out';                    d='graficas de simulacion'},
        @{f='mech\out';                   d='planos del gabinete'},
        @{f='kicad\b2b_converter.kicad_pro'; d='PROYECTO KICAD (abrir aqui)'},
        @{f='kicad\sim';                  d='esquemas simulables con ngspice'}
    )
    foreach ($x in $m) {
        $mark = if (Test-Path $x.f) { 'OK  ' } else { '--  ' }
        $col  = if (Test-Path $x.f) { 'Green' } else { 'DarkGray' }
        Write-Host ("  $mark" + $x.f.PadRight(36) + $x.d) -ForegroundColor $col
    }
}

# ---------------------------------------------------------- main
Comprobar | Out-Null
switch ($Etapa.ToLower()) {
    'check' { }
    'sim'   { Etapa-Sim }
    'spice' { Etapa-Spice }
    'fw'    { Etapa-Fw }
    'kicad' { Etapa-Kicad }
    'mech'  { Etapa-Mech }
    'all'   { Etapa-Sim; Etapa-Spice; Etapa-Fw; Etapa-Kicad; Etapa-Mech; Resumen }
    default { throw "Etapa desconocida: $Etapa  (sim|spice|fw|kicad|mech|check|all)" }
}
Write-Host ''
Write-Host 'Listo.' -ForegroundColor Green
