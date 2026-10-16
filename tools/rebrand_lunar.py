"""Change active product names while preserving Dumper copper and pad data."""
from pathlib import Path
import copy, hashlib, json, shutil
from kicad_sexpr import parse, children, one, dump
ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'validation/lunar-products-2026-10-12'
VAL.mkdir(exist_ok=True)

def save(path,tree):
    path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(n) for n in tree[1:])+'\n)\n',encoding='utf8')

pcb=ROOT/'Dumper-Lite/NM27C512_Dumper_Lite.kicad_pcb'
assert not list(pcb.parent.glob('*.lck')), 'Save and close the Dumper PCB editor first'
before=parse(pcb.read_text(encoding='utf8')); after=copy.deepcopy(before)
digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
backup=VAL/'before-renaming'/pcb.name; backup.parent.mkdir(exist_ok=True)
if not backup.exists(): shutil.copy2(pcb,backup)
changed=[]
for item in children(after,'gr_text'):
    if item[1] in ['ATmega Dumper Lite','ATmega328P USB ROM DUMPER']:
        changed.append(item[1]); item[1]='Lunar Dumper'
save(pcb,after)
def electrical(tree): return [n for n in tree if not isinstance(n,list) or n[0]!='gr_text']
assert electrical(before)==electrical(parse(pcb.read_text(encoding='utf8'))), 'Copper/footprints changed'
sch=ROOT/'Dumper-Lite/NM27C512_Dumper_Lite.kicad_sch'
if not (backup.parent/sch.name).exists(): shutil.copy2(sch,backup.parent/sch.name)
tree=parse(sch.read_text(encoding='utf8')); title=one(one(tree,'title_block'),'title'); title[1]='Lunar Dumper - 5V read-only'
for item in children(tree,'text'):
    if 'NM27C512 Dumper Lite' in item[1]: item[1]=item[1].replace('NM27C512 Dumper Lite','Lunar Dumper')
save(sch,tree)
for rel in ['firmware/lite/identity.h','app-win_forms/MainForm.cs','app-win_forms/Tests/Program.cs','app-win_forms/TestsUI/Program.cs','app-win_forms/LunarView3.csproj','firmware/lite/README.md','Dumper-Lite/README.md','docs/protocol_lite.md','app-win_forms/README.md']:
    path=ROOT/rel; text=path.read_text(encoding='utf8')
    text=text.replace('Lunar Dumper LITE','Lunar Dumper').replace('программатора Lunar Dumper или дампера Lunar Dumper','программатора Lunar Writer или дампера Lunar Dumper')
    if rel=='Dumper-Lite/README.md': text=text.replace('# NM27C512 Dumper Lite','# Lunar Dumper')
    path.write_text(text,encoding='utf8')
report={'dumper_before_sha256':digest,'dumper_after_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest(),'changed_board_text':changed,'all_non_text_pcb_nodes_identical':True,'legacy_file_names_kept_for_existing_paths':True,'writer_project':'Lunar-Writer/Lunar_Writer.kicad_pro'}
(VAL/'rename-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8'); print(report)
