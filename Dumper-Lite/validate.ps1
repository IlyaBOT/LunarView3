$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$liteKicadTools = @(Get-ChildItem -Path "$env:ProgramFiles\KiCad\*\bin\kicad-cli.exe" -ErrorAction SilentlyContinue)
if (-not $liteKicadTools.Count) { throw 'Installed kicad-cli.exe not found.' }
$liteKicad = $liteKicadTools | Sort-Object { [version](Split-Path -Leaf (Split-Path -Parent (Split-Path -Parent $_.FullName))) } | Select-Object -Last 1
$litePython = (Get-Command python.exe -ErrorAction Stop).Source
New-Item -ItemType Directory -Force -Path validation | Out-Null
& $liteKicad.FullName version | Set-Content -LiteralPath validation/kicad_version.txt
& $liteKicad.FullName sch erc --format json --severity-all --exit-code-violations -o validation/erc.json NM27C512_Dumper_Lite.kicad_sch
if ($LASTEXITCODE -ne 0) { throw 'Lite ERC failed.' }
& $liteKicad.FullName sch export netlist --format kicadxml -o validation/netlist.xml NM27C512_Dumper_Lite.kicad_sch
if ($LASTEXITCODE -ne 0) { throw 'Lite netlist export failed.' }
& $liteKicad.FullName sch export pdf -o NM27C512_Dumper_Lite.pdf NM27C512_Dumper_Lite.kicad_sch
if ($LASTEXITCODE -ne 0) { throw 'Lite PDF export failed.' }
& $litePython ../tools/audit_lite.py
if ($LASTEXITCODE -ne 0) { throw 'Lite connectivity audit failed.' }
Write-Output 'Lite validation passed. No hardware was accessed or flashed.'
