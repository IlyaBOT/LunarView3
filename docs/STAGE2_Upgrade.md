Task: upgrade the KiCad NM27C512 EPROM dumper into a safe multi-EPROM reader/programmer.

Environment:
- Windows
- KiCad is already installed
- Work in the current project/directory
- Existing project name: NM27C512_Dumper
- Do not merely describe the circuit. Actually create/update the KiCad project,
  schematic, symbols/footprints as required, run ERC with kicad-cli.exe, and
  leave the project in a valid state.

Primary goals:
1. Preserve full read support for NM27C512.
2. Add safe programming support for NM27C512.
3. Add hardware support for older and larger 8-bit parallel EPROMs.
4. Add a device-profile system for firmware/host software so address count,
   pin roles, voltages and algorithms depend on the selected device type.
5. Do NOT assume that all 27xx EPROMs use the same programming algorithm.
6. Do NOT apply >5 V directly to any ATmega328P pin.
7. Default hardware state after power-on/reset must ALWAYS be READ/SAFE mode,
   with VPP disabled.

============================================================
1. MAIN CONTROLLER
============================================================

Use:

U1 = ATmega328P-AU, TQFP-32, 5 V
U2 = 74HC595D, SOIC-16
U3 = 74HC595D, SOIC-16
U4 = 74HC595D, SOIC-16
U5 = CH340C, SOP-16

Primary direct EPROM socket:
U6 = NM27C512 / JEDEC DIP-28 socket, preferably a ZIF-compatible footprint.

Keep the original:
- 16 MHz two-pin crystal for ATmega328P
- 22 pF load capacitors
- standard 10k RESET pull-up
- RESET pushbutton to GND
- CH340C DTR# -> 100 nF -> AVR RESET
- 2x3 AVR ISP header
- 1x3 UART header ordered:
    1 GND
    2 RX (ATmega RX)
    3 TX (ATmega TX)
- Micro-USB Type-B connector
- USB +5 V powers all 5 V logic.

Use 0603 resistors whenever practical.

============================================================
2. ATmega PIN ASSIGNMENT
============================================================

Keep the data bus:

PC0 = ROM_D0
PC1 = ROM_D1
PC2 = ROM_D2
PC3 = ROM_D3
PC4 = ROM_D4
PC5 = ROM_D5
PD4 = ROM_D6
PD5 = ROM_D7

UART:

PD0 = RXD
PD1 = TXD

EPROM/control:

PD2 = VPP_EN
PD3 = PROG_MODE
PD6 = TARGET_CE_PGM#
PD7 = TARGET_OE#

PB0 = TARGET_PGM#
PB1 = RESERVED / future hardware interlock
PB2 = ADDR_LATCH
PB3 = MOSI / ADDR_SER
PB4 = MISO, keep free for ISP
PB5 = SCK / ADDR_SCK
PB6/PB7 = 16 MHz crystal

ADC6 = VPP_SENSE
ADC7 = TARGET_VCC_SENSE

PC6 = RESET.

Do not consume PB4/MISO for anything except ISP.

============================================================
3. THREE 74HC595 ADDRESS / STATUS CHAIN
============================================================

Cascade three 74HC595D devices.

Shared:

PB3/MOSI -> U2 SER
PB5/SCK  -> U2/U3/U4 SRCLK
PB2      -> U2/U3/U4 RCLK

U2 Q7S -> U3 SER
U3 Q7S -> U4 SER

Use:

U2 Q0-Q7 = A0-A7
U3 Q0-Q7 = A8-A15

U4:
Q0 = A16
Q1 = A17
Q2 = A18
Q3 = A19

This gives address support up to 20 address bits, sufficient for 1 MiB x8
devices such as 27C080-class EPROMs.

Use the remaining U4 outputs for the RGB state LED:

Q4 = STATUS_RED
Q5 = STATUS_GREEN
Q6 = STATUS_BLUE
Q7 = RESERVED

Use a common-anode RGB LED connected to +5 V.
Each colour gets its own current limiting resistor.
1k 0603 resistors are preferred.

Drive LED cathodes from U4 outputs such that firmware can display:

GREEN  = reading ROM
RED    = programming/writing
AMBER  = idle/waiting (RED + GREEN)
BLUE   = optional error/special state if useful

Because the status bits share the 24-bit shift-register chain with addresses,
firmware must preserve the current status LED bits whenever it updates the
address.

Add 100 nF decoupling at every 74HC595.

ADDR_LATCH must have a 10k pull-down so ISP activity cannot randomly latch
shifted data while the MCU is being programmed.

============================================================
4. DATA BUS PROTECTION AND BIDIRECTIONAL OPERATION
============================================================

During normal ROM reads:
ATmega data pins are INPUT.

During EPROM programming:
ATmega data pins become OUTPUT and provide D0-D7.

Place a 1k 0603 series resistor in every D0-D7 path.

Reason:
- protects against accidental output contention,
- limits current if firmware direction is wrong,
- helps protect ATmega while verifying an EPROM whose programming VCC can be
  above 5 V.

Also add external Schottky clamps from every MCU-side data line to:
- +5 V
- GND

Choose a sensible BAT54-family discrete or array implementation and verify
the diode orientation.

Do not rely only on the ATmega internal protection diodes.

============================================================
5. EXTERNAL PROGRAMMING VOLTAGE INPUT
============================================================

Do NOT make the circuit assume that all EPROMs use 12 V.

Add:

J_VPP_IN
2-pin input for an EXTERNAL REGULATED programming supply.

Expected normal range:
12.5 V ... 25 V

Clearly label:

VPP_IN
GND

Add a test point:

TP_VPP_IN

The USB connector still powers all normal 5 V electronics.
VPP_IN is only an external programming-voltage source.

Do not design an onboard 5 V -> 25 V boost converter in this revision.
Leave the design modular so one could be added later.

============================================================
6. MCU-CONTROLLED VPP HIGH-SIDE SWITCH
============================================================

VPP must be switched by the ATmega.

Use a high-side P-channel MOSFET arrangement:

VPP_IN
  ->
P-channel MOSFET
  ->
VPP_SW

The P-channel MOSFET must:
- be rated for at least 40 V, preferably 50-60 V;
- have sufficiently low Rds(on) for tens of mA;
- not depend on a -25 V VGS condition.

Use an NPN transistor controlled from ATmega PD2/VPP_EN to pull the PMOS gate
low.

Implement:

- gate-to-source pull-up so VPP defaults OFF;
- NPN base resistor;
- NPN base pull-down;
- gate pull-down/current limiting resistor;
- approximately 10-12 V gate-source Zener clamp so VGS never exceeds the
  MOSFET absolute maximum when VPP_IN is 25 V.

VPP_EN must have a hardware default that keeps VPP OFF while:
- MCU is reset,
- MCU is unprogrammed,
- ISP is active,
- UART auto-reset occurs.

Absolutely do not connect VPP directly to an ATmega pin.

Add:

TP_VPP_SW

============================================================
7. HARDWARE VPP INDICATOR
============================================================

Add a dedicated RED "VPP ACTIVE" LED independent of the RGB firmware status.

It must indicate actual switched VPP, not just the MCU command.

Suggested:

VPP_SW
 -> 5.1k
 -> 5.1k
 -> RED LED
 -> GND

Using two 5.1k 0603 resistors is preferred because these values are readily
available and split power/voltage stress.

The RGB LED RED channel indicates software WRITE state.
The dedicated VPP LED indicates that high voltage is physically present.

============================================================
8. VPP MONITORING
============================================================

Measure VPP_SW using ATmega ADC6.

Use a high impedance divider suitable for at least 30 V input, for example
approximately:

120k top
22k bottom

plus a small capacitor (for example 10 nF) on the ADC node.

Calculate the exact divider and document:

ADC voltage at:
12.75 V
21 V
25 V
30 V

Ensure ADC input stays safely below +5 V even with reasonable VPP supply
error.

Firmware must refuse programming if measured VPP is outside the selected
device profile tolerance.

============================================================
9. PROGRAMMING VCC RAIL
============================================================

NM27C512 does NOT use ordinary 5 V VCC during programming.

Provide a regulated approximately 6.25 V programming rail.

Generate it from VPP_IN using an LM317-class adjustable regulator or another
simple verified regulator appropriate for the voltage/current.

Use a package with enough dissipation capability, preferably TO-220 or
another thermally adequate footprint.

Provide:

+6V25_PROG
TP_6V25

Use proper input/output capacitors and decoupling.

Use fixed resistor(s) plus a trimmer if necessary so the user can calibrate
the rail to 6.25 V.

Clearly document the calibration procedure.

This rail only powers the target EPROM when the selected programming profile
requires elevated programming VCC.

============================================================
10. TARGET VCC SWITCHING
============================================================

Target EPROM VCC must be selectable between:

+5 V normal/read rail
+6.25 V programming rail

Use a default-safe switching solution.

Preferred implementation:
a small 5 V DPDT signal relay such as an Omron G5V-2 class device, driven from
ATmega PD3/PROG_MODE using an NPN transistor and flyback diode.

Default/de-energized state MUST be:

TARGET_VCC = +5 V
VPP disconnected from NM27C512 OE/VPP pin

Programming state:

TARGET_VCC = +6.25 V
NM27C512 OE/VPP pin is connected to VPP_SW

Use the second pole of the DPDT relay for the NM27C512 OE/VPP routing.

Relay driver:
- NPN transistor
- ~10k base resistor
- base pull-down
- flyback diode across relay coil

The relay must drop back into READ mode whenever MCU resets.

============================================================
11. NM27C512 DIRECT SOCKET
============================================================

Retain a direct DIP-28/ZIF socket dedicated to NM27C512 / compatible 27C512
devices.

Read mode:

VCC = +5 V
pin 22 OE/VPP = TARGET_OE#
pin 20 CE/PGM# = TARGET_CE_PGM#

Programming mode:

VCC = +6.25 V
pin 22 OE/VPP = VPP_SW
pin 20 CE/PGM# is pulsed by ATmega

Use the DPDT relay to physically isolate the normal OE logic path from VPP.

The ATmega must never see the programming voltage.

Add 10k pull-ups where appropriate so CE/PGM and other control inputs stay
inactive during MCU reset.

Verify every NM27C512 pin against the actual Fairchild/National datasheet.

============================================================
12. TARGET VCC MONITORING
============================================================

Use ADC7 to monitor TARGET_VCC.

A simple 10k / 10k divider is acceptable.

Add a small filter capacitor.

Firmware must verify approximately:
5 V in read mode
6.25 V when a profile requires elevated VCC

before applying VPP or programming pulses.

============================================================
13. POWER LED
============================================================

Add a GREEN power LED:

+5 V -> 1k 0603 -> green LED -> GND

This LED is always on when USB power is present.

============================================================
14. RX AND TX ACTIVITY LEDs
============================================================

Add:

RX LED = BLUE
TX LED = ORANGE

They must indicate actual serial activity without significantly loading the
UART lines.

Do not simply place a heavy LED load directly on UART pins.

Use small PNP transistor buffers, e.g. MMBT3906-class SOT-23:

emitter -> +5 V
base -> UART signal through ~10k
collector -> LED + current limiting resistor -> GND

Because UART idles HIGH:
- transistor is OFF at idle,
- LOW serial bits produce LED flashes.

Use:
RX from ATmega PD0/RXD net
TX from ATmega PD1/TXD net

Use approximately 1k for LED current limiting.

============================================================
15. UNIVERSAL TARGET / ADAPTER CONNECTOR
============================================================

Do not attempt to pretend that every EPROM package has identical physical
pin assignments.

Create a 2x20 2.54 mm expansion connector named:

J_TARGET

Expose at least:

A0-A19
D0-D7
TARGET_CE_PGM#
TARGET_OE#
TARGET_PGM#
VPP_SW
TARGET_VCC
+5V
+6V25_PROG
GND
PROG_MODE
one or more spare pins if available

Document the exact 40-pin header assignment in README.md and in schematic
notes.

This connector is intended for passive or semi-active adapter boards for
different EPROM families.

============================================================
16. DEVICE FAMILY SUPPORT
============================================================

Hardware should be designed around 8-bit parallel memories.

Initial target classes:

NM27C512 / 27C512:
64 KiB x8
A0-A15
D0-D7
direct onboard socket
read + program support

2716:
2 KiB x8
A0-A10
adapter required

KR573RF5 / КР573РФ5:
2 KiB x8
2716-family device
adapter required
hardware must support approximately 25 V VPP

2732:
4 KiB x8
A0-A11
adapter required

2764:
8 KiB x8
A0-A12

27128:
16 KiB x8
A0-A13

27256:
32 KiB x8
A0-A14

27C512:
64 KiB x8
A0-A15

27C010:
128 KiB x8
A0-A16

27C020:
256 KiB x8
A0-A17

27C040:
512 KiB x8
A0-A18

27C080:
1 MiB x8
A0-A19

Do not claim that all of these are electrically/programming-algorithm
compatible.

The hardware address generator merely provides A0-A19.

Different physical packages/pin assignments must use adapter boards.

Do NOT support 2708 in this hardware revision.
Document explicitly why:
2708-class devices require additional +12 V and -5 V power rails even for
normal reading and therefore need a different power architecture.

Do not support 16-bit devices such as 27C160 directly in Rev A.

============================================================
17. ADAPTER REFERENCE SHEETS
============================================================

Add reference/hierarchical schematic sheets for at least:

adapter_2716_KR573RF5
adapter_28pin_27xx
adapter_32pin_JEDEC

These sheets are primarily documentation for future adapter PCBs.

Show how logical signals from J_TARGET map to package pins.

Do not guess pinouts.

Verify them from datasheets before adding each adapter.

If a device has a pin that changes roles between:
address,
OE,
PGM,
VPP,
CE,
etc.,
show that explicitly.

If a safe passive mapping is impossible, document that the adapter requires
a jumper, relay or transistor-level switching.

============================================================
18. SOFTWARE / FIRMWARE DEVICE PROFILE ARCHITECTURE
============================================================

Create a device profile system instead of hardcoding NM27C512 everywhere.

Create:

firmware/
tools/
device_profiles.json
docs/device_profiles.md

Each profile must contain fields conceptually equivalent to:

name
aliases
package
adapter
size_bytes
data_bits
address_bits

read_vcc
read_vpp

program_supported
program_vcc
program_vpp
vpp_tolerance

address_pin_map
data_pin_map

ce_role
oe_role
pgm_role
vpp_pin_role

program_pulse_us
max_program_pulses
verify_algorithm
power_sequence

Do not invent programming timings.

If an exact manufacturer/device datasheet has not been verified:
- reading may be enabled if pinout is verified;
- programming must remain disabled.

============================================================
19. INITIAL DEVICE PROFILES
============================================================

Implement NM27C512 as the primary fully supported programming profile.

For the exact National/Fairchild NM27C512 profile use the values from the
datasheet, including approximately:

read:
VCC = 5 V

program:
VCC approximately 6.25 V
VPP approximately 12.75 V

Programming uses the device's documented fast programming algorithm and
program/verify sequence.

Do not exceed the datasheet VPP absolute limit.

Verify exact pulse duration and maximum retry count from the datasheet before
encoding them.

For KR573RF5:
- create the read profile;
- size = 2048 bytes;
- A0-A10;
- 8-bit data;
- mark expected programming VPP as approximately 25 V;
- do NOT enable write support until an exact KR573RF5/K573RF5 programming
  datasheet/algorithm has been verified.

Do the same conservative treatment for other 27xx parts.

============================================================
20. AVR FIRMWARE
============================================================

Create basic ATmega328P firmware.

Required commands over UART:

INFO
LIST
READ
WRITE
VERIFY
VOLTAGES

The host must always specify a device type.

Examples:

READ NM27C512
WRITE NM27C512
VERIFY NM27C512

Firmware must dynamically use:

profile.size_bytes
profile.address_bits
profile programming voltages
profile programming algorithm

For smaller EPROMs unused upper address lines must be driven LOW.

For reads:
- configure D0-D7 as inputs,
- set address,
- assert control signals,
- wait a conservative access delay,
- sample byte,
- disable output.

For writes:
- refuse if profile.program_supported == false;
- verify TARGET_VCC;
- verify VPP_IN/VPP_SW using ADC;
- enter PROG_MODE;
- ensure correct power sequence;
- switch data bus to outputs;
- execute only the selected device's verified programming algorithm;
- verify data after programming;
- immediately disable VPP on reset/error/timeout.

Any communication loss, watchdog reset or invalid command must cause:
VPP_EN = OFF
PROG_MODE = OFF/read mode
EPROM controls = inactive.

Enable the AVR watchdog during programming operations.

============================================================
21. HOST PYTHON TOOL
============================================================

Create:

tools/eprom_tool.py

Use pyserial.

CLI examples:

python eprom_tool.py list

python eprom_tool.py read ^
    --device NM27C512 ^
    --port COM5 ^
    --out bios.bin

python eprom_tool.py verify ^
    --device NM27C512 ^
    --port COM5 ^
    --file bios.bin

python eprom_tool.py write ^
    --device NM27C512 ^
    --port COM5 ^
    --file bios.bin

For a device whose write algorithm is not verified, the tool must stop with a
clear message instead of attempting generic programming.

Before WRITE display:

selected device
expected size
expected VCC
expected VPP
measured TARGET_VCC
measured VPP
adapter/socket expected

Require an explicit confirmation before enabling programming voltage unless
--yes is supplied.

============================================================
22. SAFETY / POWER SEQUENCING
============================================================

Programming voltage handling is safety-critical for the EPROM and MCU.

Enforce in hardware and firmware:

- VPP OFF by default
- relay defaults to READ mode
- CE/PGM inactive by default
- no >5 V path to ATmega GPIO
- MCU reset immediately removes VPP
- UART DTR reset immediately removes VPP
- VCC must be valid before VPP is enabled
- VPP must be removed before target VCC is removed
- user must not insert/remove EPROM while target power/VPP is active

Add these notes visibly to the schematic.

============================================================
23. DECOUPLING
============================================================

Provide at least:

100 nF at every digital IC VCC
100 nF near EPROM target socket
100 nF on AREF
10 uF bulk at USB 5 V input
10 uF bulk on target VCC
appropriate LM317 input/output capacitors
appropriate VPP_IN/VPP_SW capacitors rated for at least 35 V, preferably 50 V

Do not place an oversized capacitor directly on a switched VPP node if that
would cause slow unsafe discharge.

If VPP_SW can remain charged, add a high-value bleed resistor so it returns to
a safe voltage reasonably quickly after VPP is disabled.

============================================================
24. TEST POINTS
============================================================

Add clearly named test points:

TP_5V
TP_GND
TP_6V25
TP_VPP_IN
TP_VPP_SW
TP_RESET
TP_ADDR_SCK
TP_ADDR_LATCH
TP_CE
TP_OE
TP_PGM
TP_RX
TP_TX

============================================================
25. ERC AND VALIDATION
============================================================

Run KiCad ERC.

Validate:

- ATmega328P-AU TQFP pin numbering
- CH340C pin numbering
- all 74HC595D pin numbering
- NM27C512 DIP-28 pinout
- relay pole orientation
- MOSFET source/drain/gate orientation
- VGS Zener orientation
- NPN driver orientation
- LM317 pin numbering for the selected footprint
- no high-voltage connection can reach MCU
- target VCC defaults to 5 V
- VPP defaults OFF
- ISP remains functional
- UART remains functional
- DTR auto-reset cannot leave VPP enabled
- address range reaches A19
- RGB state LED operation
- RX/TX LEDs do not heavily load UART
- data lines can safely change direction

Fix genuine ERC errors.
Use No Connect markers only for intentionally unused pins.

============================================================
26. DOCUMENTATION
============================================================

Update README.md with:

architecture overview
block diagram
BOM
ATmega GPIO map
74HC595 bit map
NM27C512 direct socket mapping
J_TARGET pinout
power rails
VPP switching explanation
6.25 V regulator calibration
program/read power sequencing
status LED meanings
RX/TX LED meanings
supported device matrix
unsupported device matrix
adapter requirements
firmware protocol
Python CLI examples
KiCad version
ERC result

Clearly distinguish:

"Hardware electrically supported"
"Read profile verified"
"Programming algorithm verified"

Do not claim write support for a device merely because the voltage and pinout
look similar.

============================================================
27. FINAL DELIVERABLES
============================================================

The result must contain at least:

NM27C512_Dumper.kicad_pro
NM27C512_Dumper.kicad_sch

project-local symbols/footprints if required

firmware/
tools/eprom_tool.py
device_profiles.json
docs/device_profiles.md
README.md

Do not stop after generating textual documentation.
Actually create and validate the KiCad project on Windows.