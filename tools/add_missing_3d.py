"""Add visual models only; preserve every other saved PCB/S-expression node."""
from pathlib import Path
import copy, hashlib, json, shutil, sys
from kicad_sexpr import parse, dump, node as N, Atom as A, children, one
ROOT=Path(__file__).resolve().parents[1]
LIB=Path('C:/Program Files/KiCad/10.0/share/kicad/3dmodels')
STAMP='2026-10-07-before-3d'

def write(p,t):
    p.write_text('('+dump(t[0])+'\n'+'\n'.join('  '+dump(x) for x in t[1:])+'\n)\n',encoding='utf8')

def model(name,offset=(0,0,0),hide=False,rotation=(0,0,0)):
    m=N('model',name,N('offset',N('xyz',*offset)),N('scale',N('xyz',1,1,1)),N('rotate',N('xyz',*rotation)))
    if hide:m.append(N('hide',A('yes')))
    return m

def without_models(t):
    if isinstance(t,list):
        return [without_models(x) for x in t if not(isinstance(x,list) and x and x[0]=='model')]
    return t

def main():
    targets=[(ROOT,'NM27C512_Dumper'),(ROOT/'Dumper-Lite','NM27C512_Dumper_Lite')]
    if '--root-only' in sys.argv:targets=targets[:1]
    audit=[]
    for folder,name in targets:
        path=folder/(name+'.kicad_pcb')
        assert not (folder/('~'+name+'.kicad_pcb.lck')).exists(),'PCB editor is open'
        original=path.read_bytes(); before=parse(original.decode('utf8')); after=copy.deepcopy(before)
        original_backup=folder/'backups'/STAMP/path.name
        baseline=original_backup.read_bytes() if original_backup.exists() else original
        models_dir=folder/'3DModels';models_dir.mkdir(exist_ok=True)
        if folder != ROOT:
            shutil.copy2(ROOT/'3DModels/USB_Micro-B_Molex-105017-0001.step',models_dir)
            shutil.copy2(ROOT/'3DModels/KiCad-LIBRARY-LICENSE.txt',models_dir/'KiCad-LIBRARY-LICENSE.txt')
        for relative in ['LED_SMD.3dshapes/LED_RGB_5050-6.step','LED_THT.3dshapes/LED_D5.0mm-4_RGB.step']:
            shutil.copy2(LIB/relative,models_dir/Path(relative).name)
        # Generic envelope only: F1 part number has not been selected.
        generic='''#VRML V2.0 utf8
# Approximate 1812 PPTC visual envelope, not a manufacturer's mechanical model.
Transform { translation 0 0 0.65 children [ Shape { appearance Appearance { material Material { diffuseColor 0.8 0.55 0.16 } } geometry Box { size 4.1 3.2 1.1 } } ] }
Transform { translation -2.05 0 0.55 children [ Shape { appearance Appearance { material Material { diffuseColor 0.75 0.77 0.8 } } geometry Box { size 0.4 3.2 1.1 } } ] }
Transform { translation 2.05 0 0.55 children [ Shape { appearance Appearance { material Material { diffuseColor 0.75 0.77 0.8 } } geometry Box { size 0.4 3.2 1.1 } } ] }
'''
        (models_dir/'PPTC_1812_approx.wrl').write_text(generic,encoding='utf8')
        changed=[]
        for fp in children(after,'footprint'):
            ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
            if ref=='J1':
                fp[:]=[x for x in fp if not(isinstance(x,list) and x[0]=='model')]
                fp.append(model('${KIPRJMOD}/3DModels/USB_Micro-B_Molex-105017-0001.step'));changed.append(ref)
            elif fp[1].endswith(':RGB_CA_5050_or_THT5'):
                fp[:]=[x for x in fp if not(isinstance(x,list) and x[0]=='model')]
                fp.extend([model('${KIPRJMOD}/3DModels/LED_RGB_5050-6.step',rotation=(0,0,180)),model('${KIPRJMOD}/3DModels/LED_D5.0mm-4_RGB.step',(6.595,0,0),True)])
                changed.append(ref)
            elif ref=='F1':
                fp[:]=[x for x in fp if not(isinstance(x,list) and x[0]=='model')]
                # VRML units in KiCad are inches / 2.54 convention; geometry
                # above is in mm, compensated to match actual 4.5 x 3.2 mm.
                m=model('${KIPRJMOD}/3DModels/PPTC_1812_approx.wrl')
                one(one(m,'scale'),'xyz')[1:]=[1/2.54]*3
                fp.append(m);changed.append(ref)
        assert without_models(before)==without_models(after),'Non-model board change'
        backup=folder/'backups'/STAMP;backup.mkdir(parents=True,exist_ok=True)
        if not(backup/path.name).exists():shutil.copy2(path,backup/path.name)
        assert path.read_bytes()==original,'PCB changed during patch'
        write(path,after)
        assert without_models(parse(path.read_text(encoding='utf8')))==without_models(before)
        local=folder/'ProjectFootprints.pretty/RGB_CA_5050_or_THT5.kicad_mod'
        libtree=parse(local.read_text(encoding='utf8'))
        libtree[:]=[x for x in libtree if not(isinstance(x,list) and x[0]=='model')]
        libtree.extend([model('${KIPRJMOD}/3DModels/LED_RGB_5050-6.step',rotation=(0,0,180)),model('${KIPRJMOD}/3DModels/LED_D5.0mm-4_RGB.step',(6.595,0,0),True)])
        write(local,libtree)
        assert without_models(parse(baseline.decode('utf8')))==without_models(after),'Geometry differs from saved backup'
        audit.append({'board':str(path.relative_to(ROOT)),'sha256_before':hashlib.sha256(baseline).hexdigest(),'sha256_after':hashlib.sha256(path.read_bytes()).hexdigest(),'refs':changed,'non_model_ast_unchanged':True})
    out=ROOT/'validation/3d_update_2026-10-07.json';out.write_text(json.dumps(audit,indent=2),encoding='utf8');print(json.dumps(audit,indent=2))

if __name__=='__main__':main()
