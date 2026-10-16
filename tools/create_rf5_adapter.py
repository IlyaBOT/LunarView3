"""Create a separate read-only, buffered KR573RF5 adapter. Never edits the dumper."""
from pathlib import Path
import copy,csv,json,sys,uuid,math
import pcbnew as k
import generate_schematic as g
from kicad_sexpr import parse,dump,one,children,node as N,Atom as A
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Adapter-KR573RF5'
NAME='KR573RF5_Adapter'
UUID=str(uuid.uuid5(uuid.NAMESPACE_URL,'KR573RF5/READONLY/adapter/root'))
SOCKET='Package_DIP:DIP-24_W15.24mm_Socket_LongPads'
PLUG='ProjectFootprints:DIP28_Male_RoundPins_Bottom'
BUF='Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm'
PACK='Resistor_SMD:R_Array_Convex_4x0603'
HOST={'1':None,'2':None,'3':'A7','4':'A6','5':'A5','6':'A4','7':'A3','8':'A2','9':'A1','10':'A0',
 '11':'ROM_D0','12':'ROM_D1','13':'ROM_D2','14':'GND','15':'ROM_D3','16':'ROM_D4','17':'ROM_D5',
 '18':'ROM_D6','19':'ROM_D7','20':'ROM_CE#','21':'A10','22':'ROM_OE#','23':None,'24':'A9','25':'A8',
 '26':None,'27':None,'28':'+5V'}
ROM={'1':'A7','2':'A6','3':'A5','4':'A4','5':'A3','6':'A2','7':'A1','8':'A0','9':'RF5_D0',
 '10':'RF5_D1','11':'RF5_D2','12':'GND','13':'RF5_D3','14':'RF5_D4','15':'RF5_D5','16':'RF5_D6',
 '17':'RF5_D7','18':'ROM_CE#','19':'A10','20':'ROM_OE#','21':'+5V','22':'A9','23':'A8','24':'+5V'}
BUFFER={'1':'+5V','10':'GND','19':'ROM_OE#','20':'+5V',**{str(2+i):f'RF5_D{i}' for i in range(8)},
 **{str(18-i):f'ROM_D{i}' for i in range(8)}}

def write_tree(path,tree):
    path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(x) for x in tree[1:])+'\n)\n',encoding='utf8')

def rf5_symbol():
    s=N('symbol','KR573RF5_ReadOnly',N('pin_names',N('offset',1.016)),N('in_bom',A('yes')),N('on_board',A('yes')))
    for name,value,y in [('Reference','J',25.4),('Value','KR573RF5 socket / READ ONLY',22.86),('Footprint',SOCKET,0),('Datasheet','https://storage.ua.prom.st/1093634_kr573rf5.pdf',0)]:
        s.append(N('property',name,value,N('at',0,y,0),g.effects(1.27,hide=name in ['Footprint','Datasheet'])))
    s.append(N('symbol','KR573RF5_ReadOnly_0_1',N('rectangle',N('start',-10.16,20.32),N('end',10.16,-20.32),N('stroke',N('width',0.254),N('type',A('default'))),N('fill',N('type',A('background'))))))
    body=N('symbol','KR573RF5_ReadOnly_1_1')
    def pin(num,name,typ,x,y,angle):
        body.append(N('pin',A(typ),A('line'),N('at',x,y,angle),N('length',2.54),N('name',name,g.effects(1.0)),N('number',str(num),g.effects(1.0))))
    for i,(num,name) in enumerate([(8,'A0'),(7,'A1'),(6,'A2'),(5,'A3'),(4,'A4'),(3,'A5'),(2,'A6'),(1,'A7'),(23,'A8'),(22,'A9'),(19,'A10'),(18,'~{CE}'),(20,'~{OE}')]):
        pin(num,name,'input',-12.7,15.24-i*2.54,0)
    for i,num in enumerate([9,10,11,13,14,15,16,17]):pin(num,f'D{i}','tri_state',12.7,10.16-i*2.54,180)
    pin(24,'VCC','power_in',-2.54,22.86,270)
    pin(21,'VPP (5V READ)','power_in',2.54,22.86,270)
    pin(12,'GND','power_in',0,-22.86,90)
    s.append(body);return s

def buffer_symbol():
    s=g.standard('74xx:74HC245');old=s[1].split(':')[-1];s[1]='HCT245_ReadBuffer'
    for sub in children(s,'symbol'):sub[1]=sub[1].replace(old,s[1])
    for p in g.pins(s):
        if str(one(p,'number')[1]) in {str(i) for i in range(2,10)}:p[1]=A('input')
    for p in children(s,'property'):
        if p[1]=='Value':p[2]='74HCT245 (DIR=1)'
        if p[1]=='Footprint':p[2]=BUF
        if p[1]=='Datasheet':p[2]='https://www.ti.com/lit/ds/symlink/sn74hct245.pdf'
    for sub in children(s,'symbol'):
        pass
    return s

def plug_library():
    fp=N('footprint','DIP28_Male_RoundPins_Bottom',N('version',20260206),N('generator','pcbnew'),N('layer','B.Cu'),
         N('descr','Bottom male DIP28 plug, TOP-VIEW numbering. Two 1x14 ROUND pin strips, 2.54 pitch, rows 15.24. Standoff >=2.5 mm.'),N('attr',A('through_hole')))
    def eff():return N('effects',N('font',N('size',0.8,0.8),N('thickness',0.12)),N('justify',A('mirror')))
    fp.extend([N('property','Reference','REF**',N('at',7.62,-1.5,0),N('layer','B.SilkS'),eff()),N('property','Value','DIP28 male plug',N('at',7.62,34.5,0),N('layer','B.Fab'),N('hide',A('yes')),eff())])
    for pin in range(1,29):
        x=0 if pin<=14 else 15.24;y=(pin-1 if pin<=14 else 28-pin)*2.54
        fp.append(N('pad',str(pin),A('thru_hole'),A('rect' if pin==1 else 'circle'),N('at',x,y),N('size',1.8,1.8),N('drill',0.8),N('layers','*.Cu','*.Mask')))
    for x in [0,15.24]:
        for layer,w in [('B.CrtYd',0.05),('B.Fab',0.1)]:
            pts=[(x-1.25,-1.25),(x+1.25,-1.25),(x+1.25,34.27),(x-1.25,34.27),(x-1.25,-1.25)]
            for a,b in zip(pts,pts[1:]):fp.append(N('fp_line',N('start',*a),N('end',*b),N('stroke',N('width',w),N('type',A('solid'))),N('layer',layer)))
    fp.append(N('model','${KIPRJMOD}/3DModels/DIP28_RoundPinPlug.wrl',N('offset',N('xyz',0,0,0)),N('scale',N('xyz',1/2.54,1/2.54,1/2.54)),N('rotate',N('xyz',0,0,0))))
    return fp

def model_plug():
    # B.Cu model orientation: positive local Y follows the top-view pad rows.
    parts=['#VRML V2.0 utf8\n# Generic round male pins. Mechanical envelope, not vendor CAD.']
    for x in [0,15.24]:
        parts.append(f'Transform {{ translation {x} 16.51 1.5 children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.08 0.08 0.08 }} }} geometry Box {{ size 1.8 35.0 2.5 }} }} ] }}')
        for i in range(14):
            points=[f'{x+0.225*math.cos(j*math.pi/8):.6f} {i*2.54+0.225*math.sin(j*math.pi/8):.6f} {z}' for z in [0,7] for j in range(16)]
            faces=[' '.join(map(str,range(15,-1,-1)))+' -1',' '.join(map(str,range(16,32)))+' -1']
            faces += [f'{j} {(j+1)%16} {(j+1)%16+16} {j+16} -1' for j in range(16)]
            parts.append('Shape { appearance Appearance { material Material { diffuseColor 0.85 0.76 0.40 } } geometry IndexedFaceSet { solid FALSE coord Coordinate { point [ '+', '.join(points)+' ] } coordIndex [ '+', '.join(faces)+' ] } }')
    (OUT/'3DModels/DIP28_RoundPinPlug.wrl').write_text('\n'.join(parts),encoding='utf8')

def tidy_rn_schematic(t):
    """Draw each pack's common supply as one bus with one power arrow."""
    for ref, x in [('RN1',110.49),('RN2',148.59)]:
        for symbol in children(t,'symbol'):
            props=children(symbol,'property')
            symbol_ref=next(p[2] for p in props if p[1]=='Reference')
            if symbol_ref==ref:
                for p in props:
                    if p[1]=='Datasheet':p[2]='https://www.bourns.com/docs/Product-Datasheets/CATCAY.pdf'
                    if p[1] in ['Reference','Value']:
                        one(p,'at')[1:]=[x,138.43 if p[1]=='Reference' else 141.43,90]
        bus_x=round(x-8.89,2)
        obsolete=[]
        for symbol in children(t,'symbol'):
            a=one(symbol,'at')
            if (one(symbol,'lib_id')[1]=='power:+5V' and abs(float(a[1])-bus_x)<0.001
                    and 149<float(a[2])<157):obsolete.append(symbol)
        for symbol in obsolete:t.remove(symbol)
        for y1,y2 in zip([148.59,151.13,153.67],[151.13,153.67,156.21]):
            t.append(N('wire',N('pts',N('xy',bus_x,y1),N('xy',bus_x,y2)),N('stroke',N('width',0),N('type',A('default'))),N('uuid',g.uid(f'RF5/{ref}/power-bus/{y1}'))))
        for y in [151.13,153.67]:
            t.append(N('junction',N('at',bus_x,y),N('diameter',0),N('color',0,0,0,0),N('uuid',g.uid(f'RF5/{ref}/power-dot/{y}'))))

def schematic():
    g.NAME=NAME;g.BOM.clear();g.COUNTERS.clear()
    custom=[rf5_symbol(),buffer_symbol()]
    write_tree(OUT/'ProjectSymbols.kicad_sym',N('kicad_symbol_lib',N('version',20250114),N('generator',A('eeschema')),*custom))
    for s in custom:
        cached=copy.deepcopy(s);cached[1]='ProjectSymbols:'+s[1];g.USED[cached[1]]=cached
    page=g.Page(NAME+'.kicad_sch','KR573RF5 / 2048 x 8 / 5 V READ ONLY',OUT,UUID)
    page.component('Connector_Generic:Conn_01x28','J1','DIP28 male / bottom',48.26,93.98,HOST,PLUG)
    page.component('ProjectSymbols:KR573RF5_ReadOnly','J2','KR573RF5 socket DIP24',137.16,93.98,ROM,SOCKET)
    page.component('ProjectSymbols:HCT245_ReadBuffer','U1','SN74HCT245PW',233.68,93.98,BUFFER,BUF)
    page.cap('C1','100nF / 16V',183,149.86,'+5V')
    page.cap('C2','100nF / 16V',219,149.86,'+5V')
    page.cap('C3','1uF / 10V',255,149.86,'+5V')
    for ref,base,x in [('RN1',0,110.49),('RN2',4,148.59)]:
        mapping={str(i+1):f'RF5_D{base+i}' for i in range(4)}
        mapping.update({str(i):'+5V' for i in range(5,9)})
        page.component('Device:R_Pack04',ref,'4x47k CAY16-473J4LF',x,151.13,mapping,PACK,angle=90)
    page.power('+5V',110.49,185.42,True);page.power('GND',144.78,185.42,True)
    page.text('J1 numbering: TOP VIEW, notch at top.\nDIP28 pins 1, 2, 23, 26, 27 unused.\nA11..A15 ignored: read addresses 0..2047.\nNever enable programming or apply VPP.',15.24,157.48,1.02)
    page.text('U1: HCT TTL input -> 5 V CMOS output.\nDIR=HIGH: RF5 data A -> dumper data B.\nOE# follows ROM_OE#. Do not substitute HC245.',15.24,187.96,1.02)
    page.save()
    path=OUT/(NAME+'.kicad_sch');t=parse(path.read_text(encoding='utf8'))
    one(t,'paper')[1]='A4';tb=one(t,'title_block')
    one(tb,'title')[1]='KR573RF5 compact read-only adapter';one(tb,'date')[1]='2026-10-07'
    one(tb,'comment')[2]='5 V READ ONLY / buffered TTL data / no VPP'
    tidy_rn_schematic(t)
    write_tree(path,t)
    syms={next(p[2] for p in children(s,'property') if p[1]=='Reference'):str(one(s,'uuid')[1]) for s in children(t,'symbol')}
    for item in g.BOM:item['uuid']=syms[item['ref']]
    (OUT/'validation/manifest.json').write_text(json.dumps(g.BOM,ensure_ascii=False,indent=2),encoding='utf8')
    with (OUT/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Side'])
        for c in g.BOM:w.writerow([c['ref'],c['value'],c['footprint'],'top' if c['ref']=='J2' else 'bottom'])
    return g.BOM

def pcb(bom):
    b=k.BOARD();b.SetFileName(str(OUT/(NAME+'.kicad_pcb')))
    settings=b.GetDesignSettings();settings.m_MinClearance=k.FromMM(0.2);settings.m_TrackMinWidth=k.FromMM(0.2)
    nets={n:k.NETINFO_ITEM(b,n) for c in bom for n in c['nets'].values() if n}
    for pin,net in HOST.items():
        if net is None:
            name=f'unconnected-(J1-Pin_{pin}-Pad{pin})';nets[name]=k.NETINFO_ITEM(b,name)
    for net in nets.values():b.Add(net)
    nc=settings.m_NetSettings.GetDefaultNetclass()
    nc.SetTrackWidth(k.FromMM(0.2));nc.SetViaDiameter(k.FromMM(0.8));nc.SetViaDrill(k.FromMM(0.4));nc.SetClearance(k.FromMM(0.2))
    positions={'J1':(52.54,52.54,0),'J2':(55.08,55.08,0),'U1':(61.43,72.8,180),'C1':(70.32,52,90),'C2':(58.57,66.2,90),'C3':(61.43,58.5,0),'RN1':(58.2,81,0),'RN2':(63.3,81,0)}
    for item in bom:
        lib,name=item['footprint'].split(':');libpath=g.footprint_path(item['footprint'],OUT).parent
        fp=k.FootprintLoad(str(libpath),name);assert fp
        fp.SetFPIDAsString(item['footprint']);fp.SetReference(item['ref']);fp.SetValue(item['value'])
        if item['ref']=='J2':fp.SetField('Datasheet','https://storage.ua.prom.st/1093634_kr573rf5.pdf')
        if item['ref']=='U1':fp.SetField('Datasheet','https://www.ti.com/lit/ds/symlink/sn74hct245.pdf')
        if item['ref'] in ['RN1','RN2']:fp.SetField('Datasheet','https://www.bourns.com/docs/Product-Datasheets/CATCAY.pdf')
        b.Add(fp)
        if item['ref']!='J2' and item['ref']!='J1':fp.Flip(k.VECTOR2I(0,0),k.FLIP_DIRECTION_LEFT_RIGHT)
        x,y,angle=positions[item['ref']];fp.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)));fp.SetOrientationDegrees(angle)
        path=k.KIID_PATH();path.push_back(k.KIID(UUID));path.push_back(k.KIID(item['uuid']));fp.SetPath(path)
        for pad in fp.Pads():
            net=item['nets'].get(pad.GetNumber())
            if net is None and item['ref']=='J1':net=f'unconnected-(J1-Pin_{pad.GetNumber()}-Pad{pad.GetNumber()})'
            if net:pad.SetNet(nets[net])
        fp.Value().SetVisible(False);fp.Reference().SetVisible(False)
    # 22.86 x 38.10 mm; top socket shifted 2.54 mm to keep all holes separate.
    pts=[(50,50),(72.86,50),(72.86,88.1),(50,88.1),(50,50)]
    for a,z in zip(pts,pts[1:]):
        s=k.PCB_SHAPE(b);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1])));s.SetEnd(k.VECTOR2I(k.FromMM(z[0]),k.FromMM(z[1])));s.SetLayer(k.Edge_Cuts);s.SetWidth(k.FromMM(0.05));b.Add(s)
    def text(string,x,y,size,layer=k.F_SilkS,angle=0):
        t=k.PCB_TEXT(b);t.SetText(string);t.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)));t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size)));t.SetTextThickness(k.FromMM(0.12));t.SetLayer(layer);t.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T));t.SetMirrored(layer==k.B_SilkS);b.Add(t)
    text('KR573RF5',61.43,51.3,0.9);text('5V READ ONLY',61.43,87,0.8)
    text('1',55.08,52.8,0.8);text('J1 PIN 1',58,51.2,0.8,k.B_SilkS)
    text('U1 HCT245',61.43,77.6,0.8,k.B_SilkS);text('DIP28 / BOTTOM',61.43,87,0.8,k.B_SilkS)
    text('RN1',58.2,83.5,0.8,k.B_SilkS);text('RN2',63.3,83.5,0.8,k.B_SilkS)
    k.SaveBoard(str(OUT/(NAME+'.kicad_pcb')),b)
    assert k.ExportSpecctraDSN(b,str(OUT/'validation/adapter_unrouted.dsn'))
    print('Created schematic and placed PCB:',OUT)

def main():
    assert not(OUT/(NAME+'.kicad_pcb')).exists() or '--rebuild' in sys.argv,'Do not overwrite an existing adapter'
    for d in ['validation','ProjectFootprints.pretty','3DModels','fabrication']: (OUT/d).mkdir(parents=True,exist_ok=True)
    write_tree(OUT/'ProjectFootprints.pretty/DIP28_Male_RoundPins_Bottom.kicad_mod',plug_library());model_plug()
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "ProjectFootprints") (type "KiCad") (uri "${KIPRJMOD}/ProjectFootprints.pretty") (options "") (descr "Adapter local footprints")))\n',encoding='utf8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "ProjectSymbols") (type "KiCad") (uri "${KIPRJMOD}/ProjectSymbols.kicad_sym") (options "") (descr "Read-only RF5 symbols")))\n',encoding='utf8')
    pro=json.loads((ROOT/'Dumper-Lite/NM27C512_Dumper_Lite.kicad_pro').read_text(encoding='utf8'))
    ds=pro['board']['design_settings'];ds['drc_exclusions']=[]
    ds['rules'].update(min_clearance=0.2,min_track_width=0.2,min_hole_clearance=0.2,min_through_hole_diameter=0.4,min_via_diameter=0.8,min_via_annular_width=0.15,min_text_height=0.6)
    nc=pro['net_settings']['classes'][0];nc.update(clearance=0.2,track_width=0.2,via_diameter=0.8,via_drill=0.4)
    pro['net_settings']['classes']=[nc];pro['net_settings']['netclass_patterns']=[]
    pro['erc']['erc_exclusions']=[]
    pro['meta']['filename']=NAME+'.kicad_pro'
    (OUT/(NAME+'.kicad_pro')).write_text(json.dumps(pro,indent=2),encoding='utf8')
    (OUT/(NAME+'.kicad_dru')).write_text('''(version 1)
# Intentional vertical stacking: J1 top tails must be trimmed flush before J2.
# Only the J1/J2 mechanical courtyard interaction is allowed; electrical DRC stays active.
(rule "DIP socket above flush plug tails"
  (condition "(A.Reference == 'J1' && B.Reference == 'J2') || (A.Reference == 'J2' && B.Reference == 'J1')")
  (constraint courtyard_clearance (min -1mm)))
''',encoding='utf8')
    pcb(schematic())

if __name__=='__main__':main()
