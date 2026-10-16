"""Build the separate Lunar Writer project from the saved Stage 2 schematic.

Run with KiCad's Python: schema / place / import / finish / audit.
The root Stage 2 and the user's routed Dumper are never overwritten here.
"""
from pathlib import Path
import copy, csv, hashlib, json, math, re, shutil, sys, uuid
import xml.etree.ElementTree as ET
import pcbnew as k
import generate_schematic as g
from kicad_sexpr import parse, dump, one, children, node as N, Atom as A

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Lunar-Writer'
NAME='Lunar_Writer'
VAL=OUT/'validation'
ORIGIN=(50,50)
SIZE=(150,105)

def write(path,tree):
    path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(x) for x in tree[1:])+'\n)\n',encoding='utf8')

def walk(tree):
    if isinstance(tree,list):
        yield tree
        for item in tree: yield from walk(item)

def property_of(sym,key):
    return next(p for p in children(sym,'property') if p[1]==key)

def schema():
    assert not (OUT/(NAME+'.kicad_pcb')).exists() or '--refresh-schema' in sys.argv, 'Do not regenerate an already routed Writer'
    OUT.mkdir(exist_ok=True); VAL.mkdir(exist_ok=True)
    shutil.copytree(ROOT/'ProjectFootprints.pretty',OUT/'ProjectFootprints.pretty',dirs_exist_ok=True)
    shutil.copytree(ROOT/'3DModels',OUT/'3DModels',dirs_exist_ok=True)
    for name in ['fp-lib-table','sym-lib-table','ProjectSymbols.kicad_sym']:
        shutil.copy2(ROOT/name,OUT/name)
    library=parse((OUT/'ProjectSymbols.kicad_sym').read_text(encoding='utf8'))
    symbol=N('symbol','LM2577T_ADJ',N('pin_names',N('offset',1.016)),N('in_bom',A('yes')),N('on_board',A('yes')))
    for key,value in [('Reference','U'),('Value','LM2577T_ADJ'),('Footprint','ProjectFootprints:LM2577T_TO2205'),('Datasheet','https://www.ti.com/lit/ds/symlink/lm2577.pdf')]:
        symbol.append(N('property',key,value,N('at',0,12.7,0),g.effects(1.27,hide=key in ['Footprint','Datasheet'])))
    body=N('symbol','LM2577T_ADJ_0_1',N('rectangle',N('start',-10.16,10.16),N('end',10.16,-10.16),N('stroke',N('width',.254),N('type',A('default'))),N('fill',N('type',A('background')))))
    pinunit=N('symbol','LM2577T_ADJ_1_1')
    for num,name,kind,x,y,angle in [('5','VIN','power_in',-15.24,7.62,0),('1','COMP','passive',-15.24,0,0),('2','FB','input',-15.24,-7.62,0),('4','SW','open_collector',15.24,7.62,180),('3','GND','power_in',0,-15.24,90)]:
        pinunit.append(N('pin',A(kind),A('line'),N('at',x,y,angle),N('length',5.08),N('name',name,g.effects(1.27)),N('number',num,g.effects(1.27))))
    symbol.extend([body,pinunit]); library.append(symbol); write(OUT/'ProjectSymbols.kicad_sym',library)
    g.LIBS['ProjectSymbols']={s[1]:s for s in children(library,'symbol')}
    g.NAME=NAME
    ptc_footprint()
    to220=k.FootprintLoad(str(g.KICAD/'footprints/Package_TO_SOT_THT.pretty'),'TO-220-5_Vertical')
    to220.SetFPIDAsString('ProjectFootprints:LM2577T_TO2205'); to220.SetValue('LM2577T_TO2205')
    for pad in to220.Pads(): pad.SetSize(k.VECTOR2I(k.FromMM(1.5),k.FromMM(2.3)))
    k.FootprintSave(str(OUT/'ProjectFootprints.pretty'),to220)
    documents={p.name:parse(p.read_text(encoding='utf8')) for p in ROOT.glob('*.kicad_sch')}
    root=documents.pop('NM27C512_Dumper.kicad_sch')
    root_uuid=one(root,'uuid')[1]
    def rename_metadata(tree):
        for n in walk(tree):
            if n[0]=='project' and len(n)>1 and n[1]=='NM27C512_Dumper': n[1]=NAME
        tb=one(tree,'title_block')
        one(tb,'title')[1]='Lunar Writer - Rev. 1'
        one(tb,'date')[1]='2026-10-12'; one(tb,'rev')[1]='1'
        one(tb,'comment')[2]='USB 5V logic / separate 12-24V DC input / regulated VPP / default READ'
    for file,tree in documents.items():
        rename_metadata(tree)
        if file=='programming_power.kicad_sch':
            # J4 is a supply input, not an externally adjusted VPP input now.
            for n in walk(tree):
                if n[0]=='global_label' and n[1]=='VPP_IN' and float(one(n,'at')[1])<85 and float(one(n,'at')[2])<150: n[1]='VIN_RAW'
            for s in children(tree,'symbol'):
                ref=property_of(s,'Reference')[2]
                if ref=='J4': property_of(s,'Value')[2]='12-24V DC IN (+ / GND)'
                if ref=='Q4': property_of(s,'Value')[2]='MMBT5551 / 160V NPN'
                if ref=='R31':
                    property_of(s,'Value')[2]='2.2k / 0.5W'; property_of(s,'Footprint')[2]='Resistor_SMD:R_2010_5025Metric'
            # Change only U7 input, its bypass and reverse-protection labels.
            for n in children(tree,'global_label'):
                at=one(n,'at'); x,y=float(at[1]),float(at[2])
                if n[1]=='VPP_IN' and y>175 and x<95: n[1]='VIN_PROTECTED'
            for t in children(tree,'text'):
                if 'External regulated supply' in t[1]: t[1]='J4: 12...24 V DC input. Boost / VPP regulation on the supply sheet. USB powers logic only.'
                if 'TO-220 tab is OUTPUT' in t[1]: t[1]='Set TP_6V25 to 6.250V at load. U7 runs from VIN_PROTECTED.\nU7 tab is OUTPUT; fit an insulated heatsink. Worst nominal loss at 24V/100mA: ~1.8W.'
                t[1]=t[1].replace('SOURCE/VPP_IN','SOURCE/regulated VPP_IN')
        if file=='programming_pulse.kicad_sch':
            for s in children(tree,'symbol'):
                ref=property_of(s,'Reference')[2]
                if ref=='R63':
                    property_of(s,'Value')[2]='2.2k / 0.5W'; property_of(s,'Footprint')[2]='Resistor_SMD:R_2010_5025Metric'
                if ref=='R37':
                    property_of(s,'Value')[2]='10k bleed / 0.25W'; property_of(s,'Footprint')[2]='Resistor_SMD:R_1206_3216Metric'
        if file=='data_status.kicad_sch':
            for t in children(tree,'text'):
                t[1]=t[1].replace('Green: READ; Red: WRITE; Amber: IDLE; Blue: ERROR.','Green blink 500ms: READ; Purple blink 500ms: WRITE; Amber: READY; Red: disconnected.')
        write(OUT/file,tree)
    rename_metadata(root)
    one(root,'paper')[1]='A2'
    for t in children(root,'text'):
        if float(one(t,'at')[2])>=250: one(t,'at')[2]=float(one(t,'at')[2])+70
        if 'EXTERNAL REGULATED VPP ONLY' in t[1]: t[1]='LUNAR WRITER / USB 5V LOGIC / SEPARATE 12-24V INPUT / RESET = READ'
        if 'No onboard VPP boost' in t[1]: t[1]='Boost generates ~30V from 12-24V input. VPP rails are adjusted separately and selected by JP1.\nDirect NM27C512 socket uses 12.75V VPP / 6.25V VCC. Other EPROMs require verified profiles and adapters.\nDefault firmware locks WRITE until measured commissioning. One target at a time.'
        if 'NM27C512 Dumper / Stage 2' in t[1]: t[1]='Lunar Writer / parallel EPROM reader-programmer'
    g.COUNTERS[OUT.name]=1000
    page=g.Page('writer_supply.kicad_sch','Lunar Writer: protected 12-24V supply, boost and VPP rails',OUT,root_uuid,13)
    page.text('External power is never connected to USB VBUS / +5V. J4 is on the power sheet.',20,28,1.5)
    page.component('Device:Polyfuse','F2','MF-R090 / 0.9A hold / 60V',40,58,{'1':'VIN_RAW','2':'VIN_FUSED'},'ProjectFootprints:PTC_MF_R090')
    page.component('Device:D_Schottky','D40','SS36 / 3A / 60V reverse-polarity',98,58,{'1':'VIN_PROTECTED','2':'VIN_FUSED'},'Diode_SMD:D_SMA',90)
    page.component('Device:D_Zener','D41','SMBJ24A / TVS',142,75,{'1':'VIN_PROTECTED','2':'GND'},'Diode_SMD:D_SMB')
    page.cap('C30','220uF / 50V low ESR',40,116,'VIN_PROTECTED','Capacitor_THT:CP_Radial_D10.0mm_P5.00mm')
    page.cap('C31','100nF / 50V X7R',80,116,'VIN_PROTECTED','Capacitor_SMD:C_0805_2012Metric')
    page.component('ProjectSymbols:LM2577T_ADJ','U11','LM2577T-ADJ / 40V input, 60V switch',245,70,{'1':'BOOST_COMP','2':'BOOST_FB','3':'GND','4':'BOOST_SW','5':'VIN_PROTECTED'},'ProjectFootprints:LM2577T_TO2205')
    page.component('Device:L','L1','100uH / SRR1210A-101M / Isat 2.2A',244,35,{'1':'VIN_PROTECTED','2':'BOOST_SW'},'Inductor_SMD:L_Bourns_SRR1210A',90)
    page.component('Device:D_Schottky','D42','SS36 / 3A / 60V boost rectifier',321,53,{'1':'BOOST_30V','2':'BOOST_SW'},'Diode_SMD:D_SMA',90)
    page.cap('C32','680uF / 50V low ESR',374,61,'BOOST_30V','Capacitor_THT:CP_Radial_D12.5mm_P5.00mm')
    page.cap('C33','100nF / 50V X7R',374,113,'BOOST_30V','Capacitor_SMD:C_0805_2012Metric')
    page.resistor('R70','47k / 1%',325,96,'BOOST_30V','BOOST_FB')
    page.resistor('R71','2k / 1%',325,129,'BOOST_FB','GND')
    page.resistor('R72','470R compensation',204,116,'BOOST_COMP','BOOST_COMP_RC')
    page.cap('C34','47uF / 16V compensation',204,151,'BOOST_COMP_RC','Capacitor_THT:CP_Radial_D5.0mm_P2.00mm')
    page.text('Vboost = 1.23*(1+47k/2k) = 30.135V. L=100uH; Rc=470R; Cc=47uF; Cout=680uF.\nDesign load 100mA on 30V rail. Use 50V bulk capacitors, Cout ESR <=0.2ohm / ripple >=0.2A.\nValidate startup and load-step response; calculated compensation is not a measured stability test.',20,173,1.05)
    for number,x,bottom,trim,net in [(12,57,'1k','200R','VPP_12V75'),(13,208,'1.8k','1k','VPP_HIGH')]:
        base=73 if number==12 else 75
        page.component('Regulator_Linear:LM317_TO-220',f'U{number}','LM317T / '+('12.75V' if number==12 else '21...25V')+' / heatsink',x,218,{'1':f'VPP_ADJ{number}','2':net,'3':'BOOST_30V'},'Package_TO_SOT_THT:TO-220-3_Vertical')
        page.resistor(f'R{base}','120R / 1%',x,250,net,f'VPP_ADJ{number}')
        page.resistor(f'R{base+1}',bottom+' / 1%',x+42,239,f'VPP_ADJ{number}',f'VPP_TRIM{number}')
        page.component('Device:R_Potentiometer','RV2' if number==12 else 'RV3',trim+' multi-turn',x+90,252,{'1':f'VPP_TRIM{number}','2':'GND','3':'GND'},'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical')
        page.cap('C35' if number==12 else 'C36','1uF / 50V X7R',x+43,283,net,'Capacitor_SMD:C_1206_3216Metric')
        page.component('Device:D','D43' if number==12 else 'D44','M7 / 1N4007-SMD / 1A 1000V',x,283,{'1':'BOOST_30V','2':net},'Diode_SMD:D_SMA',90)
    page.component('Connector_Generic:Conn_01x03','JP1','VPP SELECT: 12.75 / common / HIGH',357,224,{'1':'VPP_12V75','2':'VPP_IN','3':'VPP_HIGH'},'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
    page.resistor('R77','100k bleed',356,268,'VPP_IN','GND')
    for ref,net,x,y in [('TP14','VIN_PROTECTED',40,148),('TP15','BOOST_30V',374,145),('TP16','VPP_12V75',142,283),('TP17','VPP_HIGH',293,283)]:
        page.component('Connector:TestPoint',ref,net,x,y,{'1':net},g.TP)
    page.text('JP1: fit ONE shunt only; 1-2 = NM27C512 12.75V, 2-3 = adjusted HIGH for a verified adapter.\nNo shunt = VPP disconnected / discharged. Do not change JP1 with either supply powered.\nRV2: adjust actual VPP_SW to 12.75V under load. RV3: adjust HIGH to the exact device voltage.\nU12/U13 tabs are OUTPUTS: separate insulated heatsinks. Programming still defaults OFF on RESET.',20,302,1.05)
    for net,x,y in [('VIN_PROTECTED',70,328),('BOOST_30V',125,328),('VPP_IN',180,328)]: page.power(net,x,y,True)
    page.save()
    supplied=parse((OUT/'writer_supply.kicad_sch').read_text(encoding='utf8')); rename_metadata(supplied)
    one(supplied,'paper')[1]='A2'; write(OUT/'writer_supply.kicad_sch',supplied)
    holder=g.Page(NAME+'.kicad_sch','',OUT,root_uuid)
    holder.child(page,'12-24V protection / boost / regulated VPP',275,235,110,24)
    root.extend(holder.items[1:]); write(OUT/(NAME+'.kicad_sch'),root)
    pro=json.loads((ROOT/'NM27C512_Dumper.kicad_pro').read_text(encoding='utf8'))
    pro['meta']['filename']=NAME+'.kicad_pro'
    pro['board']['design_settings']['drc_exclusions']=[]
    pro['erc']['erc_exclusions']=[]
    nc={'name':'Default','clearance':.2,'track_width':.25,'via_diameter':.8,'via_drill':.4,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.2,'diff_pair_via_gap':.25}
    hv={**nc,'name':'HV','clearance':.2,'track_width':.6,'via_diameter':1.2,'via_drill':.6}
    power={**nc,'name':'Power','track_width':.6,'via_diameter':1.2,'via_drill':.6}
    pro['net_settings']={'classes':[nc,hv,power],'meta':{'version':4},'netclass_assignments':{},'netclass_patterns':[{'netclass':'HV','pattern':p} for p in ['VIN_*','BOOST_30V','BOOST_SW','VPP_IN','VPP_12V75','VPP_HIGH','HV_ARM','VPP_SW','VPP_GATE','VPP_PULLDOWN','PULSE_PNP_BASE','PULSE_PULLDOWN','SOCKET_OE_VPP']]+[{'netclass':'Power','pattern':p} for p in ['+5V','+6V25_PROG','TARGET_VCC','USB_VBUS','GND']]}
    (OUT/(NAME+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n',encoding='utf8')
    print('Created Writer schematic; export XML netlist next, then run place.')

def ptc_footprint():
    # MF-R090 maximum width 11.7mm, thickness 3.1mm, pitch 5.1 +/-0.7mm.
    fp=k.FOOTPRINT(None); fp.SetFPIDAsString('ProjectFootprints:PTC_MF_R090'); fp.SetReference('REF**'); fp.SetValue('PTC_MF_R090'); fp.SetAttributes(k.FP_THROUGH_HOLE)
    for num,x in [('1',0),('2',5.1)]:
        pad=k.PAD(fp); pad.SetNumber(num); pad.SetShape(k.PAD_SHAPE_CIRCLE if num=='2' else k.PAD_SHAPE_RECT)
        layers=k.LSET.AllCuMask(); layers.AddLayer(k.F_Mask); layers.AddLayer(k.B_Mask)
        pad.SetAttribute(k.PAD_ATTRIB_PTH); pad.SetSize(k.VECTOR2I(k.FromMM(1.8),k.FromMM(1.8))); pad.SetDrillSize(k.VECTOR2I(k.FromMM(.9),k.FromMM(.9))); pad.SetLayerSet(layers); pad.SetPosition(k.VECTOR2I(k.FromMM(x),0)); fp.Add(pad)
    for layer,w in [(k.F_Fab,.1),(k.F_SilkS,.12),(k.F_CrtYd,.05)]:
        margin=.25 if layer==k.F_CrtYd else 0
        shape=k.PCB_SHAPE(fp); shape.SetShape(k.SHAPE_T_RECT); shape.SetLayer(layer); shape.SetWidth(k.FromMM(w)); shape.SetStart(k.VECTOR2I(k.FromMM(-3.3-margin),k.FromMM(-1.55-margin))); shape.SetEnd(k.VECTOR2I(k.FromMM(8.4+margin),k.FromMM(1.55+margin))); fp.Add(shape)
    k.FootprintSave(str(OUT/'ProjectFootprints.pretty'),fp)

def manifest():
    tree=ET.parse(VAL/'netlist.xml')
    root_uuid=one(parse((OUT/(NAME+'.kicad_sch')).read_text(encoding='utf8')),'uuid')[1]
    comps={c.attrib['ref']:{'ref':c.attrib['ref'],'value':c.findtext('value'),'footprint':c.findtext('footprint'),'datasheet':c.findtext("fields/field[@name='Datasheet']",''),'path':'/'+root_uuid+'/'+c.find('sheetpath').attrib['tstamps'].strip('/')+'/'+c.findtext('tstamps'),'nets':{}} for c in tree.findall('components/comp') if c.findtext('footprint')}
    for net in tree.findall('nets/net'):
        for node in net.findall('node'):
            ref=node.attrib['ref']
            if ref in comps: comps[ref]['nets'][node.attrib['pin']]=net.attrib['name']
    (VAL/'manifest.json').write_text(json.dumps(comps,indent=2),encoding='utf8')
    return comps

def pt(x,y): return k.VECTOR2I(k.FromMM(ORIGIN[0]+x),k.FromMM(ORIGIN[1]+y))
def text(b,s,x,y,size=1,layer=k.F_SilkS):
    t=k.PCB_TEXT(b); t.SetText(s); t.SetLayer(layer); t.SetPosition(pt(x,y)); t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size))); t.SetTextThickness(k.FromMM(.12)); b.Add(t); return t

def place():
    assert not (OUT/(NAME+'.kicad_pcb')).exists() or '--overwrite-unrouted' in sys.argv, 'Existing Writer PCB is protected; edit it in KiCad instead of regenerating placement.'
    comps=manifest(); source=k.LoadBoard(str(ROOT/'NM27C512_Dumper.kicad_pcb'))
    old={f.GetReference():f for f in source.GetFootprints()}
    b=k.BOARD(); b.SetFileName(str(OUT/(NAME+'.kicad_pcb')))
    names={n for c in comps.values() for n in c['nets'].values()}
    nets={n:k.NETINFO_ITEM(b,n) for n in names}
    for n in nets.values(): b.Add(n)
    ds=b.GetDesignSettings(); ds.m_MinClearance=k.FromMM(.15); ds.m_TrackMinWidth=k.FromMM(.2); ds.m_ViasMinAnnularWidth=k.FromMM(.1); ds.m_ViasMinSize=k.FromMM(.8); ds.m_MinThroughDrill=k.FromMM(.4)
    nc=ds.m_NetSettings.GetDefaultNetclass(); nc.SetClearance(k.FromMM(.2)); nc.SetTrackWidth(k.FromMM(.25)); nc.SetViaDiameter(k.FromMM(.8)); nc.SetViaDrill(k.FromMM(.4))
    positions={
        'J1':(3,31,-90),'J2':(19,32,0),'J3':(10,41,90),'J4':(8,93,0),
        'U5':(22,20,0),'U1':(46,24,0),'U2':(73,40,180),'U3':(73,20,180),'U4':(47,50,180),'U6':(100,11,0),
        'Y1':(43.62,34,0),'SW1':(30,41,0),'D3':(6,14,0),'D4':(6,22,0),'D2':(30,55,0),
        'Q1':(12,14,180),'Q2':(12,22,180),'R23':(16,14,90),'R24':(16,22,90),'R25':(6,17,90),'R26':(6,25,90),
        'F1':(9,29,90),'C1':(14,33,90),'C2':(28,14,0),'C3':(16,19,90),'R4':(32,20,90),'R5':(32,24,90),
        'C4':(39,22,90),'C5':(39,26,90),'C6':(53,24,90),'C10':(53,20,90),'C11':(43,39,0),'C12':(49,39,0),
        'R1':(36,35,90),'C13':(28,29,0),'D9':(34,38,0),'R7':(39,44,90),'R2':(119,31,90),'R3':(119,27,90),'R8':(124,29,90),
        'C7':(68,45,90),'C8':(68,25,90),'C9':(119,19,90),'C14':(119,14,90),'C15':(123,14,90),
        'R20':(27,61,90),'R21':(30,61,90),'R22':(33,61,90),
        'U9':(85,57,180),'C26':(77,65,90),
        'J5':(140,15,0),'K1':(124,74,0),'Q5':(126,63,0),'D8':(129,68,90),'R42':(121,64,90),'R43':(127,59,0),'R44':(123,59,0),
        'U8':(105,53,0),'C21':(105,49,0),'R34':(100,50,0),'Q6':(108,58,0),'Q7':(114,58,0),
        'R64':(104,58,90),'R65':(108,62,0),'R62':(115,63,90),'R63':(112,68,0),
        'D6':(117,73,0),'R38':(111,73,90),'R39':(114,73,90),'R37':(110,77,90),
        'U10':(93,51,0),'C27':(93,47,0),'R60':(89,47,0),'Q4':(95,58,0),'R32':(99,56,90),'R33':(95,62,0),
        'Q3':(97,76,0),'R30':(104,69,0),'R31':(101,63,0),'D5':(107,82,90),'C28':(98,80,0),'R61':(98,84,0),
        'R35':(57,43,90),'R36':(60,46,90),'C22':(63,46,90),'D30':(60,50,0),
        'R45':(54,30,90),'R46':(57,30,90),'C25':(57,34,0),'D31':(57,37,0),
        'U7':(81,80,0),'C23':(81,75,90),'C24':(89,84,90),'R40':(81,86,90),'R41':(85,86,90),'RV1':(94,93,0),'D7':(75,92,90),
        'F2':(9,84,0),'D40':(8,77,90),'D41':(16,76,90),'C20':(3,80,90),'C30':(22,95,0),'C31':(22,72,90),
        'U11':(20,68,0),'L1':(27,82,0),'D42':(37,68,0),'C32':(39,77,0),'C33':(40,86,90),
        'R70':(33,67,90),'R71':(32,71,90),'R72':(15,65,90),'C34':(19,58,0),
        'U12':(52,81,0),'U13':(65,81,0),'R73':(54,87,90),'R74':(58,90,90),'RV2':(60,97,0),'C35':(54,91,90),'D43':(49,94,90),
        'R75':(67,87,90),'R76':(71,90,90),'RV3':(73,99,0),'C36':(67,91,90),'D44':(73,69,0),
        'JP1':(105,89,0),'R77':(103,85,90),
    }
    # Two columns of protection around the eight data lines, close to the HCT bus.
    for i in range(8):
        positions['R'+str(10+i)]=(60,11+i*4.4,90)
        positions['D'+str(10+i)]=(65,11+i*4.4,0)
        positions['R'+str(50+i)]=(92,11+i*4.4,90)
        positions['D'+str(20+i)]=(87,11+i*4.4,180)
    tpnames=['+5V','GND','+6V25_PROG','VPP_IN','VPP_SW','RESET','ADDR_SCK','ADDR_LATCH','TARGET_CE_PGM#','TARGET_OE#','TARGET_PGM#','UART_RX','UART_TX']
    for i in range(13): positions['TP'+str(i+1)]=(8+i*7,5,0)
    positions.update({'TP14':(14,61,0),'TP15':(43,64,0),'TP16':(56,74,0),'TP17':(69,74,0)})
    assert set(comps)==set(positions), f'Missing/extra placement: {set(comps)^set(positions)}'
    for ref,c in comps.items():
        if ref in old and old[ref].GetFPID().GetUniStringLibId()==c['footprint']: fp=k.FOOTPRINT(old[ref])
        else:
            lib,name=c['footprint'].split(':'); fp=k.FootprintLoad(str(g.footprint_path(c['footprint'],OUT).parent),name); assert fp,c
        b.Add(fp); fp.SetFPIDAsString(c['footprint']); fp.SetReference(ref); fp.SetValue(c['value']); fp.SetPath(k.KIID_PATH(c['path']))
        x,y,angle=positions[ref]; fp.SetPosition(pt(x,y)); fp.SetOrientationDegrees(angle)
        for pad in fp.Pads():
            name=c['nets'].get(pad.GetNumber())
            if name: pad.SetNet(nets[name])
            else: pad.SetNetCode(0)
            # Local RGB THT geometry is retained from the project's approved dual footprint.
        fp.Value().SetVisible(False); label=fp.Reference(); label.SetVisible(not ref.startswith('TP')); label.SetLayer(k.F_SilkS); label.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T)); label.SetTextSize(k.VECTOR2I(k.FromMM(.85),k.FromMM(.85))); label.SetTextThickness(k.FromMM(.12)); label.SetPosition(pt(x,y-2.4))
        if ref in ['U1','U2','U3','U4','U5','U9']: label.SetPosition(pt(x,y-7.2 if ref!='U1' else y-6.4))
        if ref=='U6': label.SetPosition(pt(x+7.62,y-3))
        fp.SetField('Datasheet',c['datasheet'])
        if ref.startswith('TP'): fp.SetExcludedFromBOM(False); fp.SetExcludedFromPosFiles(False)
        if ref=='D2':
            for p in fp.Pads():
                if p.GetAttribute()==k.PAD_ATTRIB_PTH: p.SetSize(k.VECTOR2I(k.FromMM(1.11),k.FromMM(1.8))); p.SetLocalClearance(k.FromMM(.15))
        if ref=='U11':
            for p in fp.Pads(): p.SetSize(k.VECTOR2I(k.FromMM(1.5),k.FromMM(2.3)))
        if ref=='U5':
            name='unconnected-(U5-~{OUT}{slash}~{DTR2}-Pad8)'; net=k.NETINFO_ITEM(b,name); b.Add(net)
            next(p for p in fp.Pads() if p.GetNumber()=='8').SetNet(net)
    for i,(x,y) in enumerate([(4.5,9),(145.5,9),(4.5,102),(145.5,100.5)],1):
        fp=k.FootprintLoad(str(g.KICAD/'footprints/MountingHole.pretty'),'MountingHole_3.2mm_M3'); b.Add(fp); fp.SetReference('H'+str(i)); fp.SetValue('M3'); fp.SetPosition(pt(x,y)); fp.Reference().SetVisible(False); fp.Value().SetVisible(False); fp.SetBoardOnly(True)
    corners=[(0,0),(SIZE[0],0),SIZE,(0,SIZE[1]),(0,0)]
    for a,z in zip(corners,corners[1:]):
        s=k.PCB_SHAPE(b); s.SetLayer(k.Edge_Cuts); s.SetShape(k.SHAPE_T_SEGMENT); s.SetStart(pt(*a)); s.SetEnd(pt(*z)); s.SetWidth(k.FromMM(.05)); b.Add(s)
    for s,x,y,size in [('Lunar Writer',119,5,1.8),('Rev. 1 / IB-WorkShop / 2026',124,101,1),('USB',7,36,1),('AVR ISP',20,29,1),('RESET',33,49,1),('STATUS RGB - ONE ONLY',31,65,.85),('NM27C512 / PIN 1',108,47,1),('J4: +12...24V DC',20,99,1),('+',7,97,.9),('GND',12,97,.9),('VPP SELECT',110,97,.85),('EXTERNAL POWER / HV',28,46,1),('VPP',117,76,.8)]: text(b,s,x,y,size)
    # Keep a safe arming gate and no VPP output bulk capacitor, as in Stage 2.
    k.SaveBoard(str(OUT/(NAME+'.kicad_pcb')),b)
    print('Placed',len(comps),'electrical components on',SIZE,'mm board; run DRC before routing.')

def export():
    b=k.LoadBoard(str(OUT/(NAME+'.kicad_pcb')))
    assert k.ExportSpecctraDSN(b,str(VAL/'writer.dsn'))
    path=VAL/'writer.dsn'; dsn=path.read_text(encoding='utf8')
    block=re.search(r'    \(class kicad_default.*?\n    \)\n',dsn,re.S); assert block
    default=parse(block.group(0))
    hv={'VIN_RAW','VIN_FUSED','VIN_PROTECTED','BOOST_30V','BOOST_SW','VPP_12V75','VPP_HIGH','VPP_IN','HV_ARM','VPP_SW','SOCKET_OE_VPP'}
    power={'+5V','+6V25_PROG','TARGET_VCC','USB_VBUS','GND'}
    default[:]=[v for v in default if isinstance(v,list) or v not in hv|power]
    classes=[default]
    for label,names,width in [('HV',hv,600),('Power',power,600)]:
        classes.append(N('class',A(label),*(A(n) for n in sorted(names)),N('circuit',N('use_via','Via[0-1]_800:400_um')),N('rule',N('width',width),N('clearance',200))))
    path.write_text(dsn[:block.start()]+'\n'.join('    '+dump(c) for c in classes)+'\n'+dsn[block.end():],encoding='utf8')
    print('Exported DSN')

def import_session():
    b=k.LoadBoard(str(OUT/(NAME+'.kicad_pcb')))
    assert k.ImportSpecctraSES(b,str(VAL/'writer.ses'))
    # SES carries copper padstack layers only. Restore solder-mask openings.
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute()==k.PAD_ATTRIB_PTH:
                layers=pad.GetLayerSet(); layers.AddLayer(k.F_Mask); layers.AddLayer(k.B_Mask); pad.SetLayerSet(layers)
    k.SaveBoard(str(OUT/(NAME+'.kicad_pcb')),b)
    print('Imported routed session',len(list(b.GetTracks())),'track/via objects')

def finish():
    b=k.LoadBoard(str(OUT/(NAME+'.kicad_pcb')))
    for z in list(b.Zones()): b.Delete(z)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname()=='GND' and (fp.GetReference() in ['J1','J2','J5'] or (fp.GetReference()=='U10' and pad.GetNumber()=='3')):
                pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
    for layer in [k.F_Cu,k.B_Cu]:
        z=k.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet('GND')); z.SetLocalClearance(k.FromMM(.3)); z.SetThermalReliefGap(k.FromMM(.3)); z.SetThermalReliefSpokeWidth(k.FromMM(.3)); z.SetPadConnection(k.ZONE_CONNECTION_THERMAL); z.SetMinThickness(k.FromMM(.25)); z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().NewOutline()
        for x,y in [(1,1),(149,1),(149,104),(1,104)]: p=pt(x,y); z.Outline().Append(p.x,p.y)
        b.Add(z)
    b.BuildConnectivity(); k.ZONE_FILLER(b).Fill(b.Zones()); k.SaveBoard(str(OUT/(NAME+'.kicad_pcb')),b)
    print('Filled two GND zones')

def silk():
    b=k.LoadBoard(str(OUT/(NAME+'.kicad_pcb')))
    footprints=list(b.GetFootprints())
    for f in footprints:
        for item in f.GraphicalItems():
            if isinstance(item,k.PCB_TEXT): item.SetVisible(True)
        f.Reference().SetVisible(False)
    def rect(box): return (box.GetX(),box.GetY(),box.GetX()+box.GetWidth(),box.GetY()+box.GetHeight())
    def overlaps(a,z,margin=0): return a[0]<z[2]+margin and a[2]>z[0]-margin and a[1]<z[3]+margin and a[3]>z[1]-margin
    bodies={f.GetReference():rect(f.GetBoundingBox(False,False)) for f in footprints}
    occupied=[rect(t.GetBoundingBox()) for t in b.GetDrawings() if isinstance(t,k.PCB_TEXT)]
    shown=[]; fab=[]
    for f in sorted(footprints,key=lambda f: (bodies[f.GetReference()][2]-bodies[f.GetReference()][0])*(bodies[f.GetReference()][3]-bodies[f.GetReference()][1]),reverse=True):
        ref=f.GetReference()
        if ref.startswith(('TP','H')): continue
        label=f.Reference(); label.SetTextSize(k.VECTOR2I(k.FromMM(.8),k.FromMM(.8))); label.SetTextThickness(k.FromMM(.12)); label.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T)); label.SetLayer(k.F_SilkS)
        box=bodies[ref]; cx=(box[0]+box[2])//2; cy=(box[1]+box[3])//2
        width=k.FromMM(max(1,len(ref)*.62)); height=k.FromMM(1.1)
        candidates=[]
        for gap in [.4,.9,1.6,2.5,3.5]:
            d=k.FromMM(gap)
            candidates.extend([(cx,box[1]-height//2-d),(cx,box[3]+height//2+d),(box[0]-width//2-d,cy),(box[2]+width//2+d,cy)])
        for x,y in candidates:
            a=(x-width//2,y-height//2,x+width//2,y+height//2)
            if a[0]<k.FromMM(50.6) or a[2]>k.FromMM(199.4) or a[1]<k.FromMM(50.6) or a[3]>k.FromMM(154.4): continue
            if any(overlaps(a,z,k.FromMM(.2)) for z in bodies.values()) or any(overlaps(a,z,k.FromMM(.2)) for z in occupied): continue
            label.SetPosition(k.VECTOR2I(x,y)); label.SetVisible(True); occupied.append(a); shown.append(ref); break
        else:
            label.SetLayer(k.F_Fab); label.SetVisible(True); fab.append(ref)
    k.SaveBoard(str(OUT/(NAME+'.kicad_pcb')),b)
    (VAL/'silkscreen.json').write_text(json.dumps({'silkscreen_references':shown,'fab_only_references':fab},indent=2)+'\n',encoding='utf8')
    print('Placed',len(shown),'readable silkscreen references;',len(fab),'on Fab only:',fab)

def audit():
    comps=manifest(); b=k.LoadBoard(str(OUT/(NAME+'.kicad_pcb'))); fps={f.GetReference():f for f in b.GetFootprints()}
    for ref,c in comps.items():
        fp=fps[ref]; assert fp.GetValue()==c['value'],ref
        for pad in fp.Pads():
            expected=c['nets'].get(pad.GetNumber(),'').replace('~{OUT}/~{DTR2}','~{OUT}{slash}~{DTR2}')
            assert pad.GetNetname()==expected,(ref,pad.GetNumber(),pad.GetNetname(),c['nets'])
            if pad.GetAttribute()==k.PAD_ATTRIB_PTH: assert pad.IsOnLayer(k.F_Mask) and pad.IsOnLayer(k.B_Mask),(ref,'closed PTH soldermask')
    assert len(comps)+4==len(fps)
    with (OUT/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['Reference','Value','Footprint','Datasheet'])
        for ref,c in sorted(comps.items()): w.writerow([ref,c['value'],c['footprint'],c['datasheet']])
    tracks=list(b.GetTracks()); report={'components':len(comps),'board_mm':SIZE,'tracks':sum(not isinstance(t,k.PCB_VIA) for t in tracks),'vias':sum(isinstance(t,k.PCB_VIA) for t in tracks),'gnd_zones':b.GetAreaCount(),'pads_match_schematic':True,'physical_hardware_tested':False}
    (VAL/'board_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8'); print(report)

if __name__=='__main__':
    {'schema':schema,'place':place,'export':export,'import':import_session,'finish':finish,'silk':silk,'audit':audit}[sys.argv[1]]()
