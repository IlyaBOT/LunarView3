"""Check source pin table against the exported netlist, PCB nets and top-view orientation."""
from pathlib import Path
import json,xml.etree.ElementTree as ET,math
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Adapter-KR573RF5'
netlist=ET.parse(OUT/'validation/netlist.xml').getroot()
actual={n.attrib['name']:{(p.attrib['ref'],p.attrib['pin']) for p in n.findall('node')} for n in netlist.findall('./nets/net')}
# Independent transcription of the RF5 published 24-pin diagram and the
# NM27C512 28-pin diagram. Data goes through HCT245, never a direct jumper.
addresses=[('A7',1,3),('A6',2,4),('A5',3,5),('A4',4,6),('A3',5,7),('A2',6,8),('A1',7,9),('A0',8,10),('A10',19,21),('A9',22,24),('A8',23,25)]
checks=[]
def check(description,condition):
    assert condition,description;checks.append(description)
for signal,rom,host in addresses:check(signal+' mapping',actual[signal]=={('J2',str(rom)),('J1',str(host))})
check('CE mapping',actual['ROM_CE#']=={('J1','20'),('J2','18')})
check('OE mapping and buffer enable',actual['ROM_OE#']=={('J1','22'),('J2','20'),('U1','19')})
check('VPP tied to read supply and DIR fixed high',actual['+5V']=={('J1','28'),('J2','21'),('J2','24'),('U1','1'),('U1','20'),('C1','1'),('C2','1'),('C3','1')}|{(r,str(p)) for r in ['RN1','RN2'] for p in range(5,9)})
check('Ground mapping',actual['GND']=={('J1','14'),('J2','12'),('U1','10'),('C1','2'),('C2','2'),('C3','2')})
for i,(rp,hp) in enumerate(zip([9,10,11,13,14,15,16,17],[11,12,13,15,16,17,18,19])):
    check(f'D{i} raw input and idle bias',actual[f'RF5_D{i}']=={('J2',str(rp)),('U1',str(2+i)),('RN1' if i<4 else 'RN2',str(i%4+1))})
    check(f'D{i} buffered output',actual[f'ROM_D{i}']=={('U1',str(18-i)),('J1',str(hp))})
b=k.LoadBoard(str(OUT/'KR573RF5_Adapter.kicad_pcb'))
fps={fp.GetReference():fp for fp in b.GetFootprints()}
for fp in fps.values():
    for pad in fp.Pads():
        check(f'PCB {fp.GetReference()}.{pad.GetNumber()} net',(fp.GetReference(),pad.GetNumber()) in actual.get(pad.GetNetname(),set()))
for ref,count,x,y in [('J1',28,52.54,52.54),('J2',24,55.08,55.08)]:
    pads={p.GetNumber():p for p in fps[ref].Pads()};half=count//2
    for num,p in pads.items():
        n=int(num);ex=x if n<=half else x+15.24;ey=y+(n-1 if n<=half else count-n)*2.54
        check(f'{ref}.{n} top-view orientation',abs(k.ToMM(p.GetPosition().x)-ex)<1e-5 and abs(k.ToMM(p.GetPosition().y)-ey)<1e-5)
check('J1 mounted below board',fps['J1'].GetLayer()==k.B_Cu)
check('J2 mounted above board',fps['J2'].GetLayer()==k.F_Cu)
check('Buffer mounted below board',fps['U1'].GetLayer()==k.B_Cu)
for a in fps['J1'].Pads():
    for z in fps['J2'].Pads():
        distance=math.hypot(k.ToMM(a.GetPosition().x-z.GetPosition().x),k.ToMM(a.GetPosition().y-z.GetPosition().y))
        check(f'Distinct plug/socket holes {a.GetNumber()}/{z.GetNumber()}',distance>=2.53999)
drc=json.loads((OUT/'validation/drc.json').read_text());erc=json.loads((OUT/'validation/erc.json').read_text())
check('DRC clear',not(drc['violations'] or drc['unconnected_items'] or drc['schematic_parity']))
check('ERC clear',all(not s['violations'] for s in erc['sheets']))
result={'checks_passed':len(checks),'footprints':len(fps),'track_segments':sum(not isinstance(t,k.PCB_VIA) for t in b.GetTracks()),'vias':sum(isinstance(t,k.PCB_VIA) for t in b.GetTracks()),'width_mm':22.86,'height_mm':38.1,'mode':'5V READ ONLY','check_names':checks}
(OUT/'validation/connectivity_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print({key:value for key,value in result.items() if key!='check_names'})
