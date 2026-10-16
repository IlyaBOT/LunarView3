"""Keep intentional model/pad/text changes in the Writer's own footprint library."""
from pathlib import Path
import json,re,sys
import pcbnew as k
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kicad_sexpr import parse,one,children,dump

root=Path(__file__).resolve().parents[1]/'Lunar-Writer'
b=k.LoadBoard(str(root/'Lunar_Writer.kicad_pcb'))
report=json.loads((root/'validation/drc.json').read_text(encoding='utf8'))
refs={re.match(r'Footprint (\w+)',v['items'][0]['description'])[1] for v in report['violations'] if v['type']=='lib_footprint_mismatch'}
mapping={}
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref not in refs:continue
    old=f.GetFPID().GetUniStringLibId()
    name='Writer_'+ref+'_'+old.split(':')[1]
    new='ProjectFootprints:'+name
    f.SetFPIDAsString(new);mapping[ref]=new
    clone=k.FOOTPRINT(f);clone.SetPosition(k.VECTOR2I(0,0));clone.SetOrientationDegrees(0);clone.SetReference('REF**');clone.SetValue(name)
    for pad in clone.Pads():pad.SetNetCode(0)
    k.FootprintSave(str(root/'ProjectFootprints.pretty'),clone)
for path in root.glob('*.kicad_sch'):
    tree=parse(path.read_text(encoding='utf8'));changed=False
    for sym in children(tree,'symbol'):
        props={p[1]:p for p in children(sym,'property')}
        ref=props['Reference'][2]
        if ref in mapping:props['Footprint'][2]=mapping[ref];changed=True
    if changed:path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(x) for x in tree[1:])+'\n)\n',encoding='utf8')
k.SaveBoard(str(root/'Lunar_Writer.kicad_pcb'),b)
(root/'validation/local_footprints.json').write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf8')
print('Preserved',len(mapping),'customized footprints in the project library.')
