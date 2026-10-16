"""Place the saved Lite PCB with KiCad's own geometry API.

Run with KiCad's bundled Python. Outputs a review candidate, never overwrites
an open board. All electrical footprints, pad identities and nets are retained.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import pcbnew as k
from kicad_sexpr import parse, children

ROOT = Path(__file__).resolve().parents[1]
LITE = ROOT / 'Dumper-Lite'
SOURCE = LITE / 'NM27C512_Dumper_Lite.kicad_pcb'
OUT = LITE / 'validation'
ORIGIN = (50.0, 50.0)
SIZE = (90.0, 60.0)

# Coordinates are relative to the board's upper-left corner, in millimetres.
# SO16 outputs face the socket; the high-address register is above the low one.
PLACEMENT = {
    'U1': (39,23,0), 'U2': (58,34,180), 'U3': (58,19,180),
    'U4': (22,21,0), 'U5': (70,12,0),
    'J1': (3,32,-90), 'J2': (18,38,0),
    'Y1': (35.56,32,0), 'SW1': (32.5,41.25,0),
    'D1': (47,51,0), 'D2': (5,14,0), 'D3': (5,23,0), 'D4': (44,39.5,0),
    'C1': (9.5,31,90), 'C2': (27.5,16,0), 'C3': (16,22,90),
    'C4': (32,22.2,90), 'C5': (32,25.6,90), 'C6': (46.5,25.8,90),
    'C7': (53,39,90), 'C8': (53,24,90), 'C9': (88,13,90),
    'C10': (46.5,22.3,90), 'C11': (34.8,37.5,0), 'C12': (40,37.5,0),
    'C13': (29,19,0),
    'R1': (42.5,44.5,90), 'R2': (88,32.5,90), 'R3': (88,27.5,90),
    'R4': (46.5,30,0), 'R5': (44,43,-90), 'R6': (47.5,43,-90),
    'R7': (51,43,-90), 'R8': (15.5,13.05,180), 'R9': (15.5,18.05,180),
    'R10': (5,17,0), 'R11': (5,26,0), 'Q1': (10.5,14,180), 'Q2': (10.5,19,180),
}
REF_POS = {
    'U1': (39,16.8), 'U2': (58,26.9), 'U3': (58,11.9), 'U4': (22,13.9),
    'U5': (77.62,9), 'J1': (6.7,35.8), 'J2': (19.27,35),
    'Y1': (30,32), 'SW1': (35.75,38.7), 'D1': (51,46.7),
    'D2': (5,12.3), 'D3': (5,21.3), 'D4': (44,37.3),
    'C3': (13.9,22), 'C4': (29.9,22.2), 'C5': (29.9,25.6),
    'C6': (49,25.8), 'C7': (50.7,39), 'C8': (50.7,24), 'C9': (88,10.6),
    'C10': (49,22.3), 'C11': (34.8,35.7), 'C12': (40,35.7), 'C13': (29,17.3),
    'R1': (42.5,47.1), 'R5': (44,45.4), 'R6': (47.5,45.4), 'R7': (51,45.4),
    'R10': (7.8,17), 'R11': (7.8,26),
    'Q2': (13.8,19.5),
}

def mm(x):
    return k.FromMM(x)

def point(x, y):
    return k.VECTOR2I(mm(ORIGIN[0]+x), mm(ORIGIN[1]+y))

def electrical_signature(board):
    return {f.GetReference(): {
        'uuid': f.m_Uuid.AsString(), 'value': f.GetValue(),
        'library_id': f.GetFPID().GetUniStringLibId(),
        'pads': sorted((p.m_Uuid.AsString(), p.GetNumber(), p.GetNetname(),
                        p.GetAttribute(), p.GetShape(), tuple(p.GetSize()), p.GetDrillShape(),
                        tuple(p.GetDrillSize()), p.GetLayerSet().FmtHex()) for p in f.Pads())
    } for f in board.GetFootprints()}

def shape(board, kind, start, end, mid=None):
    obj = k.PCB_SHAPE(board)
    obj.SetLayer(k.Edge_Cuts)
    obj.SetWidth(mm(0.05))
    obj.SetShape(kind)
    if mid is None:
        obj.SetStart(point(*start)); obj.SetEnd(point(*end))
    else:
        obj.SetArcGeometry(point(*start), point(*mid), point(*end))
    board.Add(obj)

def text(board, value, x, y, size=.9, angle=0, justify=None):
    obj = k.PCB_TEXT(board)
    obj.SetText(value); obj.SetPosition(point(x,y)); obj.SetLayer(k.F_SilkS)
    size=max(.8,size)
    obj.SetTextSize(k.VECTOR2I(mm(size), mm(size)))
    obj.SetTextThickness(mm(.12))
    obj.SetTextAngle(k.EDA_ANGLE(angle, k.DEGREES_T))
    if justify is not None:
        obj.SetHorizJustify(justify)
    board.Add(obj)

def main():
    OUT.mkdir(exist_ok=True)
    data = SOURCE.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    backup = OUT / 'placement_backup' / f'Lite_before_placement_{digest[:12]}.kicad_pcb'
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():
        shutil.copy2(SOURCE, backup)
    board = k.LoadBoard(str(SOURCE))
    assert len(board.GetTracks()) == 0 and board.GetAreaCount() == 0, 'Routed board needs another workflow'
    assert len(board.GetDrawings()) == 0, 'Preserve and integrate an existing outline explicitly'
    before = electrical_signature(board)
    assert set(before) == set(PLACEMENT), f'Unexpected current components: {set(before)^set(PLACEMENT)}'
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        x,y,angle = PLACEMENT[ref]
        fp.SetPosition(point(x,y)); fp.SetOrientationDegrees(angle)
        label = fp.Reference()
        label.SetTextAngle(k.EDA_ANGLE(0, k.DEGREES_T))
        label.SetTextSize(k.VECTOR2I(mm(.85),mm(.85))); label.SetTextThickness(mm(.12))
        label.SetVisible(True); label.SetLayer(k.F_SilkS)
        box = fp.GetBoundingBox(False,False)
        if ref in REF_POS:
            label.SetPosition(point(*REF_POS[ref]))
        else:
            label.SetPosition(k.VECTOR2I(fp.GetPosition().x, box.GetY()-mm(1.15)))
        fp.Value().SetVisible(False)
        # Retain the value in the file/Fab layer for inspection, hide it on the board.
    assert electrical_signature(board) == before, 'Electrical footprint data changed'
    # Repair the pre-existing narrow RGB THT rings without reducing the 0.9mm
    # manufacturer-recommended drill. 1.11mm lands give 0.105mm annular rings,
    # 0.16mm between neighbouring lands; the local pad clearance is 0.15mm.
    rgb = next(f for f in board.GetFootprints() if f.GetReference() == 'D1')
    for pad in rgb.Pads():
        if pad.GetAttribute() == k.PAD_ATTRIB_PTH:
            pad.SetSize(k.VECTOR2I(mm(1.11),mm(1.8)))
            pad.SetLocalClearance(mm(.15))
    labels = {obj.GetText():obj for obj in rgb.GraphicalItems() if isinstance(obj,k.PCB_TEXT)}
    for value,dx,dy in [('SMD 5050',0,-3.6),('THT 5mm',8.5,3.7),('ONE ONLY',4,5)]:
        obj=labels.get(value)
        if obj is None:
            obj=k.PCB_TEXT(rgb); obj.SetText(value); rgb.Add(obj)
        obj.SetLayer(k.F_SilkS); obj.SetPosition(point(47+dx,51+dy))
        obj.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T))
        obj.SetTextSize(k.VECTOR2I(mm(.8),mm(.8))); obj.SetTextThickness(mm(.12))
    for obj in rgb.GraphicalItems():
        if isinstance(obj,k.PCB_TEXT) and obj.GetLayer() == k.F_SilkS:
            obj.SetTextSize(k.VECTOR2I(mm(.8),mm(.8)))
    rgb.GetField('Datasheet').SetText('https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KAAF-5050RGBS-13%28Ver.3B%29.pdf')
    schematic=parse((LITE/'NM27C512_Dumper_Lite.kicad_sch').read_text(encoding='utf8'))
    quartz=next(s for s in children(schematic,'symbol') if any(
        p[1]=='Reference' and p[2]=='Y1' for p in children(s,'property')))
    quartz_value=next(p[2] for p in children(quartz,'property') if p[1]=='Value')
    next(f for f in board.GetFootprints() if f.GetReference()=='Y1').SetValue(quartz_value)
    # Document the two intended non-electrical corrections in the expected data.
    expected=electrical_signature(board)
    for ref in before:
        assert expected[ref]['uuid']==before[ref]['uuid']
        assert expected[ref]['library_id']==before[ref]['library_id']
        assert [(p[0],p[1],p[2]) for p in expected[ref]['pads']]==[(p[0],p[1],p[2]) for p in before[ref]['pads']]
        if ref not in ['D1','Y1']:
            assert expected[ref]==before[ref]
    w,h = SIZE
    r=2.5
    d=r/math.sqrt(2)
    for a,b in [((r,0),(w-r,0)),((w,r),(w,h-r)),((w-r,h),(r,h)),((0,h-r),(0,r))]:
        shape(board,k.SHAPE_T_SEGMENT,a,b)
    for a,m,b in [((w-r,0),(w-r+d,r-d),(w,r)),((w,h-r),(w-r+d,h-r+d),(w-r,h)),
                  ((r,h),(r-d,h-r+d),(0,h-r)),((0,r),(r-d,r-d),(r,0))]:
        shape(board,k.SHAPE_T_ARC,a,b,m)
    library = 'C:/Program Files/KiCad/10.0/share/kicad/footprints/MountingHole.pretty'
    for i,(x,y) in enumerate([(4.5,4.5),(w-4.5,4.5),(4.5,h-4.5),(w-4.5,h-4.5)],1):
        fp = k.FootprintLoad(library,'MountingHole_3.2mm_M3')
        assert fp is not None
        fp.SetReference(f'H{i}'); fp.SetValue('M3 mounting hole')
        fp.SetAttributes(k.FP_BOARD_ONLY | k.FP_EXCLUDE_FROM_BOM | k.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetPosition(point(x,y)); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        board.Add(fp)
    text(board,'NM27C512 Dumper Lite',11,3.8,1.65,justify=k.GR_TEXT_H_ALIGN_LEFT)
    text(board,'READ-ONLY / 5 V ONLY',11,6.3,.95,justify=k.GR_TEXT_H_ALIGN_LEFT)
    text(board,'USB EPROM READER',68,3.8,.85)
    text(board,'28-PIN / DIP SOCKET',68,6.3,.7)
    for value,x,y,size in [('CH340C',22,12.3,.8),('ATmega328P',39,15.2,.8),
                         ('A8-A15',58,10.5,.7),('A0-A7',58,25.6,.7),
                         ('RX',5,10.8,.85),('TX',5,19.8,.85),('USB',3,38.7,.9),
                         ('AVR ISP',19.27,33.5,.9),('RESET',35.75,49,.95),
                         ('STATUS RGB',51,58,.8),('NM27C512 SOCKET',77.62,49.6,.9)]:
        text(board,value,x,y,size)
    for row,left,right in [(0,'MISO','+5V'),(1,'SCK','MOSI'),(2,'RST','GND')]:
        text(board,left,15,38+2.54*row,.7,justify=k.GR_TEXT_H_ALIGN_RIGHT)
        text(board,right,24,38+2.54*row,.7,justify=k.GR_TEXT_H_ALIGN_LEFT)
    candidate = OUT / 'placement_candidate.kicad_pcb'
    k.SaveBoard(str(candidate),board)
    reloaded = k.LoadBoard(str(candidate))
    actual = electrical_signature(reloaded)
    assert {ref:actual[ref] for ref in before} == expected
    assert len(reloaded.GetTracks()) == 0 and reloaded.GetAreaCount() == 0
    result = {'source_sha256':digest, 'backup':backup.relative_to(ROOT).as_posix(),
              'candidate':candidate.relative_to(ROOT).as_posix(), 'electrical_components_preserved':len(before),
              'all_electrical_pad_ids_and_nets_preserved':True, 'size_mm':SIZE,
              'rgb_THT_land_width_mm':1.11, 'rgb_THT_drill_mm':.9, 'rgb_THT_local_clearance_mm':.15,
              'metadata_corrections':[f'Y1 value aligned with schematic: {quartz_value}','D1 datasheet aligned with schematic'],
              'outline_corner_radius_mm':r, 'mounting_holes':4, 'routing_performed':False,
              'placement':PLACEMENT, 'electrical_signature_before':before, 'electrical_signature_after':expected}
    (OUT/'placement_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Candidate saved; all 39 electrical footprints and pad net assignments preserved.')

if __name__ == '__main__':
    main()
