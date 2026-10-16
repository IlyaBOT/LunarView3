"""Reload delivered PCB files and verify placement against the saved snapshots.

Run with KiCad's bundled Python. This audits files without modifying boards.
"""
from pathlib import Path
import hashlib
import json
import pcbnew as k
from kicad_sexpr import parse, children, one
from place_lite_board import electrical_signature, PLACEMENT, ORIGIN

ROOT = Path(__file__).resolve().parents[1]
LITE = ROOT / 'Dumper-Lite'
OUT = LITE / 'validation'


def main():
    checks = []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        checks.append(message)

    audit = json.loads((OUT / 'placement_audit.json').read_text())
    path = LITE / 'NM27C512_Dumper_Lite.kicad_pcb'
    board = k.LoadBoard(str(path))
    original = k.LoadBoard(str(ROOT / audit['backup']))
    signature = json.loads(json.dumps(electrical_signature(board)))
    source = json.loads(json.dumps(electrical_signature(original)))
    expected = audit['electrical_signature_after']
    check(hashlib.sha256((ROOT / audit['backup']).read_bytes()).hexdigest() == audit['source_sha256'],
          'Original Lite snapshot hash verified')
    check(hashlib.sha256(path.read_bytes()).hexdigest() == audit['published_sha256'],
          'Published Lite hash verified')
    check(source == audit['electrical_signature_before'], 'Snapshot electrical signature verified')
    check(set(expected) == set(source) == set(PLACEMENT), 'All 39 original electrical components retained')
    for ref in source:
        check(signature[ref] == expected[ref], f'{ref}: delivered UUID/value/library/pad geometry and nets match expected')
        check(signature[ref]['uuid'] == source[ref]['uuid']
              and signature[ref]['library_id'] == source[ref]['library_id']
              and [p[:3] for p in signature[ref]['pads']] == [p[:3] for p in source[ref]['pads']],
              f'{ref}: original footprint and pad UUIDs/numbers/net names retained')
    footprints = {f.GetReference(): f for f in board.GetFootprints()}
    check(set(footprints) == set(source) | {'H1', 'H2', 'H3', 'H4'}, 'Only four mechanical footprints added')
    for ref, (x, y, angle) in PLACEMENT.items():
        fp = footprints[ref]
        actual = [k.ToMM(fp.GetPosition().x), k.ToMM(fp.GetPosition().y)]
        check(all(abs(a - b) < 1e-5 for a, b in zip(actual, [ORIGIN[0]+x, ORIGIN[1]+y]))
              and abs((fp.GetOrientationDegrees()-angle+180) % 360 - 180) < 1e-5,
              f'{ref}: expected placement and rotation verified')
        check(fp.GetLayer() == k.F_Cu, f'{ref}: component on front copper')
    for ref, xy in zip(['H1', 'H2', 'H3', 'H4'], [(54.5,54.5),(135.5,54.5),(54.5,105.5),(135.5,105.5)]):
        fp = footprints[ref]
        check(tuple(fp.GetPosition()) == tuple(k.VECTOR2I(k.FromMM(xy[0]),k.FromMM(xy[1])))
              and fp.IsBoardOnly() and len(list(fp.Pads())) == 1,
              f'{ref}: board-only mounting hole position verified')
        pad = next(iter(fp.Pads()))
        check(pad.GetAttribute() == k.PAD_ATTRIB_NPTH
              and tuple(pad.GetDrillSize()) == (k.FromMM(3.2),k.FromMM(3.2)),
              f'{ref}: 3.2mm unplated drill verified')
    edges = [d for d in board.GetDrawings() if d.GetLayer() == k.Edge_Cuts]
    check(len(edges) == 8, 'Eight outline segments/arcs retained')
    check(len(board.GetTracks()) == 0 and board.GetAreaCount() == 0, 'No tracks/vias or copper zones introduced')
    nets = {'1':'RGB_R_K','2':'+5V','3':'RGB_G_K','4':'RGB_B_K'}
    for folder, ref, filename in [(ROOT,'D2','NM27C512_Dumper.kicad_pcb'),(LITE,'D1',path.name)]:
        pcb = k.LoadBoard(str(folder / filename))
        rgb = next(f for f in pcb.GetFootprints() if f.GetReference() == ref)
        check(len(list(rgb.Pads())) == 10 and all(p.GetNetname() == nets[p.GetNumber()] for p in rgb.Pads()),
              f'{ref}: all ten RGB lands have correct nets')
        tht = [p for p in rgb.Pads() if p.GetAttribute() == k.PAD_ATTRIB_PTH]
        check(len(tht) == 4 and all(tuple(p.GetSize()) == (k.FromMM(1.11),k.FromMM(1.8))
              and tuple(p.GetDrillSize()) == (k.FromMM(.9),k.FromMM(.9))
              and p.GetLocalClearance() == k.FromMM(.15) for p in tht),
              f'{ref}: corrected THT lands, original drills and local clearance verified')
        module = parse((folder / 'ProjectFootprints.pretty/RGB_CA_5050_or_THT5.kicad_mod').read_text())
        lands = [p for p in children(module,'pad') if p[2] == 'thru_hole']
        check(len(lands) == 4 and all(list(map(float,one(p,'size')[1:])) == [1.11,1.8]
              and float(one(p,'drill')[1]) == .9 and float(one(p,'clearance')[1]) == .15 for p in lands),
              f'{ref}: project library geometry matches delivered PCB')
    full = parse((ROOT / 'NM27C512_Dumper.kicad_pcb').read_text())
    prior_full = parse((OUT / 'placement_backup/Full_before_RGB_land_correction.kicad_pcb').read_text())

    def ref_of(fp):
        return next(p[2] for p in children(fp,'property') if p[1] == 'Reference')

    check([f for f in children(full,'footprint') if ref_of(f) != 'D2']
          == [f for f in children(prior_full,'footprint') if ref_of(f) != 'D2'],
          'All 142 unrelated Stage 2 footprints and placement objects preserved')
    check([x for x in full if not (isinstance(x,list) and x[0] == 'footprint')]
          == [x for x in prior_full if not (isinstance(x,list) and x[0] == 'footprint')],
          'Stage 2 non-footprint objects and settings preserved')
    drc = json.loads((OUT / 'drc_placement.json').read_text())
    check(not drc['violations'], 'Saved-board DRC: zero violations')
    check(not drc['schematic_parity'], 'Saved-board DRC: zero schematic parity issues')
    check(len(drc['unconnected_items']) == 134, '134 unconnected items explicitly retained as unfinished routing')
    result = {'passed_checks':len(checks), 'checks':checks,
              'board_sha256':audit['published_sha256'], 'routing_complete':False}
    (OUT / 'placement_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS: {len(checks)} saved-file placement and preservation checks; 134 unconnected items remain.')


if __name__ == '__main__':
    main()
