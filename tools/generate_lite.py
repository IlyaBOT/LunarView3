"""Generate the separate, single-sheet 5 V NM27C512 Lite project.

Uses the existing KiCad writer and libraries. It only writes the Lite folder.
"""
from pathlib import Path
import csv
import json
import shutil
import generate_schematic as g
from kicad_sexpr import parse, dump, one

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ('Dumper-Lite' if (ROOT / 'Dumper-Lite').exists() else 'lite')
NAME = 'NM27C512_Dumper_Lite'

MCU = {
    '1': None, '2': 'ROM_D6', '3': 'GND', '4': '+5V', '5': 'GND',
    '6': '+5V', '7': 'XTAL1', '8': 'XTAL2', '9': 'ROM_D7',
    '10': 'ROM_CE#', '11': 'ROM_OE#', '12': 'STATUS_RED',
    '13': 'STATUS_GREEN', '14': 'ADDR_LATCH', '15': 'ADDR_SER',
    '16': 'ISP_MISO', '17': 'ADDR_SCK', '18': '+5V', '19': None,
    '20': 'AREF', '21': 'GND', '22': None, '23': 'ROM_D0',
    '24': 'ROM_D1', '25': 'ROM_D2', '26': 'ROM_D3', '27': 'ROM_D4',
    '28': 'ROM_D5', '29': 'RESET', '30': 'UART_RX', '31': 'UART_TX',
    '32': 'STATUS_BLUE',
}
EPROM = {
    '1': 'A15', '2': 'A12', '3': 'A7', '4': 'A6', '5': 'A5',
    '6': 'A4', '7': 'A3', '8': 'A2', '9': 'A1', '10': 'A0',
    '11': 'ROM_D0', '12': 'ROM_D1', '13': 'ROM_D2', '14': 'GND',
    '15': 'ROM_D3', '16': 'ROM_D4', '17': 'ROM_D5', '18': 'ROM_D6',
    '19': 'ROM_D7', '20': 'ROM_CE#', '21': 'A10', '22': 'ROM_OE#',
    '23': 'A11', '24': 'A9', '25': 'A8', '26': 'A13', '27': 'A14',
    '28': '+5V',
}


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / 'validation').mkdir(exist_ok=True)
    g.NAME = NAME
    g.BOM.clear()
    g.COUNTERS.clear()
    p = g.Page(NAME + '.kicad_sch', 'NM27C512 Lite / READ-ONLY / 5 V ONLY',
               OUT, g.uid('lite/root'))

    # USB and UART. No external UART header, so both UART paths are direct.
    p.text('USB power and CH340C', 20, 28, 1.6)
    p.component('Connector:USB_B_Micro', 'J1', 'USB Micro-B', 36, 70,
                {'1': '+5V', '2': 'USB_D-', '3': 'USB_D+', '4': None,
                 '5': 'GND', 'SH': 'GND'},
                'Connector_USB:USB_Micro-B_Molex-105017-0001')
    ch = dict(g.CH_NETS)
    ch.update({'2': 'UART_RX', '3': 'UART_TX'})
    p.component('ProjectSymbols:CH340C_WCH', 'U4', 'CH340C', 110, 70,
                ch, g.SOIC16)
    p.cap('C1', '10uF / 10V', 28, 116, '+5V',
          'Capacitor_SMD:C_0805_2012Metric')
    p.cap('C2', '100nF', 94, 116, '+5V')
    p.cap('C3', '100nF', 129, 116, 'CH_V3')
    p.text('CH340C internal clock: no 12 MHz crystal.\nR232 = GND; unused modem pins = NC.',
           20, 132, 1.05)

    # MCU, standard AVR ISP and reset/clock.
    p.component('MCU_Microchip_ATmega:ATmega328P-A', 'U1', 'ATmega328P-AU',
                214, 92, MCU, 'Package_QFP:TQFP-32_7x7mm_P0.8mm')
    for ref, x in [('C4', 172), ('C5', 201), ('C6', 230)]:
        p.cap(ref, '100nF', x, 147, '+5V')
    p.cap('C10', '100nF', 258, 147, 'AREF')
    p.component('Connector:AVR-ISP-6', 'J2', 'AVR ISP', 49, 166,
                {'1': 'ISP_MISO', '2': '+5V', '3': 'ADDR_SCK',
                 '4': 'ADDR_SER', '5': 'RESET', '6': 'GND'},
                'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical')
    p.text('J2: 1 MISO / 2 +5V / 3 SCK\n4 MOSI / 5 RESET / 6 GND', 76, 166, 1.05)
    p.component('Device:Crystal', 'Y1', '16MHz / CL ~18pF', 168, 189,
                {'1': 'XTAL1', '2': 'XTAL2'}, 'Crystal:Crystal_HC49-4H_Vertical')
    p.cap('C11', '22pF', 157, 221, 'XTAL1')
    p.cap('C12', '22pF', 195, 221, 'XTAL2')
    p.resistor('R1', '10k', 197, 178, '+5V', 'RESET')
    p.component('Switch:SW_Push', 'SW1', 'RESET', 266, 176,
                {'1': 'RESET', '2': 'GND'}, 'Button_Switch_THT:SW_PUSH_6mm')
    p.component('Device:D_Schottky', 'D4', 'BAT54WS', 231, 179,
                {'1': '+5V', '2': 'RESET'}, 'Diode_SMD:D_SOD-323')
    p.component('Device:C', 'C13', '100nF', 257, 202,
                {'1': 'DTR#', '2': 'RESET'}, g.C0603, 90)
    p.text('DTR# -> C13 -> RESET; D4 clamps positive reset edge.', 154, 244, 1.0)

    # Exactly two address registers, A0-A15. RGB consumes free MCU GPIOs.
    p.text('Two 74HC595 / A0-A15', 290, 28, 1.6)
    for i, x in enumerate([305, 376]):
        sr = {'8': 'GND', '10': '+5V', '11': 'ADDR_SCK',
              '12': 'ADDR_LATCH', '13': 'GND',
              '14': 'ADDR_SER' if i == 0 else 'ADDR_CASCADE',
              '16': '+5V', '9': 'ADDR_CASCADE' if i == 0 else None}
        sr.update({n: 'A' + str(i * 8 + bit)
                   for bit, n in enumerate(['15', '1', '2', '3', '4', '5', '6', '7'])})
        p.component('74xx:74HC595', 'U' + str(i + 2), '74HC595D', x, 76,
                    sr, g.SOIC16)
        p.cap('C' + str(i + 7), '100nF', x, 118, '+5V')
    p.resistor('R4', '10k LATCH', 284, 143, 'ADDR_LATCH', 'GND')
    p.resistor('R2', '10k CE', 321, 143, '+5V', 'ROM_CE#')
    p.resistor('R3', '10k OE', 362, 143, '+5V', 'ROM_OE#')
    p.component('Memory_EPROM:27C512', 'U5', 'NM27C512Q SOCKET', 355, 210,
                EPROM, 'Package_DIP:DIP-28_W15.24mm_Socket_LongPads')
    p.cap('C9', '100nF', 392, 224, '+5V')
    p.text('U3 high byte first, U2 low byte last; MSB first.\nCE#/OE# pull-ups keep EPROM outputs inactive during RESET/ISP.',
           285, 164, 1.0)

    # Three physical indicators: one common-anode RGB and two UART LEDs.
    for i, (net, x, color) in enumerate([('UART_RX', 39, 'RX BLUE'),
                                        ('UART_TX', 110, 'TX ORANGE')]):
        p.resistor('R' + str(8 + i), '10k', x, 199, net, net + '_LED_B', 90)
        p.component('Transistor_BJT:MMBT3906', 'Q' + str(i + 1), 'MMBT3906',
                    x, 229, {'1': net + '_LED_B', '2': '+5V', '3': net + '_LED_C'},
                    'Package_TO_SOT_SMD:SOT-23')
        p.resistor('R' + str(10 + i), '1k', x, 257, net + '_LED_C', net + '_LED_A')
        p.component('Device:LED', 'D' + str(i + 2), color, x + 29, 257,
                    {'1': 'GND', '2': net + '_LED_A'}, 'LED_SMD:LED_0603_1608Metric')
    for i, (colour, short, x) in enumerate([('RED', 'R', 229),
                                            ('GREEN', 'G', 263),
                                            ('BLUE', 'B', 297)]):
        p.resistor('R' + str(i + 5), '1k', x, 228,
                   'STATUS_' + colour, 'RGB_' + short + '_K')
    p.component('ProjectSymbols:RGB_CA_DualMount', 'D1', 'RGB CA / 5050 OR THT5', 264, 265,
                {'1': 'RGB_R_K', '2': '+5V', '3': 'RGB_G_K', '4': 'RGB_B_K'},
                'ProjectFootprints:RGB_CA_5050_or_THT5')
    p.text('RX/TX: PNP buffers, UART LOW = ON, idle HIGH = OFF.', 20, 282, 1.0)
    p.text('RGB: PB0=R / PB1=G / PD2=B; LOW = ON.', 164, 281, 1.0)
    p.save()
    sch_path = OUT / (NAME + '.kicad_sch')
    sch = parse(sch_path.read_text(encoding='utf8'))
    title = one(sch, 'title_block')
    one(title, 'title')[1] = 'NM27C512 Dumper Lite - read-only 5 V'
    one(title, 'comment')[2] = 'NO VPP / NO PROGRAMMING / one sheet / no PCB layout'
    sch_path.write_text('(kicad_sch\n' + '\n'.join('  ' + dump(v) for v in sch[1:])
                        + '\n)\n', encoding='utf8')

    project = json.loads((ROOT / 'baseline_readonly' / 'NM27C512_Dumper.kicad_pro').read_text())
    project['meta']['filename'] = NAME + '.kicad_pro'
    (OUT / (NAME + '.kicad_pro')).write_text(json.dumps(project, indent=2) + '\n', encoding='utf8')
    for filename in ['ProjectSymbols.kicad_sym', 'sym-lib-table', 'fp-lib-table']:
        shutil.copyfile(ROOT / filename, OUT / filename)
    shutil.copytree(ROOT / 'ProjectFootprints.pretty', OUT / 'ProjectFootprints.pretty', dirs_exist_ok=True)
    (OUT / 'validation' / 'bom.json').write_text(json.dumps(g.BOM, indent=2) + '\n', encoding='utf8')
    with (OUT / 'BOM.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['ref', 'value', 'footprint'])
        writer.writeheader()
        writer.writerows({key: part[key] for key in writer.fieldnames} for part in g.BOM)
    print(f'Generated {sch_path}: {len(g.BOM)} components, one sheet, no programming circuit.')


if __name__ == '__main__':
    main()
