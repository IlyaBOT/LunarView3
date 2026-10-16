"""Generate editable KiCad 10 schematics using the installed standard libraries.

Run from the project root. The original read-only project is retained separately.
No ERC rules are disabled and no PCB is generated.
"""
from pathlib import Path
import copy
import json
import math
import os
import re
import uuid
from kicad_sexpr import Atom as A, node as N, one, children, parse, dump

ROOT = Path(__file__).resolve().parents[1]
_installed=list((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'KiCad').glob('*/share/kicad'))
KICAD = max(_installed,key=lambda p:tuple(map(int,re.findall(r'\d+',p.parent.parent.name))))
LIBS = {}
USED = {}
BOM = []
COUNTERS = {}
NAME = 'NM27C512_Dumper'
R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
SOIC16 = 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm'
TP = 'TestPoint:TestPoint_Pad_D1.5mm'

def footprint_path(lib_id, project_folder=ROOT):
    lib, name = lib_id.split(':')
    if lib == 'ProjectFootprints':
        return project_folder / 'ProjectFootprints.pretty' / (name + '.kicad_mod')
    return KICAD / 'footprints' / (lib + '.pretty') / (name + '.kicad_mod')

def standard_erc_rules(project):
    ignored = {'single_global_label', 'four_way_junction', 'simulation_model_issue', 'footprint_filter'}
    # KiCad's GUI expands the default dictionary when saving a project.
    # An expanded default dictionary is not a new suppression.
    return not project['erc']['erc_exclusions'] and all(
        severity != 'ignore' or name in ignored
        for name, severity in project['erc']['rule_severities'].items())

def uid(key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'NM27C512_Dumper/RevA/' + key))

def standard(lib_id):
    if lib_id in USED:
        return copy.deepcopy(USED[lib_id])
    lib, name = lib_id.split(':')
    if lib not in LIBS:
        source = ROOT/'ProjectSymbols.kicad_sym' if lib=='ProjectSymbols' else KICAD/'symbols'/f'{lib}.kicad_sym'
        LIBS[lib] = {s[1]: s for s in children(parse(source.read_text(encoding='utf8')), 'symbol')}
    s = copy.deepcopy(LIBS[lib][name])
    ext = one(s, 'extends')
    if ext:
        base = standard(lib + ':' + ext[1])
        base_name = base[1].split(':')[-1]
        for sub in children(base, 'symbol'):
            sub[1] = name + sub[1][len(base_name):]
        props = {p[1]: p for p in children(s, 'property')}
        base = [c for c in base if not (isinstance(c, list) and c[0] == 'property' and c[1] in props)]
        base.extend(copy.deepcopy(list(props.values())))
        s = base
    s[1] = lib_id
    USED[lib_id] = copy.deepcopy(s)
    return s

def pins(s):
    return [p for sub in children(s, 'symbol') for p in children(sub, 'pin')]

def effects(size=1.0, justify=None, hide=False):
    e = N('effects', N('font', N('size', size, size)))
    if justify:
        e.append(N('justify', A(justify)))
    if hide:
        e.append(N('hide', A('yes')))
    return e

class Page:
    def __init__(self, filename, title, folder, root_uuid, index=1):
        self.filename, self.folder, self.index = filename, folder, index
        self.uuid = root_uuid if index == 1 else uid(folder.name + '/' + filename)
        self.root_uuid = root_uuid
        self.path = '/' + root_uuid + (('/' + self.uuid) if index != 1 else '')
        self.items, self.libs, self.serial = [], {}, 0
        self.power_positions = []
        self.text(title, 15, 15, 2.5)

    def id(self):
        self.serial += 1
        return uid(self.folder.name + '/' + self.filename + '/' + str(self.serial))

    def text(self, text, x, y, size=1.3):
        self.items.append(N('text', text, N('at', x, y, 0), effects(size, 'left'), N('uuid', self.id())))

    def line(self, p, q, graphical=False):
        self.items.append(N('polyline' if graphical else 'wire', N('pts', N('xy', *p), N('xy', *q)),
                            N('stroke', N('width', 0.2 if graphical else 0), N('type', A('default'))), N('uuid', self.id())))

    def box(self, x, y, w, h):
        self.items.append(N('rectangle', N('start', x, y), N('end', x+w, y+h),
            N('stroke', N('width', 0.25), N('type', A('default'))), N('fill', N('type', A('none'))), N('uuid', self.id())))

    def label(self, net, x, y, angle=0):
        self.items.append(N('global_label', net, N('shape', A('bidirectional')), N('at', x, y, angle),
            effects(0.95, 'left' if angle in (0,90) else 'right'), N('uuid', self.id()),
            N('property', 'Intersheetrefs', '${INTERSHEET_REFS}', N('at', x, y, angle), effects(0.9, hide=True))))

    def component(self, lib_id, ref, value, x, y, nets, footprint=None, angle=0, dnp=False):
        x, y = round(round(x/1.27)*1.27,6), round(round(y/1.27)*1.27,6)
        s = standard(lib_id)
        self.libs[lib_id] = s
        power = lib_id.startswith('power:')
        fp = footprint if footprint is not None else next((p[2] for p in children(s, 'property') if p[1] == 'Footprint'), '')
        sym_id = self.id()
        inst = N('symbol', N('lib_id', lib_id), N('at', x, y, angle), N('unit', 1),
            N('in_bom', A('no' if power else 'yes')), N('on_board', A('no' if power else 'yes')),
            N('dnp', A('yes' if dnp else 'no')), N('uuid', sym_id))
        ps = pins(s)
        if not power:
            assert set(nets)=={str(one(p,'number')[1]) for p in ps}, f'{ref}: mapping must explicitly cover every library pin'
        # Put references/values above each IC and beside vertical passives.
        top = max((float(one(p, 'at')[2]) for p in ps), default=0)
        if power:
            prop_xy = {'Reference': (x, y-5), 'Value': (x, y-3)}
        elif len(ps) > 3 or lib_id.startswith(('Connector','Transistor','Diode:','Regulator_Linear:')) or lib_id in ('Device:LED','Device:Crystal','Switch:SW_Push','Device:D','Device:D_Zener','Device:D_Schottky','Device:R_Potentiometer','Device:Polyfuse'):
            prop_xy = {'Reference': (x, y-top-14), 'Value': (x, y-top-11)}
        elif angle == 0:
            prop_xy = {'Reference': (x+4, y-1.5), 'Value': (x+4, y+1.5)}
        else:
            prop_xy = {'Reference': (x, y-5.5), 'Value': (x, y-2.7)}
        for name, val in [('Reference',ref), ('Value',value), ('Footprint',fp), ('Datasheet',next((p[2] for p in children(s,'property') if p[1]=='Datasheet'),''))]:
            px, py = prop_xy.get(name, (x, y))
            beside = not power and px == x+4
            prop_angle = 90 if angle % 180 else 0
            inst.append(N('property', name, val, N('at',px,py,prop_angle), effects(1.1, 'left' if beside else None,
                hide=(power and (name=='Reference' or (name=='Value' and lib_id=='power:GND'))) or name in ('Footprint','Datasheet'))))
        pin_coords = {}
        wired_positions = set()
        for p in ps:
            num = str(one(p, 'number')[1])
            px, py, pa = map(float, one(p, 'at')[1:4])
            a = math.radians(angle)
            # KiCad page Y is opposite symbol-local Y.
            wx, wy = round(x+px*math.cos(a)-py*math.sin(a),6), round(y-px*math.sin(a)-py*math.cos(a),6)
            pin_coords[num] = [wx, wy]
            inst.append(N('pin', num, N('uuid', uid(sym_id+'/'+num))))
            if power:
                continue
            net = nets.get(num)
            if (wx,wy,net) in wired_positions:
                continue
            wired_positions.add((wx,wy,net))
            if net is None:
                self.items.append(N('no_connect', N('at',wx,wy), N('uuid',self.id())))
            else:
                rad = math.radians(pa + angle)
                ex, ey = round(wx-3.81*math.cos(rad),6), round(wy+3.81*math.sin(rad),6)
                self.line((wx,wy),(ex,ey))
                if net in ('GND','+5V'):
                    self.power(net,ex,ey)
                else:
                    if round(math.cos(rad)) == 0:
                        # Bend vertical stubs so long net names do not cover IC properties.
                        self.line((ex,ey),(ex+5.08,ey))
                        self.label(net,ex+5.08,ey,0)
                    else:
                        self.label(net,ex,ey,0 if round(math.cos(rad)) == -1 else 180)
        inst.append(N('instances', N('project',NAME, N('path',self.path, N('reference',ref), N('unit',1)))))
        self.items.append(inst)
        if not power:
            assert fp, f'No footprint: {ref}'
            assert footprint_path(fp, self.folder).exists(), fp
            BOM.append({'sheet':self.filename,'ref':ref,'value':value,'symbol':lib_id,'footprint':fp,'nets':nets})
        return pin_coords

    def power(self, net, x, y, flag=False):
        x, y = round(round(x/1.27)*1.27,6), round(round(y/1.27)*1.27,6)
        if not flag:
            for old_net, ox, oy in self.power_positions:
                if old_net==net and abs(oy-y)<0.001 and abs(ox-x)<=2.55:
                    if (ox,oy)!=(x,y): self.line((x,y),(ox,oy))
                    return
            self.power_positions.append((net,x,y))
        key = self.folder.name
        COUNTERS[key] = COUNTERS.get(key,0) + 1
        self.component('power:' + ('PWR_FLAG' if flag else net), '#FLG' + str(COUNTERS[key]) if flag else '#PWR'+str(COUNTERS[key]), 'PWR_FLAG' if flag else net, x,y,{},'')
        if flag:
            self.label(net,x,y)

    def resistor(self, ref, value, x, y, net1, net2, angle=0, footprint=R0603):
        return self.component('Device:R',ref,value,x,y,{'1':net1,'2':net2},footprint,angle)

    def cap(self, ref, value, x,y,net,footprint=C0603):
        self.component('Device:C',ref,value,x,y,{'1':net,'2':'GND'},footprint)

    def child(self, child, title, x,y,w=95,h=24):
        self.items.append(N('sheet',N('at',x,y),N('size',w,h),N('stroke',N('width',0.25),N('type',A('default'))),
            N('fill',N('color',0,0,0,0)),N('uuid',child.uuid),
            N('property','Sheetname',title,N('at',x,y-2,0),effects(1.4,'left')),
            N('property','Sheetfile',child.filename,N('at',x,y+h+2,0),effects(1.05,'left')),
            N('instances',N('project',NAME,N('path','/'+self.root_uuid,N('page',str(child.index)))))))

    def save(self):
        doc=N('kicad_sch',N('version',20250114),N('generator',A('eeschema')),N('generator_version','10.0'),N('uuid',self.uuid),
            N('paper','A3'),N('title_block',N('title','NM27C512 Dumper - '+('read-only baseline' if self.folder.name=='baseline_readonly' else 'Stage 2 Rev A')),
            N('date','2026-10-06'),N('rev','A'),N('comment',1,'5 V ONLY / NO VPP / no PCB layout' if self.folder.name=='baseline_readonly' else '5 V logic / external VPP only / no PCB layout')),N('lib_symbols',*self.libs.values()),*self.items)
        if self.index == 1:
            doc.append(N('sheet_instances',N('path','/',N('page','1'))))
        doc.append(N('embedded_fonts',A('no')))
        # One complete top-level item per line makes later edits/diffs practical.
        out='(kicad_sch\n'+'\n'.join('  '+dump(v) for v in doc[1:])+'\n)\n'
        (self.folder/self.filename).write_text(out,encoding='utf8')

MCU_NETS = {'1':'PROG_MODE','2':'ROM_D6','3':'GND','4':'+5V','5':'GND','6':'+5V','7':'XTAL1','8':'XTAL2','9':'ROM_D7',
    '10':'TARGET_CE_PGM#','11':'TARGET_OE#','12':'TARGET_PGM#','13':'HV_ARM_EN','14':'ADDR_LATCH','15':'ADDR_SER','16':'ISP_MISO',
    '17':'ADDR_SCK','18':'+5V','19':'VPP_SENSE','20':'AREF','21':'GND','22':'TARGET_VCC_SENSE','23':'ROM_D0','24':'ROM_D1',
    '25':'ROM_D2','26':'ROM_D3','27':'ROM_D4','28':'ROM_D5','29':'RESET','30':'UART_RX','31':'UART_TX','32':'VPP_EN'}
EPROM_NETS={'1':'A15','2':'A12','3':'A7','4':'A6','5':'A5','6':'A4','7':'A3','8':'A2','9':'A1','10':'A0','11':'TARGET_D0',
    '12':'TARGET_D1','13':'TARGET_D2','14':'GND','15':'TARGET_D3','16':'TARGET_D4','17':'TARGET_D5','18':'TARGET_D6','19':'TARGET_D7',
    '20':'TARGET_CE_PGM#','21':'A10','22':'SOCKET_OE_VPP','23':'A11','24':'A9','25':'A8','26':'A13','27':'A14','28':'TARGET_VCC'}
CH_NETS={'1':'GND','2':'CH_TX','3':'CH_RX','4':'CH_V3','5':'USB_D+','6':'USB_D-','7':None,'8':None,'9':None,'10':None,
    '11':None,'12':None,'13':'DTR#','14':None,'15':'GND','16':'+5V'}

def controller(p, stage):
    p.text('USB input and internal-clock USB UART',20,28,1.6)
    p.component('Connector:USB_B_Micro','J1','USB Micro-B',45,65,{'1':'USB_VBUS','2':'USB_D-','3':'USB_D+','4':None,'5':'GND','SH':'GND'},
        'Connector_USB:USB_Micro-B_Molex-105017-0001')
    p.component('Device:Polyfuse','F1','500mA hold',45,112,{'1':'USB_VBUS','2':'+5V'},'Fuse:Fuse_1812_4532Metric')
    p.power('+5V',48,140,True)
    p.cap('C1','10uF / 10V',98,110,'+5V','Capacitor_SMD:C_0805_2012Metric')
    p.component('ProjectSymbols:CH340C_WCH','U5' if stage else 'U4','CH340C',132,65,CH_NETS,SOIC16)
    p.cap('C2','100nF',132,115,'+5V'); p.cap('C3','100nF',167,115,'CH_V3')
    p.text('CH340C: no 12 MHz crystal. R232 = GND (TTL mode).\nPins 7/8 are variant-dependent: leave unconnected.\nOnly DTR# (13) is used; other modem pins are NC.',20,155,1.25)
    p.resistor('R4','1k',197,52,'CH_TX','UART_RX',90)
    p.resistor('R5','1k',197,77,'UART_TX','CH_RX',90)
    nets=copy.deepcopy(MCU_NETS)
    if not stage:
        for n in ('1','12','13','19','22','32'): nets[n]=None
        nets['10']='ROM_CE#'; nets['11']='ROM_OE#'
    p.component('MCU_Microchip_ATmega:ATmega328P-A','U1','ATmega328P-AU',285,80,nets,'Package_QFP:TQFP-32_7x7mm_P0.8mm')
    p.text('ATmega328P-AU / 16 MHz / 5 V',235,28,1.6)
    p.component('Device:Crystal','Y1','16MHz, CL ~18pF',255,157,{'1':'XTAL1','2':'XTAL2'},'Crystal:Crystal_HC49-4H_Vertical')
    p.cap('C11','22pF',231,188,'XTAL1'); p.cap('C12','22pF',273,188,'XTAL2')
    p.resistor('R1','10k',338,155,'+5V','RESET')
    p.component('Switch:SW_Push','SW1','RESET',375,177,{'1':'RESET','2':'GND'},'Button_Switch_THT:SW_PUSH_6mm')
    p.component('Device:C','C13','100nF auto-reset',337,198,{'1':'DTR#','2':'RESET'},C0603,90)
    if stage:
        p.component('Device:D_Schottky','D9','BAT54WS RESET clamp',379,212,{'1':'+5V','2':'RESET'},'Diode_SMD:D_SOD-323')
        p.text('D9 clamps the positive DTR edge on RESET, protecting the 5V interlock inputs.',230,265,1.05)
    for i,x in enumerate([246,281,316,351]): p.cap('C'+str(4+i),'100nF',x,235,'+5V' if i<3 else 'AREF')
    # Preserve original capacitor numbering: C7 is on the first 595, AREF is C10.
    for b in BOM:
        if b['sheet']==p.filename and b['ref']=='C7': b['ref']='C10'
    for item in p.items:
        if isinstance(item,list) and item[0]=='symbol':
            for prop in children(item,'property'):
                if prop[1]=='Reference' and prop[2]=='C7': prop[2]='C10'
            inst=one(item,'instances')
            if inst:
                for pr in children(inst,'project'):
                    for path in children(pr,'path'):
                        r=one(path,'reference')
                        if r and r[1]=='C7': r[1]='C10'
    p.component('Connector:AVR-ISP-6','J2','AVR ISP',73,209,{'1':'ISP_MISO','2':'+5V','3':'ADDR_SCK','4':'ADDR_SER','5':'RESET','6':'GND'},
        'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical')
    p.component('Connector_Generic:Conn_01x03','J3','UART (MCU RX/TX)',170,213,{'1':'GND','2':'UART_RX','3':'UART_TX'},
        'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
    p.text('J2: 1 MISO, 2 +5V, 3 SCK,\n4 MOSI, 5 RESET, 6 GND.\nNever power J2 and USB from competing sources.',20,241,1.15)
    p.text('J3 names are from MCU viewpoint.\n1 = GND   2 = RX (PD0)   3 = TX (PD1)\nUse 5 V TTL UART; avoid simultaneous UART drivers.',124,241,1.15)

def targets(p, stage):
    p.text('Address / status shift registers: SPI shifts while latch stays LOW',20,28,1.6)
    for i,x in enumerate([68,169,270] if stage else [68,169]):
        nets={'8':'GND','10':'+5V','11':'ADDR_SCK','12':'ADDR_LATCH','13':'GND','14':'ADDR_SER' if i==0 else 'CASCADE_'+str(i), '16':'+5V'}
        qnums=['15','1','2','3','4','5','6','7']
        for b,n in enumerate(qnums): nets[n]= 'A'+str(i*8+b) if i<2 or b<4 else ['STATUS_RED','STATUS_GREEN','STATUS_BLUE',None][b-4]
        nets['9']='CASCADE_'+str(i+1) if i < (2 if stage else 1) else None
        p.component('74xx:74HC595','U'+str(i+2),'74HC595D',x,68,nets,SOIC16)
        p.cap('C'+str(7+i if i<2 else 14),'100nF',x,111,'+5V')
    p.resistor('R7','10k LATCH pull-down',363,72,'ADDR_LATCH','GND')
    p.text(('Send U4 byte first, U3 byte second, U2 byte last; MSB first.\nU2 Q0-Q7 = A0-A7; U3 Q0-Q7 = A8-A15.\nStage 2: U4 Q0-Q3 = A16-A19; Q4/Q5/Q6 = active-low R/G/B.\nOE# = GND and SRCLR# = +5V on every 595.' if stage else
        'Send U3 (A8-A15) byte first, U2 (A0-A7) byte last; MSB first.\nU2 Q0-Q7 = A0-A7; U3 Q0-Q7 = A8-A15.\nOE# = GND and SRCLR# = +5V on both 595.\nU4 is the CH340C in this read-only project.'),20,140,1.25)
    nets=copy.deepcopy(EPROM_NETS)
    if not stage:
        nets={n: (v.replace('TARGET_D','ROM_D') if v else v) for n,v in nets.items()}
        nets.update({'20':'ROM_CE#','22':'ROM_OE#','28':'+5V'})
    p.component('Memory_EPROM:27C512','U6' if stage else 'U5','NM27C512Q SOCKET',281,212,nets,'Package_DIP:DIP-28_W15.24mm_Socket_LongPads')
    p.cap('C9','100nF / 16V',356,185,'TARGET_VCC' if stage else '+5V')
    p.resistor('R2','10k CE pull-up',68,195,'+5V','TARGET_CE_PGM#' if stage else 'ROM_CE#')
    p.resistor('R3','10k OE pull-up',125,195,'+5V','TARGET_OE#' if stage else 'ROM_OE#')
    if stage:
        p.resistor('R8','10k PGM pull-up',68,239,'+5V','TARGET_PGM#')
        p.cap('C15','10uF / 16V',356,231,'TARGET_VCC','Capacitor_SMD:C_0805_2012Metric')
        p.text('Direct socket U6 is dedicated to NM27C512.\nOne target only: socket OR adapter.\nPin 20 = CE/PGM#; pin 22 = OE/VPP via K1.\nREAD: +5V, OE logic. PROG: +6.25V, switched VPP.\nDo not insert/remove a target with USB or VPP connected.',20,264,1.15)
    else:
        p.resistor('R6','1k',167,204,'+5V','POWER_LED_A')
        p.component('Device:LED','D1','POWER GREEN',167,239,{'1':'GND','2':'POWER_LED_A'},'LED_SMD:LED_0603_1608Metric')
        p.text('NM27C512 READ-ONLY DUMPER\n5 V ONLY\nNO VPP PROGRAMMING VOLTAGE\nCE# and OE# default HIGH in reset and ISP.',20,239,1.5)

def protection(p):
    p.text('Eight bidirectional data paths: series current limit + external Schottky clamps',20,28,1.6)
    for i in range(8):
        x=48+(i%4)*96; y=57+(i//4)*61
        p.resistor('R'+str(10+i),'1k',x,y,'HCT_A'+str(i),'ROM_D'+str(i),90)
        p.component('Diode:BAT54S','D'+str(10+i),'BAT54S',x,y+27,{'1':'GND','2':'+5V','3':'ROM_D'+str(i)},'Package_TO_SOT_SMD:SOT-23')
    p.text('BAT54S: pin 1 anode = GND; pin 2 cathode = +5V; pin 3 midpoint = MCU data.\nHigh data clamps toward +5V; negative data clamps toward GND. No target HV on these paths.\n1k limits MCU/buffer contention. HCT245 and target-side protection are on the TTL bus sheet.',20,168,1.2)
    p.resistor('R6','1k',36,211,'+5V','POWER_LED_A')
    p.component('Device:LED','D1','POWER GREEN',36,244,{'1':'GND','2':'POWER_LED_A'},'LED_SMD:LED_0603_1608Metric')
    p.component('ProjectSymbols:RGB_CA_DualMount','D2','RGB CA / 5050 OR THT5',366,232,{'1':'RGB_R_K','2':'+5V','3':'RGB_G_K','4':'RGB_B_K'},
        'ProjectFootprints:RGB_CA_5050_or_THT5',0)
    for i,net in enumerate(['RED','GREEN','BLUE']):
        p.resistor('R'+str(20+i),'1k',263+i*35,216,'STATUS_'+net,'RGB_'+['R','G','B'][i]+'_K')
    for i,(net,x,color) in enumerate([('UART_RX',111,'RX BLUE'),('UART_TX',194,'TX ORANGE')]):
        p.component('Transistor_BJT:MMBT3906','Q'+str(1+i),'MMBT3906',x,218,{'1':net+'_LED_B','2':'+5V','3':net+'_LED_C'},'Package_TO_SOT_SMD:SOT-23')
        p.resistor('R'+str(23+i),'10k',x,188,net,net+'_LED_B',90)
        p.resistor('R'+str(25+i),'1k',x,245,net+'_LED_C',net+'_LED_A')
        p.component('Device:LED','D'+str(3+i),color,x+28,245,{'1':'GND','2':net+'_LED_A'},'LED_SMD:LED_0603_1608Metric')
    p.text('RGB cathode LOW = ON. Green: READ; Red: WRITE; Amber: IDLE; Blue: ERROR.\nRX/TX PNP emitters = +5V; base current is limited by 10k. UART HIGH idle = LEDs OFF.\nD2: combined SMD 5050 / THT5 footprint. Populate ONE ONLY; pads 1R/2A/3G/4B.',20,280,1.05)

def ttl_bus(p):
    p.text('TTL-compatible bidirectional buffer: preserves reads from older 27xx EPROMs',20,28,1.6)
    nets={'1':'VPP_DRIVE','10':'GND','19':'GND','20':'+5V'}
    for i in range(8):
        nets[str(i+2)]='HCT_A'+str(i)
        nets[str(18-i)]='HCT_B'+str(i)
    p.component('74xx:74HC245','U9','SN74HCT245DW',78,87,nets,'Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm')
    p.cap('C26','100nF',149,90,'+5V')
    p.text('DIR = VPP_DRIVE: LOW -> target-to-MCU (READ/VERIFY); HIGH -> MCU-to-target (PROGRAM).\nOE# tied LOW. Firmware releases MCU data outputs BEFORE removing VPP.\n74HCT input VIH = 2.0V; MCU sees full 5V logic. Do not substitute 74HC245.\nMCU-side R10-R17 and D10-D17 are on data/status sheet. Target-side protection below.',20,144,1.3)
    for i in range(8):
        x=47+(i%4)*97;y=164+(i//4)*48
        p.resistor('R'+str(50+i),'1k',x,y,'TARGET_D'+str(i),'HCT_B'+str(i),90)
        p.component('Diode:BAT54S','D'+str(20+i),'BAT54S',x,y+28,{'1':'GND','2':'+5V','3':'HCT_B'+str(i)},'Package_TO_SOT_SMD:SOT-23')
    p.text('Target-side clamps keep +6.25V verify outputs away from the 5V buffer. Maximum nominal injection ~1mA/line.\nUSB-powered logic and relay draw more current than all eight clamps inject; never operate with USB absent.',20,280,1.05)

def high_voltage(p):
    p.text('External regulated supply only: 12.5...25 V. Select the voltage for the exact device.',20,28,1.6)
    p.component('Connector_Generic:Conn_01x02','J4','J_VPP_IN',39,64,{'1':'VPP_IN','2':'GND'},'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal')
    p.power('VPP_IN',30,95,True)
    p.cap('C20','100nF / 50V',75,61,'VPP_IN')
    # IRF9540N is a standard 100 V P-MOS. Local source is UP on this sheet.
    p.component('Transistor_FET:IRF9540N','Q3','IRF9540N / 100V PMOS',141,63,{'1':'VPP_GATE','2':'HV_ARM','3':'VPP_IN'},'Package_TO_SOT_THT:TO-220-3_Vertical',180)
    p.resistor('R30','47k gate-source',105,93,'VPP_IN','VPP_GATE')
    p.component('Device:D_Zener','D5','BZT52C10 / 10V',165,105,{'1':'VPP_IN','2':'VPP_GATE'},'Diode_SMD:D_SOD-123')
    p.resistor('R31','2.2k / 0.25W',211,67,'VPP_GATE','VPP_PULLDOWN',0,'Resistor_SMD:R_1206_3216Metric')
    p.component('Transistor_BJT:MMBT3904','Q4','MMBT3904',249,91,{'1':'VPP_NPN_BASE','2':'GND','3':'VPP_PULLDOWN'},'Package_TO_SOT_SMD:SOT-23')
    p.resistor('R32','1k',216,119,'HV_ARM_DRIVE','VPP_NPN_BASE',90)
    p.resistor('R33','10k base pull-down',266,129,'VPP_NPN_BASE','GND')
    p.component('74xGxx:74LVC1G08','U10','74LVC1G08 / arm interlock',335,73,{'1':'HV_ARM_EN','2':'RESET','3':'GND','4':'HV_ARM_DRIVE','5':'+5V'},'Package_TO_SOT_SMD:SOT-23-5')
    p.cap('C27','100nF',370,113,'+5V')
    p.resistor('R60','10k arm pull-down',335,129,'HV_ARM_EN','GND')
    p.text('Gate Zener: cathode to SOURCE/VPP_IN, anode to GATE.\nQ4 collector pulls gate through R31; emitter = GND.\nRESET LOW forces U10 output LOW immediately.\nPB1 is the hardware arming interlock; PD2 controls the final pulse switch.',20,138,1.15)
    p.cap('C28','100nF / 50V',335,202,'HV_ARM')
    p.resistor('R61','100k bleed',335,235,'HV_ARM','GND')
    p.component('Regulator_Linear:LM317_TO-220','U7','LM317T: calibrate 6.250 V',68,192,{'1':'LM_ADJ','2':'+6V25_PROG','3':'VPP_IN'},'Package_TO_SOT_THT:TO-220-3_Vertical')
    p.cap('C23','100nF / 50V',26,192,'VPP_IN')
    p.cap('C24','10uF / 16V',115,188,'+6V25_PROG','Capacitor_SMD:C_1206_3216Metric')
    p.resistor('R40','120R / 1%',68,222,'+6V25_PROG','LM_ADJ')
    p.resistor('R41','430R / 1%',116,224,'LM_ADJ','LM_TRIM')
    p.component('Device:R_Potentiometer','RV1','100R multi-turn',172,223,{'1':'LM_TRIM','2':'GND','3':'GND'},'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical')
    p.component('Device:D','D7','1N4007 output protection',67,256,{'1':'VPP_IN','2':'+6V25_PROG'},'Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal')
    p.text('Vout = 1.25*(1+(430+trim)/120) + Iadj*(430+trim).\nSet trim near 48 ohm; measure TP_6V25 unloaded and loaded.\nTO-220 tab is OUTPUT. At 25V/60mA dissipation is ~1.13W: heatsink.\n120 ohm feedback draws ~10.4mA, including with K1 in READ.',20,277,1.05)

def pulse_switch(p):
    p.text('Final VPP pulse switch: separate slow arming from pin22 rise/verify switching',20,28,1.6)
    p.component('Transistor_BJT:Q_PNP_BEC','Q7','MMBT5401 / 150V PNP',122,75,{'1':'PULSE_PNP_BASE','2':'HV_ARM','3':'VPP_SW'},'Package_TO_SOT_SMD:SOT-23')
    p.resistor('R62','10k base-emitter',66,104,'HV_ARM','PULSE_PNP_BASE')
    p.resistor('R63','2.2k / 0.25W',166,110,'PULSE_PNP_BASE','PULSE_PULLDOWN',0,'Resistor_SMD:R_1206_3216Metric')
    p.component('Transistor_BJT:Q_NPN_BEC','Q6','MMBT5551 / 160V NPN',225,80,{'1':'PULSE_NPN_BASE','2':'GND','3':'PULSE_PULLDOWN'},'Package_TO_SOT_SMD:SOT-23')
    p.resistor('R64','1k',225,131,'VPP_DRIVE','PULSE_NPN_BASE',90)
    p.resistor('R65','10k',277,108,'PULSE_NPN_BASE','GND')
    p.component('74xGxx:74LVC1G08','U8','74LVC1G08 / pulse interlock',343,75,{'1':'VPP_EN','2':'RESET','3':'GND','4':'VPP_DRIVE','5':'+5V'},'Package_TO_SOT_SMD:SOT-23-5')
    p.cap('C21','100nF',370,126,'+5V')
    p.resistor('R34','10k VPP_EN pull-down',321,130,'VPP_EN','GND')
    p.resistor('R35','120k / 1%',83,196,'VPP_SW','VPP_SENSE')
    p.resistor('R36','22k / 1%',83,234,'VPP_SENSE','GND')
    p.cap('C22','10nF',129,235,'VPP_SENSE')
    p.component('Diode:BAT54S','D30','ADC6 BAT54S clamp',166,239,{'1':'GND','2':'+5V','3':'VPP_SENSE'},'Package_TO_SOT_SMD:SOT-23')
    p.resistor('R37','10k bleed',198,198,'VPP_SW','GND')
    p.resistor('R38','5.1k',269,186,'VPP_SW','VPP_LED_MID')
    p.resistor('R39','5.1k',269,225,'VPP_LED_MID','VPP_LED_A')
    p.component('Device:LED','D6','VPP ACTIVE RED',349,230,{'1':'GND','2':'VPP_LED_A'},'LED_SMD:LED_0603_1608Metric')
    p.text('Arm Q3 while relay remains READ; settle HV_ARM; then pulse Q7 using PD2.\nPreflight measures actual switched VPP with socket isolated. Remove VPP before moving relay.\nPNP emitter = HV_ARM, collector = VPP_SW. VPP has a load-dependent VCE drop: calibrate under 30mA load.\nNo added VPP_SW capacitor. R37 returns pin22 LOW for byte verify. ADC filter is behind 120k.\nCommissioning requires measured <=50ns pin22 rise time and <14V overshoot for NM27C512.\nWRITE is locked in the default firmware build until the assembled pulse stage has passed these checks.',20,275,1.1)

def relay_interface(p):
    p.text('K1 DPDT / break-before-make / default READ position',20,28,1.6)
    p.component('Relay:G5V-2','K1','G5V-2-DC5 (100mA coil)',85,76,{'1':'+5V','16':'RELAY_COIL_LOW','4':'TARGET_VCC','6':'+5V','8':'+6V25_PROG',
        '13':'SOCKET_OE_VPP','11':'TARGET_OE#','9':'VPP_SW'},'Relay_THT:Relay_DPDT_Omron_G5V-2',90)
    p.power('TARGET_VCC',113,44,True)
    p.component('Transistor_BJT:MMBT3904','Q5','MMBT3904',174,73,{'1':'RELAY_BASE','2':'GND','3':'RELAY_COIL_LOW'},'Package_TO_SOT_SMD:SOT-23')
    p.resistor('R42','470R relay drive',159,118,'PROG_MODE','RELAY_BASE',90)
    p.resistor('R43','10k',212,106,'RELAY_BASE','GND')
    p.resistor('R44','10k',212,145,'PROG_MODE','GND')
    p.component('Device:D','D8','1N4148WS flyback',137,155,{'1':'+5V','2':'RELAY_COIL_LOW'},'Diode_SMD:D_SOD-323')
    p.text('Coil 1/16. Pole A: COM4, NC6, NO8. Pole B: COM13, NC11, NO9.\nDe-energized: target VCC = +5V, socket OE/VPP = MCU OE#.\nEnergized: target VCC = +6.25V, socket OE/VPP = VPP_SW.\n470R base resistor supplies ~9mA: the standard G5V-2 coil draws 100mA.\nThe suggested 10k base drive would not guarantee saturation.',20,179,1.25)
    p.resistor('R45','10k / 1%',273,52,'TARGET_VCC','TARGET_VCC_SENSE')
    p.resistor('R46','10k / 1%',273,91,'TARGET_VCC_SENSE','GND')
    p.cap('C25','10nF',316,93,'TARGET_VCC_SENSE')
    p.component('Diode:BAT54S','D31','ADC7 BAT54S clamp',364,103,{'1':'GND','2':'+5V','3':'TARGET_VCC_SENSE'},'Package_TO_SOT_SMD:SOT-23')
    p.text('ADC7: half of target VCC.\n5.00V -> 2.50V; 6.25V -> 3.125V.',248,128,1.25)
    p.component('Connector_Generic:Conn_02x20_Odd_Even','J5','J_TARGET / 40-pin',328,220,TARGET_HEADER,'Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical')
    p.text('J_TARGET: odd pins on left; even pins on right.\n1-20 A0-A19; 21-28 D0-D7 (protected target side);\n29 CE/PGM#, 30 OE#, 31 PGM#, 32 VPP_SW;\n33 TARGET_VCC, 34 +5V, 35 +6.25V, 36 GND;\n37 PROG_MODE, 38 GND, 39 RESET, 40 GND.\nNEVER wire VPP_SW to address/data/control GPIO.\nAdapters requiring VPP=VCC in READ need physical switching.\nKeep onboard U6 empty when an adapter is installed.',20,233,1.25)
    # Test points grouped on a separate schematic page avoid crowded labels.

TARGET_HEADER={str(i+1):'A'+str(i) for i in range(20)}
TARGET_HEADER.update({str(i+21):'TARGET_D'+str(i) for i in range(8)})
TARGET_HEADER.update(dict(zip(map(str,range(29,41)),['TARGET_CE_PGM#','TARGET_OE#','TARGET_PGM#','VPP_SW','TARGET_VCC','+5V','+6V25_PROG','GND','PROG_MODE','GND','RESET','GND'])))

def testpoints(p):
    names=['+5V','GND','+6V25_PROG','VPP_IN','VPP_SW','RESET','ADDR_SCK','ADDR_LATCH','TARGET_CE_PGM#','TARGET_OE#','TARGET_PGM#','UART_RX','UART_TX']
    values=['TP_5V','TP_GND','TP_6V25','TP_VPP_IN','TP_VPP_SW','TP_RESET','TP_ADDR_SCK','TP_ADDR_LATCH','TP_CE','TP_OE','TP_PGM','TP_RX','TP_TX']
    for i,(net,value) in enumerate(zip(names,values)):
        p.component('Connector:TestPoint','TP'+str(i+1),value,48+(i%4)*95,55+(i//4)*37,{'1':net},TP)
    p.text('Safety sequence / required bench checks',20,198,1.8)
    p.text('1. USB supplies all 5V logic. External supply is regulated, current-limited and shares GND.\n2. Power-up / RESET / ISP / DTR reset: CE and OE HIGH, relay READ, VPP disabled.\n3. Preflight VPP measurement is made with relay in READ; onboard socket is isolated from VPP.\n4. Verify target VCC before enabling VPP. Verify VPP voltage before every programming pulse.\n5. Remove VPP and confirm VPP_SW <0.40V before verifying or releasing PROG_MODE.\n6. Watchdog / timeout / invalid command returns to safe mode.\n7. NEVER insert/remove an EPROM with USB or VPP connected. One populated target only.\n8. Before commissioning WRITE, scope pin 22 for overshoot (<14V) and rise time (<=50ns).\n9. This revision is a schematic/prototype basis; ERC cannot certify switching waveforms or PCB layout.',20,229,1.35)

def reference_sheet(p, kind):
    p.text('REFERENCE ONLY - logical mapping for future adapter PCBs, not additional live targets',20,28,1.6)
    if kind==24:
        addr={str(n):'A'+str(8-n) for n in range(1,9)};addr.update({'19':'A10','22':'A9','23':'A8'})
        data=dict(zip(map(str,[9,10,11,13,14,15,16,17]),['D'+str(i) for i in range(8)]))
        rows={**addr,**data,'12':'GND','18':'CE/PGM (READ low)','20':'OE#','21':'VPP (READ +5V)','24':'TARGET_VCC'}
        for i in range(1,25): p.text(f'Pin {i:02}: {rows[str(i)]}',30+(0 if i<=12 else 110),50+((i-1)%12)*7,1.4)
        p.text('Intel 2716: VPP pin21 must be +5V for READ. NOT VPP_SW=0V.\nRead adapter ties pin21 to TARGET_VCC; pin18 = CE, pin20 = OE.\nFuture WRITE needs a relay/jumper to select pin21 between +5V and VPP_SW;\nseparate exact algorithm and polarity are required. Do not copy NM27C512 WRITE.\nKR573RF5 profile is quarantined pending a traceable original device datasheet.\nIts manufacturer pinout/algorithm must be checked before populating an adapter.\n2732 differs: pin21 = A11 and pin20 = OE/VPP (requires HV isolation).',20,163,1.45)
        p.text('Source: Intel 2716 datasheet, Intel 1980, pin configuration / mode selection.\nSee docs/sources.md for the source URL. No unverified KR573RF5 wiring is fabricated.',20,245,1.15)
    elif kind==28:
        fixed={k:v.replace('TARGET_D','D') for k,v in EPROM_NETS.items() if k not in ('1','20','22','26','27')}
        variants={'1':'64/128/256: VPP; 512: A15','20':'64/128: CE#; 256/512: CE/PGM#','22':'64/128/256: OE#; 512: OE/VPP',
                  '26':'64: NC; 128/256/512: A13','27':'64/128: PGM#; 256/512: A14'}
        for i in range(1,29): p.text(f'Pin {i:02}: {variants.get(str(i),fixed.get(str(i),""))}',23+(0 if i<=14 else 190),48+((i-1)%14)*7,1.3)
        p.text('2764/27128: pin27 is PGM#, NOT A14. 27256: pin27 is A14.\nDo not route a 595 output onto a VPP pin. Use keyed jumpers or a device-specific adapter.\nVPP on pin1 needs READ +5V selection, separate from the onboard NM27C512 relay.\nRead-only adapters may tie VPP and unused PGM# HIGH. WRITE remains disabled for these profiles.\nSources: National NM27C512 and Intel 2764 / 27128A / 27256 original datasheets.',20,170,1.4)
    else:
        rows={'1':'010/020/040: VPP; 080: A19','2':'A16','3':'A15','4':'A12',**{str(n):'A'+str(12-n) for n in range(5,13)},
              **dict(zip(map(str,[13,14,15,17,18,19,20,21]),['D'+str(i) for i in range(8)])), '16':'GND','22':'CE / CE-PGM# (family dependent)',
              '23':'A10','24':'010/020/040: OE#; 080: OE/VPP','25':'A11','26':'A9','27':'A8','28':'A13','29':'A14',
              '30':'010: NC; 020/040/080: A17','31':'010/020: PGM#; 040/080: A18','32':'TARGET_VCC'}
        for i in range(1,33): p.text(f'Pin {i:02}: {rows[str(i)]}',23+(0 if i<=16 else 190),48+((i-1)%16)*6.5,1.3)
        p.text('National 27C010/020/040/080 package comparison is the source for these pin roles.\nUse a device-specific adapter; role changes require keyed selection or HV-rated switching.\nPin1 must never receive VPP when it is A19. Pin24 changes from OE to OE/VPP on 080.\n27C080 cannot use a generic 32-pin VPP-pin1 adapter. Program profiles remain disabled.\nRead VPP pins require +5V, not an unpowered VPP_SW. See device_profiles.json for verified status.',20,173,1.4)

def project(folder, stage=True):
    folder.mkdir(parents=True,exist_ok=True)
    root_id=uid(folder.name+'/root')
    p=Page(NAME+'.kicad_sch','NM27C512 Dumper / '+('Stage 2 - multi-EPROM architecture' if stage else 'Original read-only architecture'),folder,root_id)
    specs=[('controller.kicad_sch','USB / CH340C / ATmega / clock / reset / ISP / UART',controller),
           ('address_target.kicad_sch','Address generator and NM27C512 direct socket',targets)]
    if stage:
        specs += [('data_status.kicad_sch','Data protection and status LEDs',protection),
                  ('ttl_bus.kicad_sch','TTL-compatible bidirectional data bus',ttl_bus),
                  ('programming_power.kicad_sch','External VPP / high-side switch / 6.25 V regulator',high_voltage),
                  ('programming_pulse.kicad_sch','Fast VPP pulse switch / indicator / ADC monitor',pulse_switch),
                  ('target_interface.kicad_sch','Default-read relay / target connector / monitoring',relay_interface),
                  ('testpoints_safety.kicad_sch','Test points and safety sequence',testpoints),
                  ('adapter_2716_KR573RF5.kicad_sch','2716 / KR573RF5 adapter reference',lambda q:reference_sheet(q,24)),
                  ('adapter_28pin_27xx.kicad_sch','28-pin EPROM adapter reference',lambda q:reference_sheet(q,28)),
                  ('adapter_32pin_JEDEC.kicad_sch','32-pin JEDEC adapter reference',lambda q:reference_sheet(q,32))]
    for i,(file,title,fn) in enumerate(specs):
        child=Page(file,title,folder,root_id,i+2)
        if fn in (controller,targets): fn(child,stage)
        else: fn(child)
        child.save()
        x=25+(i%3)*125;y=42+(i//3)*49
        p.child(child,title,x,y,110,24)
        p.text('Open sheet '+str(i+2),x+5,y+15,1.3)
    if stage:
        p.text('5 V LOGIC / EXTERNAL REGULATED VPP ONLY / DEFAULT READ ON RESET',25,254,1.8)
        p.text('The original 5V-only dumper is preserved in baseline_readonly/. This project adds programming-voltage routing.\nNo onboard VPP boost. Exact manufacturer profiles govern voltages, pin roles and algorithm.\nHardware bring-up and pulse-waveform validation are required before commissioning WRITE. One target at a time.',25,271,1.15)
    else:
        p.text('NM27C512 READ-ONLY DUMPER\n5 V ONLY\nNO VPP PROGRAMMING VOLTAGE',25,165,2.3)
    p.save()
    pro={'meta':{'filename':NAME+'.kicad_pro','version':1},'board':{},'boards':[],
         'cvpcb':{},'erc':{'erc_exclusions':[],'meta':{'version':0},'rule_severities':{}},
         'libraries':{'pinned_footprint_libs':[],'pinned_symbol_libs':[]},'net_settings':{'classes':[{'name':'Default','clearance':0.2,'track_width':0.25,'via_diameter':0.6,'via_drill':0.3,'microvia_diameter':0.3,'microvia_drill':0.1,'diff_pair_width':0.2,'diff_pair_gap':0.25,'diff_pair_via_gap':0.25}],'meta':{'version':3}},
         'pcbnew':{},'schematic':{'drawing':{'default_line_thickness':6,'default_text_size':50},'meta':{'version':1}},'text_variables':{}}
    (folder/(NAME+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n',encoding='utf8')
    (folder/'ProjectSymbols.kicad_sym').write_text((ROOT/'ProjectSymbols.kicad_sym').read_text(encoding='utf8'),encoding='utf8')
    (folder/'sym-lib-table').write_text('(sym_lib_table\n (version 7)\n (lib (name "ProjectSymbols") (type "KiCad") (uri "${KIPRJMOD}/ProjectSymbols.kicad_sym") (options "") (descr "WCH-corrected CH340C pin 8"))\n)\n',encoding='utf8')
    if not stage:
        (folder/'fp-lib-table').write_text('(fp_lib_table\n (version 7)\n)\n',encoding='utf8')

if __name__=='__main__':
    ch=standard('Interface_USB:CH340C')
    ch[1]='CH340C_WCH'
    for sub in children(ch,'symbol'):
        sub[1]=sub[1].replace('CH340C_','CH340C_WCH_')
        for pin in children(sub,'pin'):
            if str(one(pin,'number')[1])=='8':
                pin[1]=A('output'); one(pin,'name')[1]='~{OUT}/~{DTR2}'
    for prop in children(ch,'property'):
        if prop[1]=='Value': prop[2]='CH340C_WCH'
        if prop[1]=='Datasheet': prop[2]='https://cdn.sparkfun.com/assets/5/0/a/8/5/CH340DS1.PDF'
    retained = [s for s in children(parse((ROOT/'ProjectSymbols.kicad_sym').read_text(encoding='utf8')), 'symbol') if s[1]=='RGB_CA_DualMount']
    (ROOT/'ProjectSymbols.kicad_sym').write_text(dump(N('kicad_symbol_lib',N('version',20241209),N('generator',A('kicad_symbol_editor')),ch,*retained))+'\n',encoding='utf8')
    project(ROOT,True)
    main_bom=copy.deepcopy(BOM)
    BOM.clear()
    project(ROOT/'baseline_readonly',False)
    # Separate power indicator for the preserved baseline.
    (ROOT/'validation'/'bom.json').write_text(json.dumps(main_bom,indent=2)+'\n',encoding='utf8')
    (ROOT/'validation'/'baseline_bom.json').write_text(json.dumps(BOM,indent=2)+'\n',encoding='utf8')
    (ROOT/'validation'/'target_header.json').write_text(json.dumps(TARGET_HEADER,indent=2)+'\n',encoding='utf8')
    print(f'Generated Stage 2 ({len(main_bom)} components) and read-only baseline ({len(BOM)} components).')
