"""Read-only hole inventory for home assembly of the user's routed Lite PCB."""
from pathlib import Path
import csv,json
from collections import Counter
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Dumper-Lite/validation'
b=k.LoadBoard(str(ROOT/'Dumper-Lite/NM27C512_Dumper_Lite.kicad_pcb'))
fps=[fp for fp in b.GetFootprints() if fp.GetReference() and not fp.GetReference().startswith('H')]
tracks=[t for t in b.GetTracks() if not isinstance(t,k.PCB_VIA)]
vias=sorted((t for t in b.GetTracks() if isinstance(t,k.PCB_VIA)),key=lambda v:(v.GetPosition().y,v.GetPosition().x))
with (OUT/'vias_for_hand_assembly.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Index','Net','X_mm','Y_mm','Pad_diameter_mm','Drill_mm','Footprint_bbox_candidates'])
    for i,v in enumerate(vias,1):
        candidates=[fp.GetReference() for fp in fps if fp.GetBoundingBox(False,False).Contains(v.GetPosition())]
        w.writerow([i,v.GetNetname(),k.ToMM(v.GetPosition().x),k.ToMM(v.GetPosition().y),k.ToMM(v.GetWidth(k.F_Cu)),k.ToMM(v.GetDrillValue()),';'.join(candidates)])
rows=[]
for fp in fps:
    for pad in fp.Pads():
        if pad.GetAttribute()!=k.PAD_ATTRIB_PTH or not pad.GetNetCode():continue
        layers={t.GetLayerName() for t in tracks if t.GetNetCode()==pad.GetNetCode() and (pad.HitTest(t.GetStart()) or pad.HitTest(t.GetEnd()))}
        if {'F.Cu','B.Cu'}<=layers:
            rows.append([fp.GetReference(),pad.GetNumber(),pad.GetNetname(),k.ToMM(pad.GetPosition().x),k.ToMM(pad.GetPosition().y),k.ToMM(pad.GetDrillSize().x),'F.Cu+B.Cu'])
with (OUT/'pth_two_sided_connections.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Ref','Pad','Net','X_mm','Y_mm','Drill_mm','Tracks_touching_pad']);w.writerows(rows)
result={'vias':len(vias),'via_sizes':{str(size):n for size,n in Counter((k.ToMM(v.GetWidth(k.F_Cu)),k.ToMM(v.GetDrillValue())) for v in vias).items()},'pth_with_tracks_on_both_sides':len(rows),'pth_refs':dict(Counter(r[0] for r in rows)), 'note':'Footprint bounding boxes are candidates only; inspect Fab layers. PTH contact detection uses track endpoint hit tests.'}
(OUT/'hand_assembly_summary.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
