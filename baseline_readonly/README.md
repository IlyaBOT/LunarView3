# Original NM27C512 read-only dumper

This separate three-sheet KiCad project preserves the first task: 5 V only, no VPP generation and no EPROM programming circuit. U1=ATmega328P-AU, U2/U3=74HC595D, U4=CH340C, U5=NM27C512 socket. PC0-PC5 and PD4/PD5 are the direct data inputs, PD6/PD7 are CE/OE, PB2/PB3/PB5 are latch/serial/clock; PB4 remains MISO. Send U3 high address byte then U2 low byte, MSB first. CE/OE pull-ups and latch pull-down hold the socket harmless during reset/ISP.

Open NM27C512_Dumper.kicad_pro in this directory. All footprints are assigned; USB SH is grounded and the WCH-corrected CH340C pin8 is intentionally NC. J3 is 1GND/2MCU RX/3MCU TX; J2 is standard AVR ISP. ERC on KiCad 10.0.6: 0 errors and 0 warnings. Full BOM and baseline netlist/ERC/PDF are in ../docs/BOM.md and ../validation/.

The firmware in ../firmware/ targets the upgraded Stage 2 circuit, including ADC monitors, three shift registers and HCT bus. It is not baseline firmware. The baseline hardware was not assembled or physically read-tested in this task. The root README documents the upgrade and its validation scope.
