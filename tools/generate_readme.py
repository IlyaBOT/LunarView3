"""Generate documentation tables from the audited BOM and profile manifest."""
from collections import defaultdict
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def table(head,rows):
    return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |',
        *['| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows]])+'\n'
def main():
    bom=json.loads((ROOT/'validation/bom.json').read_text())
    base=json.loads((ROOT/'validation/baseline_bom.json').read_text())
    audit=json.loads((ROOT/'validation/connectivity_audit.json').read_text())
    profiles=json.loads((ROOT/'device_profiles.json').read_text())['profiles']
    mcu=next(p for p in bom if p['ref']=='U1')['nets']
    eprom=next(p for p in bom if p['ref']=='U6')['nets']
    header=json.loads((ROOT/'validation/target_header.json').read_text())
    gpio=['PD3','PD4','GND','VCC','GND','VCC','PB6 / XTAL1','PB7 / XTAL2','PD5','PD6','PD7','PB0','PB1','PB2','PB3 / MOSI','PB4 / MISO',
          'PB5 / SCK','AVCC','ADC6','AREF','GND','ADC7','PC0','PC1','PC2','PC3','PC4','PC5','PC6 / RESET','PD0 / RXD','PD1 / TXD','PD2']
    group=defaultdict(list)
    for part in bom:group[part['value'],part['footprint']].append(part['ref'])
    bom_table=table(['Refs','Qty','Value / exact part','KiCad footprint'],[(', '.join(refs),len(refs),value,fp) for (value,fp),refs in group.items()])
    matrices=[]
    for p in profiles:
        hw='Yes, U6' if p['name'] in ('NM27C512','27C512') else 'Pending pinout' if p['name']=='KR573RF5' else 'Address/pin-role basis' if p['name']=='NM27C080' else 'Yes, matching adapter'
        matrices.append((p['name'],p['size_bytes']//1024,p['address_bits'],hw,'Enabled' if p['read_supported'] else 'Disabled/pending',
            'Verified; default bench lock' if p['program_algorithm_verified'] else 'Disabled'))
    vpp_table=table(['VPP_SW, V','Nominal ADC6, V'],[(v,f'{v*22/142:.6f}') for v in (12.75,21,25,30)])
    text='''# NM27C512_Dumper — KiCad Stage 2 Rev A

The root project is an editable multi-sheet **Stage 2 reader/programmer schematic**, upgraded according to `docs/STAGE2_Upgrade.md`. The original **5 V read-only dumper** is preserved as a separate project in `baseline_readonly/`: it never generates or switches EPROM programming VPP and has no programming circuit. The root Stage 2 project routes an external regulated VPP supply and produces a 6.25 V target rail; it has no onboard VPP boost converter.

**Status:** schematic/ERC, pin/footprint audits, AVR compilation and host simulator tests passed. Stage 2 and Lite PCB files include the RGB mounting alternatives. Lite has component placement, a 90×60 mm outline and four M3 mounting holes; see [placement report](Dumper-Lite/validation/PLACEMENT.md). Stage 2 still has no outline. Neither board has tracks. No assembled hardware was tested. Default firmware permits verified reading/verification and locks WRITE until bench commissioning. KR573RF5 and NM27C080 remain disabled pending the missing exact device documents. This is a reviewable prototype basis, not a tested universal programmer.

## Files and opening

- [Lite project](Dumper-Lite/NM27C512_Dumper_Lite.kicad_pro): a separate minimal, single-sheet 5 V read-only circuit with two address registers, MCU-driven RGB and buffered RX/TX LEDs. See [Lite README](Dumper-Lite/README.md); Stage 2 firmware does not target this circuit.
- Open `NM27C512_Dumper.kicad_pro`, then its main schematic. All 12 sheets are in the project directory; the three adapter sheets are reference documentation for future boards.
- `baseline_readonly/NM27C512_Dumper.kicad_pro`: original three-sheet 5 V circuit; U4=CH340C and U5=socket in this version. The Stage 2 firmware requires voltage monitors/three registers and is not firmware for this baseline.
- `validation/NM27C512_Dumper.pdf` and `NM27C512_ReadOnly.pdf`: full-sheet previews.
- `validation/erc.json`, `baseline_erc.json`, exported XML netlists and `connectivity_audit.json`: validation evidence.
- `validation/BOM.csv` and `baseline_BOM.csv`: per-component BOMs; `docs/BOM.md`: both full tables.
- `firmware/main.c`, `config.h`, `profiles.h`, `build.ps1` and compiled HEX/ELF variants.
- `device_profiles.json`, `tools/eprom_tool.py`, `tools/requirements.txt` and host tests.
- [Profiles](docs/device_profiles.md), [protocol](docs/protocol.md), [bring-up/calibration](docs/bringup.md), [datasheet sources](docs/sources.md).

## Architecture

```mermaid
flowchart LR
    USB[USB Micro-B 5 V] --> F[F1 and 5 V logic rail]
    USB --> CH[CH340C USB UART]
    CH <--> AVR[ATmega328P 16 MHz]
    AVR --> SR[U2/U3/U4 74HC595 chain]
    SR --> A[A0-A19 and RGB status]
    AVR <--> H[Protected HCT245 data bus]
    H <--> ROM[U6 NM27C512 or one J_TARGET adapter]
    A --> ROM
    EXT[External regulated VPP] --> ARM[Q3 PMOS arming stage]
    ARM --> PULSE[Q7 final VPP switch]
    EXT --> REG[LM317 6.25 V]
    REG --> K[K1 default-READ DPDT relay]
    PULSE --> K
    F --> K
    K --> ROM
    RESET[RESET and enable gates] --> ARM
    RESET --> PULSE
    AVR --> K
```

USB supplies all 5 V logic, the CH340 and relay. J4 accepts regulated VPP_IN on pin1 and GND on pin2, expected 12.5-25 V depending on the exact profile. +6V25_PROG is generated from that supply with LM317T. K1 selects target +5 V / +6.25 V and separately selects socket pin22 OE logic / VPP_SW. Normal RESET and power-on use the unenergized READ contacts. VPP and elevated target VCC have no direct connection to an AVR GPIO.

Old NMOS EPROMs can have TTL output-high specifications below the AVR's 5 V CMOS input threshold. Stage 2 therefore uses **SN74HCT245DW**, with TTL-compatible inputs; a 74HC245 is not an equivalent substitute here. Both sides have 1k resistors and external BAT54S clamps. The read-only baseline keeps the requested direct NM27C512 data connection. Target outputs during 6.25 V byte verify are clamped on the buffer side. MCU releases its outputs before VPP_DRIVE changes the bus direction.

## ATmega328P-AU TQFP32 map

PB1, originally reserved for an interlock, now explicitly controls HV_ARM_EN. PB4/MISO is used only by ISP. ADC6/ADC7 are analog-only package pins.

'''+table(['Package pin','Function','Net'],[(i,gpio[i-1],mcu[str(i)]) for i in range(1,33)])+'''
## Address and status chain

U2 SER is PB3/MOSI. U2 Q7S (pin9) goes to U3 SER (pin14), then U3 Q7S to U4 SER. All three share pin11 SRCLK=ADDR_SCK/PB5 and pin12 RCLK=ADDR_LATCH/PB2; SRCLR# pin10=+5V, OE# pin13=GND, VCC16=+5V and GND8=GND. R7 pulls LATCH down during RESET/ISP, keeping ISP shifts from latching. CE/OE/PGM pull-ups keep the target inactive while addresses are unspecified at initial power-up.

| Output | U2 | U3 | U4 |
|---|---|---|---|
| Q0 / pin15 | A0 | A8 | A16 |
| Q1 / pin1 | A1 | A9 | A17 |
| Q2 / pin2 | A2 | A10 | A18 |
| Q3 / pin3 | A3 | A11 | A19 |
| Q4 / pin4 | A4 | A12 | STATUS_RED |
| Q5 / pin5 | A5 | A13 | STATUS_GREEN |
| Q6 / pin6 | A6 | A14 | STATUS_BLUE |
| Q7 / pin7 | A7 | A15 | NC / reserved |

Send U4 byte first, U3 next and U2 last, MSB first, then latch. The high byte's low nibble is A16-A19; bits4/5/6 are active-low RGB R/G/B; bit7 remains LOW. Firmware preserves RGB state on every address update and masks unused upper addresses LOW for smaller profiles. The baseline sends only U3 then U2.

## Direct U6 socket: NM27C512 DIP28

Use only a correctly oriented NM27C512 or verified compatible read part in U6. Footprint is `Package_DIP:DIP-28_W15.24mm_Socket_LongPads`; it suits a conventional 600 mil socket. Verify the selected ZIF socket's body/lever clearance before PCB layout rather than assuming every ZIF is mechanically identical.

'''+table(['Pin','Net','Pin','Net'],[(i,eprom[str(i)],29-i,eprom[str(29-i)]) for i in range(1,15)])+'''
In READ, TARGET_VCC=+5V and SOCKET_OE_VPP follows TARGET_OE#. In PROGRAM, TARGET_VCC=+6.25V and SOCKET_OE_VPP=VPP_SW. Pin20 CE/PGM# is the programming-pulse input. R2/R3/R8 pull CE/OE/PGM HIGH from the logic rail during RESET. K1 physically disconnects the MCU OE path from VPP.

## Headers and UART

J2 is the standard AVR ISP 2x3: pin1 MISO, 2 +5V, 3 SCK, 4 MOSI, 5 RESET, 6 GND. J3 is a 1x3 header: **1 GND, 2 RX (MCU PD0), 3 TX (MCU PD1)**. An external UART TX goes to J3 RX and external RX to J3 TX. Use 5 V TTL and avoid simultaneous active TX sources.

CH340C TXD pin2 goes through R4=1k to MCU RX; MCU TX goes through R5=1k to CH340 RXD pin3. WCH pins: 1 GND, 4 V3 (C3 only), 5 UD+, 6 UD-, 7 NC, 8 OUT#/optional DTR2 (unused), 9 CTS#, 10 DSR#, 11 RI#, 12 DCD#, 13 DTR#, 14 RTS#, 15 R232=GND, 16 VCC=+5V. Every unused output/input has an explicit NC marker. CH340C has an internal oscillator: there is no 12 MHz crystal.

DTR# reaches RESET through C13=100nF, not directly. R1 is the 10k 0603 pull-up, SW1 resets to GND, and ISP RESET is the same net. D9 clamps a positive DTR-release spike on RESET, which also feeds the 5 V interlock inputs.

J1 uses `Connector_USB:USB_Micro-B_Molex-105017-0001`; buy that pad-compatible receptacle. Pins1/2/3/4/5 are VBUS/D-/D+/NC/GND. Shield pad SH=GND. USB VBUS reaches the logic rail through the 1812 500 mA hold polyfuse. The complete circuit can exceed 100 mA, especially with an old EPROM and the 100 mA relay coil. Use a stable USB source whose permitted current covers the load; assess USB descriptor/current and inrush compliance during product engineering. The polyfuse is not an active inrush limiter.

## J_TARGET 2x20 expansion pinout

Odd numbers are the symbol's left column; even numbers are right. Data pins expose the protected **target side** of U9, not the bare MCU pins. Populate U6 or one adapter, never both.

'''+table(['Odd pin','Net','Even pin','Net'],[(i,header[str(i)],i+1,header[str(i+1)]) for i in range(1,40,2)])+'''
Adapters are device-specific. The three reference sheets document 24/28/32-pin roles without adding multiple live EPROM loads. Separate VPP pins often need +5 V in READ, so do not tie them to an unpowered VPP_SW. Future programming adapters require appropriately rated switching or keyed jumpers; the onboard K1 switches U6 pin22 only. RF5 mapping is intentionally withheld pending a manufacturer source.

## VPP, relay and regulator details

Q3 IRF9540N is a 100 V P-channel TO220 device, G1/D2/S3. R30 pulls gate to source; Q4 pulls the gate through R31=2.2k. D5's cathode is SOURCE/VPP_IN and anode is GATE, limiting |VGS| to approximately 10 V. The gate resistor is 1206 / at least 0.25 W for the worst input, instead of overstressing a small resistor. U10 gates PB1 with RESET for arming; U8 gates PD2 with RESET for the final VPP switch. Pull-downs keep both OFF when AVR pins float. No onboard 5-to-25 V boost is present.

The slow PMOS arms an internal node; Q7 MMBT5401 / Q6 MMBT5551 provide the separate final VPP switch. This is a prototype pulse-stage choice; its <=50 ns OE/VPP rise requirement is **unverified** and must be measured before WRITE is commissioned. Its voltage drop must be calibrated at load. No bulk cap sits on VPP_SW; R37=10k discharges it. D6 and two 5.1k resistors indicate actual switched VPP independently of the software RGB LED.

K1 standard G5V-2-DC5 uses coil pins1/16, COM4-NC6-NO8 for VCC and COM13-NC11-NO9 for OE/VPP. Q5 drives the 100 mA coil; R42=470 ohm gives roughly 9 mA base drive. This replaces the suggested 10k value, which would not establish saturation for that coil. D8 is the 1N4148WS SOD323 flyback diode, cathode on +5V.

LM317T pin1 ADJ, 2 OUT, 3 IN. R40=120 ohm, R41=430 ohm and RV1=100 ohm set +6V25_PROG. Measure and adjust TP_6V25 to 6.250 V, then verify under load. Approximately 48 ohm of trim is nominal; real reference/Iadj vary. A heatsink is needed for the intended high-input/load combination. Details and acceptance tests are in [bringup.md](docs/bringup.md).

## Voltage monitoring

ADC6 divider is 120k/22k, both 1%, with 10nF at the node: `Vadc = VPP_SW * 22 / 142`. ADC7 is a 10k/10k, 1% divider with 10nF: 5 V target gives 2.500 V and 6.25 V gives 3.125 V. D30/D31 add external Schottky clamps at the ADC nodes.

'''+vpp_table+f'''
At 30 V, worst 1% divider tolerance (118.8k top / 22.22k bottom) gives {30*22.22/(118.8+22.22):.6f} V, below the firmware's 4.75 V minimum logic rail. Normal external supply maximum is 25 V. These are divider ratings, not permitted NM27C512 programming voltages. The calibrated ADC must enforce that profile's much narrower 12.50-13.00 V window. ADC filtering cannot certify transient overshoot; the socket waveform must be scoped.

## Indicators and test points

| Indicator | Meaning |
|---|---|
| D2 GREEN | READ / VERIFY state |
| D2 RED | WRITE state |
| D2 AMBER | IDLE (red and green) |
| D2 BLUE | Transfer/program error state |
| D3 BLUE | Actual UART RX LOW bits via Q1 |
| D4 ORANGE | Actual UART TX LOW bits via Q2 |
| D6 RED | Actual VPP_SW present |

D2 uses the project-local combined footprint for a square Kingbright KAAF-5050RGBS-13 SMD RGB or a four-lead WP154A4SEJ3VBDZGW/CA RGB. Populate exactly one. Logical pads remain 1R/2A/3G/4B; the differing physical pinouts are mapped inside the footprint. Each colour retains its 1k resistor and LOW=ON behavior. See [RGB mounting](docs/RGB_Mounting.md), including the requirement to route both pad sets. Q1/Q2 MMBT3906 emitters are +5V; 10k base resistors limit UART loading to roughly 0.4 mA during LOW bits and LEDs are OFF at idle HIGH. Their collectors drive LEDs through 1k; they do not put a heavy direct LED load on UART.

TP1-TP13 are respectively 5V, GND, 6V25, VPP_IN, VPP_SW, RESET, ADDR_SCK, ADDR_LATCH, CE, OE, PGM, RX and TX. Each is named on its schematic page and is a 1.5 mm pad footprint.

## Device support matrix

The hardware column describes routed schematic capability; no adapter or board has been physically validated. Read verification and algorithm verification have separate source/implementation meanings.

'''+table(['Device profile','KiB','Address bits','Hardware electrically supported (schematic)','Read profile','Programming algorithm'],matrices)+'''
2708 is unsupported: its normal read needs +12 V and -5 V in addition to +5 V. 27C160 is unsupported: it requires a 16-bit bus. Different manufacturers' programming rails/polarities/timings must be separate profiles; generic aliases do not authorize WRITE.

## Firmware and host use

Bare-metal AVR C implements INFO, LIST, READ, VERIFY, WRITE and VOLTAGES. Profile size/address mask and program voltage/pulse parameters come from the generated flash table. Timer1 generates the nominal 100 us CE pulse; Timer0 handles the timeouts. Watchdog is 1 s. Hardware RESET gates cut both VPP switches even while AVR GPIO state changes; software turns off VPP before returning the relay to READ. Link/CRC/UART errors invoke the safe sequence. [Protocol details](docs/protocol.md) include the frames, keepalive and final whole-image CRC.

Default WRITE is locked. The National algorithm implemented for NM27C512 requires an erased device, 6.25 V VCC, 12.75 V VPP, 100 us pulses with up to 25 attempts, per-byte verify and final comparison at 5 V. The host requires ambient 20-30 C and explicit confirmation. It checks actual switched VPP with the socket isolated before selecting PROGRAM, then target VCC and VPP before pulses. The circuit must pass [bench commissioning](docs/bringup.md) before using a commissioned build. Do not insert/remove devices while either supply is connected.

```powershell
# Build the default read/verify firmware (WRITE locked).
./firmware/build.ps1

# Install the host's serial dependency; listing itself works without pyserial.
python -m pip install -r tools/requirements.txt
python tools/eprom_tool.py list
python tools/eprom_tool.py info --port COM5
python tools/eprom_tool.py voltages --port COM5
python tools/eprom_tool.py read --device NM27C512 --port COM5 --out bios.bin
python tools/eprom_tool.py verify --device NM27C512 --port COM5 --file bios.bin

# Only on measured, commissioned hardware; confirmation remains required.
python tools/eprom_tool.py write --device NM27C512 --port COM5 --file bios.bin --ambient-c 25
```

READ preserves exact length and validates CRC before creating the output file. VERIFY compares every byte. WRITE resends the complete image for final 5 V verification. Unsupported algorithms and incorrect image sizes fail before programming; --yes bypasses only the prompt, not the hardware commissioning lock. No actual port was opened or device flashed in this task.

## BOM and footprints

All components have assigned installed standard footprints; there is no custom footprint library. C4/C5/C6 decouple VCC/VCC/AVCC, C10 is AREF, C7/C8/C14 are the three 595s, C9/C15 are target 100nF/10uF; the other digital ICs have 100nF each. C3 decouples CH340 V3, not an external 3.3 V supply. The 16 MHz quartz is two-pin HC49 with 22pF load capacitors; account for board stray capacitance when selecting its specified load.

The following is the complete grouped Stage 2 BOM; CSV has one row for every reference. Baseline has its own table because its U4/U5 reference meanings differ.

'''+bom_table+f'''
Total: {len(bom)} Stage 2 components, {len(base)} baseline components. Generic colour LEDs must match the selected 0603 cathode/anode pad convention. Use rated capacitors, heatsinking and the exact footprints, especially the wide SOIC20 HCT245, PMOS TO220, relay and USB connector.

## Validation and reproducibility

Detected KiCad **10.0.6** on Windows. ERC: **0 errors, 0 warnings** for both projects, with no custom severity suppression or exclusions. The KiCad defaults leave single-global-label, four-way-junction, SPICE-model and footprint-filter checks ignored; every assigned footprint's existence and pin/pad coverage is independently audited. The exported netlist passed **{audit['passed_checks']} checks**, including every MCU/EPROM pin, cascades, relay poles, Q3/D5/Q6/Q7/LM317 orientation, clamps, headers, protected data paths, ADC dividers, MISO isolation and absence of direct HV nets at U1. These are connectivity checks, not a simulation of all conductive paths or component faults.

**19 host tests passed**, covering the CRC reference vector, frame boundaries, offsets, hash matching, partial serial reads, rejected operations and reset/cleanup on errors. Both firmware variants compile under avr-gcc 7.3.0 with -Wall -Wextra -Werror: safe 4224 bytes flash / 235 bytes static RAM; commissioned compile-check 5542 / 319. Nothing was flashed. PDFs were exported and all pages visually inspected.

```powershell
# Re-run ERC, exports, connectivity/footprint audits, host tests and safe build.
./tools/validate.ps1
# Optional compile check of the WRITE-enabled code, not hardware commissioning:
./tools/validate.ps1 -BuildCommissioned
```

The validator locates installed KiCad automatically. `tools/generate_schematic.py` regenerates both editable projects from installed libraries; it intentionally overwrites generated schematic files, so retain any manual edits before running it. `tools/generate_profiles.py` regenerates JSON and the firmware table; rebuild afterward. `tools/generate_readme.py` refreshes these documentation tables after a successful netlist audit.

Project-local symbol `ProjectSymbols:CH340C_WCH` corrects the installed CH340C pin8 name/type to the WCH document; its pin8 remains intentionally unconnected. `ProjectSymbols:RGB_CA_DualMount` and `ProjectFootprints:RGB_CA_5050_or_THT5` implement the two RGB mounting alternatives. Other symbols come from installed standard libraries. U9 uses a pin-compatible HC245 drawing with the explicit **HCT245** part value; Q6/Q7 use standard B/E/C symbols with the exact MMBT5551/MMBT5401 values. No unverified RF5 symbol was invented. Source links and pending verifications are in [sources.md](docs/sources.md).
'''
    (ROOT/'README.md').write_text(text,encoding='utf8')
    full=['# Per-component BOM\n','## Stage 2\n',table(['Ref','Value','Footprint','Sheet'],[(p['ref'],p['value'],p['footprint'],p['sheet']) for p in bom]),
          '\n## Original 5 V read-only baseline\n',table(['Ref','Value','Footprint','Sheet'],[(p['ref'],p['value'],p['footprint'],p['sheet']) for p in base])]
    (ROOT/'docs/BOM.md').write_text('\n'.join(full),encoding='utf8')
    (ROOT/'baseline_readonly/README.md').write_text('''# Original NM27C512 read-only dumper

This separate three-sheet KiCad project preserves the first task: 5 V only, no VPP generation and no EPROM programming circuit. U1=ATmega328P-AU, U2/U3=74HC595D, U4=CH340C, U5=NM27C512 socket. PC0-PC5 and PD4/PD5 are the direct data inputs, PD6/PD7 are CE/OE, PB2/PB3/PB5 are latch/serial/clock; PB4 remains MISO. Send U3 high address byte then U2 low byte, MSB first. CE/OE pull-ups and latch pull-down hold the socket harmless during reset/ISP.

Open NM27C512_Dumper.kicad_pro in this directory. All footprints are assigned; USB SH is grounded and the WCH-corrected CH340C pin8 is intentionally NC. J3 is 1GND/2MCU RX/3MCU TX; J2 is standard AVR ISP. ERC on KiCad 10.0.6: 0 errors and 0 warnings. Full BOM and baseline netlist/ERC/PDF are in ../docs/BOM.md and ../validation/.

The firmware in ../firmware/ targets the upgraded Stage 2 circuit, including ADC monitors, three shift registers and HCT bus. It is not baseline firmware. The baseline hardware was not assembled or physically read-tested in this task. The root README documents the upgrade and its validation scope.
''',encoding='utf8')
    print('README.md, docs/BOM.md and baseline README generated.')
if __name__=='__main__':main()
