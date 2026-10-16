"""Validate generated KiCad reports, critical power pins and manufacturing outputs."""
from pathlib import Path
import hashlib,json,zipfile
import pcbnew as k

p=Path(__file__).resolve().parents[1]/'Lunar-Writer'
b=k.LoadBoard(str(p/'Lunar_Writer.kicad_pcb'))
m=json.loads((p/'validation/manifest.json').read_text(encoding='utf8'))
checks={
    'J4':{'1':'VIN_RAW','2':'GND'},
    'U11':{'1':'BOOST_COMP','2':'BOOST_FB','3':'GND','4':'BOOST_SW','5':'VIN_PROTECTED'},
    'U7':{'1':'LM_ADJ','2':'+6V25_PROG','3':'VIN_PROTECTED'},
    'U12':{'1':'VPP_ADJ12','2':'VPP_12V75','3':'BOOST_30V'},
    'U13':{'1':'VPP_ADJ13','2':'VPP_HIGH','3':'BOOST_30V'},
    'JP1':{'1':'VPP_12V75','2':'VPP_IN','3':'VPP_HIGH'},
}
for ref,pins in checks.items():
    for num,net in pins.items():assert m[ref]['nets'][num]==net,(ref,num,m[ref]['nets'])
for name,keys in [('erc.json',['violations']),('drc.json',['violations','unconnected_items','schematic_parity'])]:
    d=json.loads((p/'validation'/name).read_text(encoding='utf8'))
    if name=='erc.json': d={'violations':[v for sheet in d['sheets'] for v in sheet['violations']]}
    for key in keys:assert not d[key],(name,key)
for name in ['Lunar_Writer-F_Cu.gtl','Lunar_Writer-B_Cu.gbl','Lunar_Writer-F_Mask.gts','Lunar_Writer-B_Mask.gbs']:
    assert (p/'production'/name).stat().st_size>2000,name
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetAttribute()==k.PAD_ATTRIB_PTH:assert pad.IsOnLayer(k.F_Mask) and pad.IsOnLayer(k.B_Mask),fp.GetReference()
report={
    'date':'2026-10-12','name':'Lunar Writer','revision':1,
    'erc_violations':0,'drc_violations':0,'unconnected_items':0,'schematic_parity_issues':0,
    'supply_pinout_audited':True,'through_hole_mask_openings_audited':True,
    'physical_programming_verified':False,'default_write_locked':True,
    'files':{str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'Lunar_Writer.kicad_pcb',p/'Lunar_Writer.kicad_sch',p/'BOM.csv',*list((p/'production').glob('*'))]},
}
(p/'validation/final_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
with zipfile.ZipFile(p/'Lunar_Writer_Manufacturing.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in (p/'production').iterdir():
        if f.is_file():z.write(f,f.name)
print('Final electrical/manufacturing audit passed. Manufacturing ZIP created.')
