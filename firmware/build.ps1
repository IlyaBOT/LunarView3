param([switch]$Commissioned, [int]$BandgapMillivolts = 1100)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$avrTool = Get-ChildItem -Path "$env:LOCALAPPDATA\Arduino15\packages\arduino\tools\avr-gcc\*\bin\avr-gcc.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
if (-not $avrTool) { throw 'avr-gcc not found. Install an AVR toolchain or the Arduino AVR Boards toolchain.' }
$toolBin = Split-Path -Parent $avrTool.FullName
$tag = if ($Commissioned) { 'commissioned' } else { 'safe' }
$elf = Join-Path $PSScriptRoot "writer_$tag.elf"
$hex = Join-Path $PSScriptRoot "writer_$tag.hex"
$opts = @('-mmcu=atmega328p','-Os','-std=gnu11','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',"-DBANDGAP_MV=$BandgapMillivolts")
if ($Commissioned) { $opts += '-DHARDWARE_COMMISSIONED=1' }
& $avrTool.FullName @opts -o $elf (Join-Path $PSScriptRoot 'main.c')
if ($LASTEXITCODE -ne 0) { throw 'Firmware compilation failed.' }
& (Join-Path $toolBin 'avr-objcopy.exe') -O ihex -R .eeprom $elf $hex
if ($LASTEXITCODE -ne 0) { throw 'HEX export failed.' }
& (Join-Path $toolBin 'avr-size.exe') -C --mcu=atmega328p $elf
if ($LASTEXITCODE -ne 0) { throw 'Size check failed.' }
Write-Output "Built $hex using $($avrTool.FullName)"
