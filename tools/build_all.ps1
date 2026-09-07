# build_all.ps1 - Regenera TODO el proyecto KiCad desde los scripts.
#   .\tools\build_all.ps1
#
# Cadena: esquematico -> ERC -> netlist -> PCB -> DRC -> PDF/SVG -> render 3D

$ErrorActionPreference = 'Stop'
$KI  = 'C:\Program Files\KiCad\9.0\bin'
$PY  = Join-Path $KI 'python.exe'
$CLI = Join-Path $KI 'kicad-cli.exe'
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT
New-Item -ItemType Directory -Force render, export | Out-Null

Write-Host "`n=== 1/7  Esquematico ===" -ForegroundColor Cyan
& $PY tools\gen_schematic.py

Write-Host "`n=== 2/7  Conectividad (verificador propio) ===" -ForegroundColor Cyan
& $PY tools\check_conn.py

Write-Host "`n=== 3/7  ERC ===" -ForegroundColor Cyan
& $CLI sch erc --output export\erc.rpt --severity-all kicad\b2b_converter.kicad_sch |
    Select-String 'encontr|violation'

Write-Host "`n=== 4/7  Netlist ===" -ForegroundColor Cyan
& $CLI sch export netlist --output kicad\b2b_converter.net kicad\b2b_converter.kicad_sch |
    Select-Object -Last 1

Write-Host "`n=== 5/7  PCB ===" -ForegroundColor Cyan
& $PY tools\gen_pcb.py

Write-Host "`n=== 6/7  DRC + planos ===" -ForegroundColor Cyan
& $CLI pcb drc --output export\drc.rpt --severity-all kicad\b2b_converter.kicad_pcb |
    Select-String 'encontr|violation'
& $CLI sch export pdf --output export\b2b_esquematicos.pdf kicad\b2b_converter.kicad_sch |
    Select-Object -Last 1
& $CLI sch export svg --output export\svg kicad\b2b_converter.kicad_sch |
    Select-Object -Last 1

Write-Host "`n=== 7/7  Render 3D ===" -ForegroundColor Cyan
& $CLI pcb render --output render\b2b_top.png --width 1700 --height 1250 `
    --side top --quality high kicad\b2b_converter.kicad_pcb | Select-Object -Last 1
& $CLI pcb render --output render\b2b_iso.png --width 1700 --height 1250 `
    --preset follow_pcb_editor --perspective --quality high `
    kicad\b2b_converter.kicad_pcb | Select-Object -Last 1
& $CLI pcb render --output render\b2b_bottom.png --width 1700 --height 1250 `
    --side bottom --quality high kicad\b2b_converter.kicad_pcb | Select-Object -Last 1

Write-Host "`nOK. Salidas en render\ y export\" -ForegroundColor Green
