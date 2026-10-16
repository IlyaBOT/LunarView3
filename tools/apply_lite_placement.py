"""Publish the reviewed Lite candidate after the PCB editor has been closed."""
from pathlib import Path
import copy, hashlib, json, shutil
from kicad_sexpr import parse, dump, one, children, node as N

ROOT=Path(__file__).resolve().parents[1]
LITE=ROOT/'Dumper-Lite'
OUT=LITE/'validation'

def write_tree(path,tree):
    path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(x) for x in tree[1:])+'\n)\n',encoding='utf8')

def correct_rgb(fp):
    for pad in children(fp,'pad'):
        if pad[2]=='thru_hole':
            one(pad,'size')[1:]=[1.11,1.8]
            old=one(pad,'clearance')
            if old is None: pad.append(N('clearance',.15))
            else: old[1]=.15
    for obj in children(fp,'fp_text'):
        if one(obj,'layer')[1]=='F.SilkS':
            one(one(one(obj,'effects'),'font'),'size')[1:]=[.8,.8]

def main():
    audit=json.loads((OUT/'placement_audit.json').read_text())
    source=LITE/'NM27C512_Dumper_Lite.kicad_pcb'
    assert not (LITE/'~NM27C512_Dumper_Lite.kicad_pcb.lck').exists(), 'Close the Lite PCB editor first'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==audit['source_sha256'], 'The saved board changed after review'
    drc=json.loads((OUT/'drc_placement_candidate.json').read_text())
    assert all(v['type']=='lib_footprint_issues' for v in drc['violations']), 'Resolve candidate geometry/silkscreen DRC first'
    for folder in [ROOT,LITE]:
        mod=folder/'ProjectFootprints.pretty/RGB_CA_5050_or_THT5.kicad_mod'
        backup=OUT/'placement_backup'/mod.relative_to(ROOT)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists(): shutil.copy2(mod,backup)
        tree=parse(mod.read_text(encoding='utf8')); correct_rgb(tree); write_tree(mod,tree)
    # Correct the same previously created RGB lands in the full board, while
    # retaining its entire existing placement and every unrelated board object.
    full=ROOT/'NM27C512_Dumper.kicad_pcb'
    assert not (ROOT/'~NM27C512_Dumper.kicad_pcb.lck').exists(), 'Close the full PCB editor first'
    backup=OUT/'placement_backup'/'Full_before_RGB_land_correction.kicad_pcb'
    if not backup.exists(): shutil.copy2(full,backup)
    tree=parse(full.read_text(encoding='utf8')); old=copy.deepcopy(tree)
    rgb=next(f for f in children(tree,'footprint') if any(p[1]=='Reference' and p[2]=='D2' for p in children(f,'property')))
    correct_rgb(rgb)
    assert [x for x in children(tree,'footprint') if x is not rgb]==[x for x in children(old,'footprint') if not any(p[1]=='Reference' and p[2]=='D2' for p in children(x,'property'))]
    assert [x for x in tree if not(isinstance(x,list) and x[0]=='footprint')]==[x for x in old if not(isinstance(x,list) and x[0]=='footprint')]
    write_tree(full,tree)
    shutil.copy2(OUT/'placement_candidate.kicad_pcb',source)
    audit.update({'applied_to':'Dumper-Lite/NM27C512_Dumper_Lite.kicad_pcb',
                  'published_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'full_board_change':'RGB D2 THT land width / local pad clearance / silkscreen text size only; full placement preserved'})
    (OUT/'placement_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print('Lite placement published; full board placement retained, RGB lands corrected in both projects.')

if __name__=='__main__': main()
