"""Read-only summary of saved PCB geometry and 3D model references."""
from pathlib import Path
import json,sys,os
import pcbnew as k
from kicad_sexpr import parse,children,one
ROOT=Path(__file__).resolve().parents[1]
MODELS=Path('C:/Program Files/KiCad/10.0/share/kicad/3dmodels')
for folder,name in [(ROOT,'NM27C512_Dumper'),(ROOT/'Dumper-Lite','NM27C512_Dumper_Lite')]:
    path=folder/(name+'.kicad_pcb')
    board=k.LoadBoard(str(path)); tree=parse(path.read_text(encoding='utf8'))
    tracks=list(board.GetTracks()); vias=[t for t in tracks if isinstance(t,k.PCB_VIA)]
    embedded=one(tree,'embedded_files')
    embedded_names={one(f,'name')[1] for f in children(embedded,'file')} if embedded else set()
    widths=sorted({round(k.ToMM(t.GetWidth()),4) for t in tracks if not isinstance(t,k.PCB_VIA)})
    print(name,'footprints',len(list(board.GetFootprints())),'tracks',len(tracks)-len(vias),'vias',len(vias),'zones',board.GetAreaCount(),'widths',widths)
    print('VIA SIZES',sorted({(k.ToMM(v.GetWidth(k.F_Cu)),k.ToMM(v.GetDrillValue())) for v in vias}))
    for fp in children(tree,'footprint'):
        ref=next(p[2] for p in children(fp,'property') if p[1]=='Reference')
        models=children(fp,'model')
        for model in models:
            raw=model[1]; resolved=raw.replace('${KICAD10_3DMODEL_DIR}',str(MODELS)).replace('${KIPRJMOD}',str(folder))
            exists=raw.removeprefix('kicad-embed://') in embedded_names if raw.startswith('kicad-embed://') else Path(resolved).is_file()
            if not exists: print('MISSING',ref,fp[1],raw)
        if not models and not ref.startswith('H'): print('NO MODEL',ref,fp[1])
