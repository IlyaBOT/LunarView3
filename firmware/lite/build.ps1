param([Nullable[int]]$Revision, [string]$FirmwareVersion, [string]$DeviceName, [string]$BuildId, [string]$BuildDate, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$tool = Get-ChildItem -Path "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\avr-gcc\*\bin\avr-gcc.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
if (-not $tool) { throw 'Install the Arduino AVR Boards toolchain or point this script at avr-gcc.' }
$bin = Split-Path -Parent $tool.FullName
$outDir = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $PSScriptRoot 'build' }
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
# Generated macros override identity.h defaults without allocating SRAM.
$defines = [System.Collections.Generic.List[string]]::new()
if ($null -ne $Revision) {
    if ($Revision -lt 1 -or $Revision -gt 9999) { throw 'Revision must be 1..9999' }
    $defines.Add("#define DUMPER_REVISION $Revision")
}
foreach ($field in @(@('FirmwareVersion', $FirmwareVersion, 'FIRMWARE_VERSION'), @('DeviceName', $DeviceName, 'DUMPER_NAME'))) {
    if ($field[1]) {
        if ($field[1].Length -gt 48 -or $field[1] -notmatch '^[a-zA-Z0-9 ._()-]+$') { throw "Invalid $($field[0])" }
        $defines.Add('#define ' + $field[2] + ' "' + $field[1] + '"')
    }
}
if (-not $BuildDate) { $BuildDate = Get-Date -Format 'dd.MM.yyyy' }
if ($BuildDate -notmatch '^\d{2}\.\d{2}\.\d{4}$') { throw 'BuildDate must be dd.MM.yyyy' }
if (-not $BuildId) {
    $sourceHashes = @('main.c', 'protocol_core.h', 'identity.h', '../status_core.h') | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $_) -Algorithm SHA256).Hash }
    $taskHash = [System.Security.Cryptography.SHA256]::Create()
    try { $bytes = [Text.Encoding]::UTF8.GetBytes(($sourceHashes -join '') + ($defines -join ''))
        $BuildId = ([BitConverter]::ToString($taskHash.ComputeHash($bytes))).Replace('-', '').Substring(0, 10).ToLowerInvariant()
    } finally { $taskHash.Dispose() }
}
if ($BuildId -notmatch '^[a-zA-Z0-9._-]{1,24}$') { throw 'Invalid BuildId' }
$defines.Add('#define FIRMWARE_BUILD_ID "' + $BuildId + '"')
$defines.Add('#define FIRMWARE_BUILD_DATE "' + $BuildDate + '"')
$metadata = Join-Path $outDir 'build_metadata.h'
[IO.File]::WriteAllLines($metadata, $defines, [Text.Encoding]::ASCII)
$elf = Join-Path $outDir 'dumper_lite.elf' 
$hex = Join-Path $outDir 'dumper_lite.hex'
& $tool.FullName -mmcu=atmega328p -DF_CPU=16000000UL -include $metadata -std=gnu11 -Os -Wall -Wextra -Werror -ffunction-sections -fdata-sections '-Wl,--gc-sections' -o $elf (Join-Path $PSScriptRoot 'main.c')
if ($LASTEXITCODE -ne 0) { throw 'avr-gcc failed' }
& (Join-Path $bin 'avr-objcopy.exe') -O ihex -R .eeprom $elf $hex
if ($LASTEXITCODE -ne 0) { throw 'avr-objcopy failed' }
& (Join-Path $bin 'avr-size.exe') -C --mcu=atmega328p $elf
if ($LASTEXITCODE -ne 0) { throw 'avr-size failed' }
Write-Output "HEX: $hex"
