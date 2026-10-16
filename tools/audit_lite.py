"""Audit the actual Lite XML netlist, pin/pad coverage and reset-safe wiring."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from generate_schematic import KICAD, footprint_path, standard_erc_rules
from kicad_sexpr import parse, children

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ('Dumper-Lite' if (ROOT / 'Dumper-Lite').exists() else 'lite')


def main():
    checks = []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        checks.append(message)

    tree = ET.parse(OUT / 'validation' / 'netlist.xml')
    nets = {n.attrib['name']: {(p.attrib['ref'], p.attrib['pin']) for p in n.findall('node')}
            for n in tree.findall('./nets/net')}
    by_pin = {pair: name for name, pairs in nets.items() for pair in pairs}

    def expect(ref, mapping):
        for pin, expected in mapping.items():
            actual = by_pin.get((ref, str(pin)))
            if expected is None:
                check(actual is None or actual.startswith('unconnected-'),
                      f'{ref}.{pin}: intentionally unconnected')
            else:
                check(actual == expected, f'{ref}.{pin}: {expected}; actual {actual}')

    # Transcribed independently of the generator's requested wiring.
    expect('U1', {1: None, 2: 'ROM_D6', 3: 'GND', 4: '+5V', 5: 'GND', 6: '+5V',
                  7: 'XTAL1', 8: 'XTAL2', 9: 'ROM_D7', 10: 'ROM_CE#', 11: 'ROM_OE#',
                  12: 'STATUS_RED', 13: 'STATUS_GREEN', 14: 'ADDR_LATCH', 15: 'ADDR_SER',
                  16: 'ISP_MISO', 17: 'ADDR_SCK', 18: '+5V', 19: None, 20: 'AREF',
                  21: 'GND', 22: None, 23: 'ROM_D0', 24: 'ROM_D1', 25: 'ROM_D2',
                  26: 'ROM_D3', 27: 'ROM_D4', 28: 'ROM_D5', 29: 'RESET', 30: 'UART_RX',
                  31: 'UART_TX', 32: 'STATUS_BLUE'})
    expect('U5', {1: 'A15', 2: 'A12', 3: 'A7', 4: 'A6', 5: 'A5', 6: 'A4', 7: 'A3',
                  8: 'A2', 9: 'A1', 10: 'A0', 11: 'ROM_D0', 12: 'ROM_D1', 13: 'ROM_D2',
                  14: 'GND', 15: 'ROM_D3', 16: 'ROM_D4', 17: 'ROM_D5', 18: 'ROM_D6',
                  19: 'ROM_D7', 20: 'ROM_CE#', 21: 'A10', 22: 'ROM_OE#', 23: 'A11',
                  24: 'A9', 25: 'A8', 26: 'A13', 27: 'A14', 28: '+5V'})
    expect('U4', {1: 'GND', 2: 'UART_RX', 3: 'UART_TX', 4: 'CH_V3', 5: 'USB_D+',
                  6: 'USB_D-', 7: None, 8: None, 9: None, 10: None, 11: None,
                  12: None, 13: 'DTR#', 14: None, 15: 'GND', 16: '+5V'})
    expect('J1', {1: '+5V', 2: 'USB_D-', 3: 'USB_D+', 4: None, 5: 'GND', 'SH': 'GND'})
    expect('J2', {1: 'ISP_MISO', 2: '+5V', 3: 'ADDR_SCK', 4: 'ADDR_SER', 5: 'RESET', 6: 'GND'})
    expect('R1', {1: '+5V', 2: 'RESET'})
    expect('SW1', {1: 'RESET', 2: 'GND'})
    expect('C13', {1: 'DTR#', 2: 'RESET'})
    expect('D4', {1: '+5V', 2: 'RESET'})
    expect('R2', {1: '+5V', 2: 'ROM_CE#'})
    expect('R3', {1: '+5V', 2: 'ROM_OE#'})
    expect('R4', {1: 'ADDR_LATCH', 2: 'GND'})
    for index, ref in enumerate(['U2', 'U3']):
        expect(ref, {8: 'GND', 10: '+5V', 11: 'ADDR_SCK', 12: 'ADDR_LATCH', 13: 'GND',
                     14: 'ADDR_SER' if index == 0 else 'ADDR_CASCADE', 16: '+5V',
                     9: 'ADDR_CASCADE' if index == 0 else None})
        expect(ref, {pin: 'A' + str(index * 8 + bit)
                     for bit, pin in enumerate([15, 1, 2, 3, 4, 5, 6, 7])})
    expect('D1', {1: 'RGB_R_K', 2: '+5V', 3: 'RGB_G_K', 4: 'RGB_B_K'})
    for index, colour in enumerate(['RED', 'GREEN', 'BLUE']):
        expect('R' + str(index + 5), {1: 'STATUS_' + colour,
                                      2: 'RGB_' + ['R', 'G', 'B'][index] + '_K'})
    for index, net in enumerate(['UART_RX', 'UART_TX']):
        expect('Q' + str(index + 1), {1: net + '_LED_B', 2: '+5V', 3: net + '_LED_C'})
        expect('R' + str(index + 8), {1: net, 2: net + '_LED_B'})
        expect('R' + str(index + 10), {1: net + '_LED_C', 2: net + '_LED_A'})
        expect('D' + str(index + 2), {1: 'GND', 2: net + '_LED_A'})

    check(nets['ISP_MISO'] == {('U1', '16'), ('J2', '1')}, 'PB4 is used only by ISP')
    for bit in range(8):
        mcu_pin = str([23, 24, 25, 26, 27, 28, 2, 9][bit])
        rom_pin = str([11, 12, 13, 15, 16, 17, 18, 19][bit])
        check(nets['ROM_D' + str(bit)] == {('U1', mcu_pin), ('U5', rom_pin)},
              f'D{bit}: direct EPROM-to-MCU path without other drivers')
    check(not any(any(word in name.upper() for word in ['VPP', 'PROG', '6V25', 'HCT'])
                  for name in nets if not name.startswith('unconnected-')),
          'No programming rails, controls or data buffer')
    comps = {c.attrib['ref']: c for c in tree.findall('./components/comp')}
    check({r for r in comps if r.startswith('U')} == {'U1', 'U2', 'U3', 'U4', 'U5'},
          'Exactly MCU, two 595s, CH340C and EPROM socket')
    check({r for r in comps if r.startswith('J')} == {'J1', 'J2'}, 'Only MicroUSB and ISP headers')
    check({r for r in comps if r.startswith('Q')} == {'Q1', 'Q2'}, 'Only UART indicator buffers')
    for ref in ['R1', 'R2', 'R3', 'R4']:
        check(comps[ref].findtext('value').startswith('10k'), f'{ref}: 10k reset/control bias')
    for ref in ['R5', 'R6', 'R7', 'R10', 'R11']:
        check(comps[ref].findtext('value') == '1k', f'{ref}: LED current limited by 1k')
    for ref in ['R8', 'R9']:
        check(comps[ref].findtext('value') == '10k', f'{ref}: UART base current limited by 10k')
    for ref in ['C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C13']:
        check(comps[ref].findtext('value') == '100nF', f'{ref}: 100nF decoupling/reset capacitor')
    bom = json.loads((OUT / 'validation' / 'bom.json').read_text())
    check(len(comps) == len(bom) == 39, 'Exactly 39 components including required passives')
    for part in bom:
        ref, fp = part['ref'], part['footprint']
        check(comps[ref].findtext('footprint') == fp, f'{ref}: assigned footprint exported')
        path = footprint_path(fp, OUT)
        check(path.is_file(), f'{ref}: installed footprint exists')
        pads = {str(p[1]) for p in children(parse(path.read_text(encoding='utf8')), 'pad') if p[1]}
        check(set(part['nets']) <= pads, f'{ref}: all symbol pins have footprint pads')
        expect(ref, part['nets'])
    erc = json.loads((OUT / 'validation' / 'erc.json').read_text())
    check(not any(s['violations'] for s in erc['sheets']), 'ERC has no violations')
    project = json.loads((OUT / 'NM27C512_Dumper_Lite.kicad_pro').read_text())
    check(standard_erc_rules(project), 'No non-default ignored ERC checks or exclusions')
    report = {'components': len(comps), 'nets': len(nets), 'passed_checks': len(checks),
              'checks': checks, 'hardware_tested': False}
    (OUT / 'validation' / 'connectivity_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Lite audit: {len(checks)} checks passed; {len(comps)} components; footprints verified.')


if __name__ == '__main__':
    main()
