"""Audit exported KiCad connectivity against independently transcribed pin tables.

Run after exporting validation/netlist.xml and baseline_netlist.xml.
This checks actual KiCad nets, not just the generator's requested connections.
"""
from pathlib import Path
import csv
import json
import xml.etree.ElementTree as ET
from kicad_sexpr import parse, children
from generate_schematic import KICAD, footprint_path, standard_erc_rules

ROOT=Path(__file__).resolve().parents[1]
CHECKS=[]
def check(condition,description):
    if not condition:raise AssertionError(description)
    CHECKS.append(description)

def read(path):
    tree=ET.parse(path)
    bypin={}
    nets={}
    for net in tree.findall('./nets/net'):
        name=net.attrib['name'];nodes={(n.attrib['ref'],n.attrib['pin']) for n in net.findall('node')}
        nets[name]=nodes
        for ref,pin in nodes:bypin[ref,pin]=name
    return tree,bypin,nets

def audit(path,bom_path,baseline=False):
    tree,bypin,nets=read(path)
    def expect(ref,mapping):
        for pin,net in mapping.items():
            actual=bypin.get((ref,str(pin)))
            check(actual==net,f'{path.name}: {ref}.{pin} expected {net}, got {actual}')
    mcu={1:'PROG_MODE',2:'ROM_D6',3:'GND',4:'+5V',5:'GND',6:'+5V',7:'XTAL1',8:'XTAL2',9:'ROM_D7',
         10:'TARGET_CE_PGM#',11:'TARGET_OE#',12:'TARGET_PGM#',13:'HV_ARM_EN',14:'ADDR_LATCH',15:'ADDR_SER',16:'ISP_MISO',
         17:'ADDR_SCK',18:'+5V',19:'VPP_SENSE',20:'AREF',21:'GND',22:'TARGET_VCC_SENSE',23:'ROM_D0',24:'ROM_D1',
         25:'ROM_D2',26:'ROM_D3',27:'ROM_D4',28:'ROM_D5',29:'RESET',30:'UART_RX',31:'UART_TX',32:'VPP_EN'}
    if baseline:
        for n in (1,12,13,19,22,32):mcu.pop(n)
        mcu.update({10:'ROM_CE#',11:'ROM_OE#'})
    expect('U1',mcu)
    eprom={1:'A15',2:'A12',3:'A7',4:'A6',5:'A5',6:'A4',7:'A3',8:'A2',9:'A1',10:'A0',
           11:'TARGET_D0',12:'TARGET_D1',13:'TARGET_D2',14:'GND',15:'TARGET_D3',16:'TARGET_D4',17:'TARGET_D5',
           18:'TARGET_D6',19:'TARGET_D7',20:'TARGET_CE_PGM#',21:'A10',22:'SOCKET_OE_VPP',23:'A11',24:'A9',25:'A8',26:'A13',27:'A14',28:'TARGET_VCC'}
    if baseline:
        eprom={k:v.replace('TARGET_D','ROM_D') for k,v in eprom.items()}
        eprom.update({20:'ROM_CE#',22:'ROM_OE#',28:'+5V'})
    expect('U5' if baseline else 'U6',eprom)
    expect('U4' if baseline else 'U5',{1:'GND',2:'CH_TX',3:'CH_RX',4:'CH_V3',5:'USB_D+',6:'USB_D-',13:'DTR#',15:'GND',16:'+5V'})
    expect('J1',{1:'USB_VBUS',2:'USB_D-',3:'USB_D+',5:'GND','SH':'GND'})
    expect('R4',{1:'CH_TX',2:'UART_RX'});expect('R5',{1:'UART_TX',2:'CH_RX'})
    expect('C13',{1:'DTR#',2:'RESET'});expect('R1',{1:'+5V',2:'RESET'})
    expect('J2',{1:'ISP_MISO',2:'+5V',3:'ADDR_SCK',4:'ADDR_SER',5:'RESET',6:'GND'})
    expect('J3',{1:'GND',2:'UART_RX',3:'UART_TX'})
    expect('R7',{1:'ADDR_LATCH',2:'GND'})
    expect('R2',{1:'+5V',2:'ROM_CE#' if baseline else 'TARGET_CE_PGM#'})
    expect('R3',{1:'+5V',2:'ROM_OE#' if baseline else 'TARGET_OE#'})
    q_pins=[15,1,2,3,4,5,6,7]
    for i in range(2 if baseline else 3):
        expect('U'+str(i+2),{16:'+5V',8:'GND',10:'+5V',13:'GND',11:'ADDR_SCK',12:'ADDR_LATCH',14:'ADDR_SER' if i==0 else 'CASCADE_'+str(i)})
        for j,pin in enumerate(q_pins):
            if i<2:expect('U'+str(i+2),{pin:'A'+str(8*i+j)})
            elif j<4:expect('U4',{pin:'A'+str(16+j)})
            elif j<7:expect('U4',{pin:'STATUS_'+['RED','GREEN','BLUE'][j-4]})
        if i<(1 if baseline else 2):expect('U'+str(i+2),{9:'CASCADE_'+str(i+1)})
    if not baseline:
        expect('K1',{1:'+5V',16:'RELAY_COIL_LOW',4:'TARGET_VCC',6:'+5V',8:'+6V25_PROG',13:'SOCKET_OE_VPP',11:'TARGET_OE#',9:'VPP_SW'})
        expect('Q3',{1:'VPP_GATE',2:'HV_ARM',3:'VPP_IN'})
        expect('D5',{1:'VPP_IN',2:'VPP_GATE'})
        expect('Q4',{1:'VPP_NPN_BASE',2:'GND',3:'VPP_PULLDOWN'})
        expect('Q5',{1:'RELAY_BASE',2:'GND',3:'RELAY_COIL_LOW'})
        expect('Q6',{1:'PULSE_NPN_BASE',2:'GND',3:'PULSE_PULLDOWN'})
        expect('Q7',{1:'PULSE_PNP_BASE',2:'HV_ARM',3:'VPP_SW'})
        expect('D8',{1:'+5V',2:'RELAY_COIL_LOW'});expect('D9',{1:'+5V',2:'RESET'})
        expect('U7',{1:'LM_ADJ',2:'+6V25_PROG',3:'VPP_IN'})
        expect('RV1',{1:'LM_TRIM',2:'GND',3:'GND'})
        expect('U8',{1:'VPP_EN',2:'RESET',3:'GND',4:'VPP_DRIVE',5:'+5V'})
        expect('U10',{1:'HV_ARM_EN',2:'RESET',3:'GND',4:'HV_ARM_DRIVE',5:'+5V'})
        expect('U9',{1:'VPP_DRIVE',19:'GND',20:'+5V',10:'GND'})
        expect('D2',{1:'RGB_R_K',2:'+5V',3:'RGB_G_K',4:'RGB_B_K'})
        expect('D30',{1:'GND',2:'+5V',3:'VPP_SENSE'});expect('D31',{1:'GND',2:'+5V',3:'TARGET_VCC_SENSE'})
        for i in range(8):
            expect('R'+str(10+i),{1:'HCT_A'+str(i),2:'ROM_D'+str(i)})
            expect('D'+str(10+i),{1:'GND',2:'+5V',3:'ROM_D'+str(i)})
            expect('U9',{i+2:'HCT_A'+str(i),18-i:'HCT_B'+str(i)})
            expect('R'+str(50+i),{1:'TARGET_D'+str(i),2:'HCT_B'+str(i)})
            expect('D'+str(20+i),{1:'GND',2:'+5V',3:'HCT_B'+str(i)})
        for ref,mapping in {'R35':{1:'VPP_SW',2:'VPP_SENSE'},'R36':{1:'VPP_SENSE',2:'GND'},
                            'R45':{1:'TARGET_VCC',2:'TARGET_VCC_SENSE'},'R46':{1:'TARGET_VCC_SENSE',2:'GND'}}.items():expect(ref,mapping)
        header={i+1:'A'+str(i) for i in range(20)}
        header.update({21+i:'TARGET_D'+str(i) for i in range(8)})
        header.update(dict(zip(range(29,41),['TARGET_CE_PGM#','TARGET_OE#','TARGET_PGM#','VPP_SW','TARGET_VCC','+5V','+6V25_PROG','GND','PROG_MODE','GND','RESET','GND'])))
        expect('J5',header)
        for name in ['VPP_IN','VPP_GATE','VPP_PULLDOWN','HV_ARM','VPP_SW','PULSE_PNP_BASE','PULSE_PULLDOWN','+6V25_PROG','TARGET_VCC','SOCKET_OE_VPP']:
            check(not any(ref=='U1' for ref,pin in nets.get(name,set())),f'No direct high voltage net {name} at U1')
        check(nets['ISP_MISO']=={('U1','16'),('J2','1')},'PB4/MISO used only for ISP')
    else:
        check(not any(name in nets for name in ['VPP_IN','VPP_SW','+6V25_PROG','HV_ARM']),'Baseline contains no programming rails')
    components={c.attrib['ref']:c for c in tree.findall('./components/comp')}
    bom=json.loads(bom_path.read_text())
    check(len(components)==len(bom),f'{path.name}: BOM count agrees with actual export')
    for part in bom:
        ref=part['ref'];fp=part['footprint']
        check(components[ref].findtext('footprint')==fp,f'{ref}: footprint exported correctly')
        fp_file=footprint_path(fp, ROOT/'baseline_readonly' if baseline else ROOT)
        check(fp_file.is_file(),f'{ref}: installed footprint exists')
        pads={str(p[1]) for p in children(parse(fp_file.read_text(encoding='utf8')),'pad') if p[1]}
        check(set(part['nets'])<=pads,f'{ref}: physical footprint has every numbered symbol pin')
        for pin,net in part['nets'].items():
            if net is not None:expect(ref,{pin:net})
    return len(components),len(nets)

def main():
    main_count,main_nets=audit(ROOT/'validation/netlist.xml',ROOT/'validation/bom.json')
    base_count,base_nets=audit(ROOT/'validation/baseline_netlist.xml',ROOT/'validation/baseline_bom.json',True)
    for name,folder in [('erc.json',ROOT),('baseline_erc.json',ROOT/'baseline_readonly')]:
        erc=json.loads((ROOT/'validation'/name).read_text())
        check(not any(s['violations'] for s in erc['sheets']),f'{name}: no ERC violations')
        pro=json.loads((folder/'NM27C512_Dumper.kicad_pro').read_text())
        check(standard_erc_rules(pro),f'{name}: no non-default ignored checks/exclusions')
    profiles=json.loads((ROOT/'device_profiles.json').read_text())['profiles']
    nm=next(p for p in profiles if p['name']=='NM27C512')
    check(nm['size_bytes']==65536 and nm['address_bits']==16,'NM27C512 image size')
    check(nm['program_pulse_us']==100 and nm['max_program_pulses']==25,'National 100us / maximum 25 pulses')
    check(nm['program_vpp_min']==12.5 and nm['program_vpp_max']==13.0 and nm['program_vpp_absolute_max']==14.0,'National programming voltage limits')
    check(sum(p['program_supported'] for p in profiles)==1,'Only verified NM27C512 programming algorithm enabled in profiles')
    report={'kicad_version':'10.0.6','main_components':main_count,'main_nets':main_nets,'baseline_components':base_count,'baseline_nets':base_nets,
            'passed_checks':len(CHECKS),'checks':CHECKS,'hardware_tested':False}
    (ROOT/'validation/connectivity_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    for input_name,output_name in [('bom.json','BOM.csv'),('baseline_bom.json','baseline_BOM.csv')]:
        with (ROOT/'validation'/output_name).open('w',newline='',encoding='utf8') as f:
            writer=csv.DictWriter(f,fieldnames=['ref','value','symbol','footprint','sheet']);writer.writeheader()
            for row in json.loads((ROOT/'validation'/input_name).read_text()):writer.writerow({k:row[k] for k in writer.fieldnames})
    print(f'PASS: {len(CHECKS)} connectivity, footprint and profile checks; {main_count} Stage2 / {base_count} baseline components.')
if __name__=='__main__':main()
