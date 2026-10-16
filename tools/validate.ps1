param([switch]$BuildCommissioned)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$kicadTools = @(Get-ChildItem -Path "$env:ProgramFiles\KiCad\*\bin\kicad-cli.exe" -ErrorAction SilentlyContinue)
if (-not $kicadTools.Count) { throw 'Installed kicad-cli.exe not found.' }
$kicad = $kicadTools | Sort-Object { [version](Split-Path -Leaf (Split-Path -Parent (Split-Path -Parent $_.FullName))) } | Select-Object -Last 1
$python = (Get-Command python.exe -ErrorAction Stop).Source
New-Item -ItemType Directory -Force -Path validation | Out-Null
$version = & $kicad.FullName version
$version | Set-Content -LiteralPath validation/kicad_version.txt
foreach ($item in @(@('NM27C512_Dumper.kicad_sch','erc.json','netlist.xml','NM27C512_Dumper.pdf'), @('baseline_readonly/NM27C512_Dumper.kicad_sch','baseline_erc.json','baseline_netlist.xml','NM27C512_ReadOnly.pdf'))) {
    & $kicad.FullName sch erc --format json --severity-all --exit-code-violations -o (Join-Path validation $item[1]) $item[0]
    if ($LASTEXITCODE -ne 0) { throw "ERC failed: $($item[0])" }
    & $kicad.FullName sch export netlist --format kicadxml -o (Join-Path validation $item[2]) $item[0]
    if ($LASTEXITCODE -ne 0) { throw 'Netlist export failed.' }
    & $kicad.FullName sch export pdf -o (Join-Path validation $item[3]) $item[0]
    if ($LASTEXITCODE -ne 0) { throw 'PDF export failed.' }
}
& $python tools/audit_netlist.py
if ($LASTEXITCODE -ne 0) { throw 'Connectivity audit failed.' }
& $python -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath validation/host_tests.txt
if ($LASTEXITCODE -ne 0) { throw 'Host tests failed.' }
& ./firmware/build.ps1 | Tee-Object -FilePath validation/firmware_build_safe.txt
if ($BuildCommissioned) { & ./firmware/build.ps1 -Commissioned | Tee-Object -FilePath validation/firmware_build_commissioned.txt }
Write-Output "Validation passed using KiCad $version. Bench commissioning is still required for WRITE."
