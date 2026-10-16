"""Install RGB mounting alternatives without regenerating user-edited projects.

One four-pin common-anode schematic node maps to ten copper pads: six for
KAAF-5050RGBS-13 and four for WP154A4SEJ3VBDZGW/CA. Populate one body only.
The PCB is still unrouted: both pad sets must be connected when routing it.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import math
import shutil
import uuid
from kicad_sexpr import Atom as A, node as N, one, children, parse, dump
import generate_schematic as g

ROOT = Path(__file__).resolve().parents[1]
LITE = ROOT / ('Dumper-Lite' if (ROOT / 'Dumper-Lite').exists() else 'lite')
LIB_ID = 'ProjectSymbols:RGB_CA_DualMount'
FP_ID = 'ProjectFootprints:RGB_CA_5050_or_THT5'
VALUE = 'RGB CA / 5050 OR THT5'
SMD_URL = 'https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KAAF-5050RGBS-13%28Ver.3B%29.pdf'
THT_URL = 'https://www.kingbrightusa.com/images/catalog/SPEC/WP154A4SEJ3VBDZGW-CA.pdf'
NETS = {'1': 'RGB_R_K', '2': '+5V', '3': 'RGB_G_K', '4': 'RGB_B_K'}


def write_tree(path, tree):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('(' + dump(tree[0]) + '\n' + '\n'.join('  ' + dump(item)
                    for item in tree[1:]) + '\n)\n', encoding='utf8')


def effects(size=0.8, hidden=False):
    result = N('effects', N('font', N('size', size, size), N('thickness', 0.12)))
    if hidden:
        result.append(N('hide', A('yes')))
    return result


def footprint():
    fp = N('footprint', FP_ID.split(':')[1], N('version', 20260206),
           N('generator', 'pcbnew'), N('layer', 'F.Cu'),
           N('descr', 'Populate ONE ONLY: Kingbright KAAF-5050RGBS-13 5x5mm SMD OR '
                     'WP154A4SEJ3VBDZGW/CA 5mm THT. Logical pads 1R/2A/3G/4B. '
                     'SMD physical 1R/2G/3B/4A/5A/6A; THT physical 1R/2A/3B/4G.'),
           N('tags', 'RGB common anode 5050 THT optional assembly'),
           N('attr', A('through_hole')))
    fp.append(N('property', 'Reference', 'REF**', N('at', 4, -4.3, 0),
                N('layer', 'F.SilkS'), effects(0.9)))
    fp.append(N('property', 'Value', 'RGB CA 5050 or THT5', N('at', 4, 6.5, 0),
                N('layer', 'F.Fab'), N('hide', A('yes')), effects(0.8)))

    def line(x1, y1, x2, y2, layer='F.SilkS'):
        fp.append(N('fp_line', N('start', x1, y1), N('end', x2, y2),
                    N('stroke', N('width', 0.12 if layer == 'F.SilkS' else 0.05),
                      N('type', A('solid'))), N('layer', layer)))

    # Manufacturer recommended lands, datasheet p7: 2.2 x 1.1, 2.6 mm gap,
    # row pitch 1.6 mm. Top-view pin numbering is from the p1 drawing.
    smd = [(3, 4, 2.4, -1.6), (2, 3, 2.4, 0), (1, 1, 2.4, 1.6),
           (4, 2, -2.4, -1.6), (5, 2, -2.4, 0), (6, 2, -2.4, 1.6)]
    for physical, logical, x, y in smd:
        fp.append(N('pad', str(logical), A('smd'), A('rect'), N('at', x, y),
                    N('size', 2.2, 1.1), N('layers', 'F.Cu', 'F.Paste', 'F.Mask')))
        fp.append(N('fp_text', A('user'), f'S{physical}', N('at', x / 2, y, 0),
                    N('layer', 'F.Fab'), effects(0.45)))
    # Datasheet p1: 1.27 mm pitch and 0.9 mm drilled holes. Two mount centers
    # are 8.5 mm apart. THT 3=B and 4=G are deliberately remapped to 4 and 3.
    for physical, logical, colour in [(1, 1, 'R'), (2, 2, '+'), (3, 4, 'B'), (4, 3, 'G')]:
        x = 6.595 + (physical - 1) * 1.27
        fp.append(N('pad', str(logical), A('thru_hole'), A('rect' if physical == 1 else 'oval'),
                    N('at', x, 0), N('size', 1.11, 1.8), N('drill', 0.9),
                    N('layers', '*.Cu', '*.Mask'), N('clearance', 0.15)))
        fp.append(N('fp_text', A('user'), colour, N('at', x, -1.55, 0),
                    N('layer', 'F.SilkS'), effects(0.8)))
        fp.append(N('fp_text', A('user'), f'T{physical}', N('at', x, 1.5, 0),
                    N('layer', 'F.Fab'), effects(0.45)))
    for y in [-2.65, 2.65]:
        line(-2.65, y, 2.65, y)
    for x in [-2.65, 2.65]:
        line(x, -2.65, x, -2.4)
        line(x, 2.4, x, 2.65)
    # SMD manufacturer pin 1 is the lower-right cathode; the package
    # chamfer is on the opposite lower-left corner, next to pin 6.
    fp.append(N('fp_circle', N('center', 3.25, 2.85), N('end', 3.40, 2.85),
                N('stroke', N('width', 0.12), N('type', A('solid'))),
                N('fill', A('solid')), N('layer', 'F.SilkS')))
    # The SMD package's chamfered corner is next to manufacturer pin 6.
    points = [(-2.5, -2.5), (2.5, -2.5), (2.5, 2.5), (-1.9, 2.5), (-2.5, 1.9), (-2.5, -2.5)]
    for start, end in zip(points, points[1:]):
        line(*start, *end, 'F.Fab')
    for layer, radius in [('F.SilkS', 3.05), ('F.Fab', 2.95)]:
        fp.append(N('fp_circle', N('center', 8.5, 0), N('end', 8.5 + radius, 0),
                    N('stroke', N('width', 0.12 if layer == 'F.SilkS' else 0.1),
                      N('type', A('solid'))), N('fill', A('none')), N('layer', layer)))
    for text, x, y in [('SMD 5050', 0, -3.6), ('THT 5mm', 8.5, 3.7), ('ONE ONLY', 4, 5.0)]:
        fp.append(N('fp_text', A('user'), text, N('at', x, y, 0),
                    N('layer', 'F.SilkS'), effects(0.8)))
    corners = [(-3.75, -3.25), (11.7, -3.25), (11.7, 3.25), (-3.75, 3.25), (-3.75, -3.25)]
    for start, end in zip(corners, corners[1:]):
        line(*start, *end, 'F.CrtYd')
    return fp


def symbol():
    s = g.standard('LED:APFA3010')
    old_name = s[1].split(':')[-1]
    s[1] = LIB_ID.split(':')[1]
    for sub in children(s, 'symbol'):
        sub[1] = sub[1].replace(old_name, s[1])
    for prop in children(s, 'property'):
        if prop[1] == 'Value': prop[2] = 'RGB_CA_DualMount'
        if prop[1] == 'Footprint': prop[2] = FP_ID
        if prop[1] == 'Datasheet': prop[2] = SMD_URL
        if prop[1] == 'Description': prop[2] = 'Common-anode RGB; populate ONE of the two physical mounting options'
        if prop[1] == 'ki_fp_filters': prop[2] = 'RGB_CA_5050_or_THT5'
    return s


def backup(path, folder):
    target = folder / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(path, target)


def install_library(folder, sym, fp):
    lib_path = folder / 'ProjectSymbols.kicad_sym'
    lib = parse(lib_path.read_text(encoding='utf8'))
    lib[:] = [x for x in lib if not (isinstance(x, list) and x[0] == 'symbol' and x[1] == sym[1])]
    lib.append(copy.deepcopy(sym))
    write_tree(lib_path, lib)
    write_tree(folder / 'ProjectFootprints.pretty' / (fp[1] + '.kicad_mod'), fp)
    table_path = folder / 'fp-lib-table'
    table = parse(table_path.read_text(encoding='utf8'))
    table[:] = [x for x in table if not (isinstance(x, list) and x[0] == 'lib'
                and one(x, 'name')[1] == 'ProjectFootprints')]
    table.append(N('lib', N('name', 'ProjectFootprints'), N('type', 'KiCad'),
                   N('uri', '${KIPRJMOD}/ProjectFootprints.pretty'), N('options', ''),
                   N('descr', 'RGB SMD 5050 / THT5 alternative mounting')))
    write_tree(table_path, table)


def patch_schematic(path, ref, sym):
    tree = parse(path.read_text(encoding='utf8'))
    inst = next(s for s in children(tree, 'symbol') if any(p[1] == 'Reference' and p[2] == ref
                    for p in children(s, 'property')))
    before = copy.deepcopy(tree)
    one(inst, 'lib_id')[1] = LIB_ID
    for p in children(inst, 'property'):
        if p[1] == 'Value': p[2] = VALUE
        if p[1] == 'Footprint': p[2] = FP_ID
        if p[1] == 'Datasheet': p[2] = SMD_URL
    libs = one(tree, 'lib_symbols')
    embedded = copy.deepcopy(sym)
    embedded[1] = LIB_ID
    if not any(s[1] == LIB_ID for s in children(libs, 'symbol')):
        libs.append(embedded)
    for note in children(tree, 'text'):
        if 'D2 Kingbright APFA3010' in note[1]:
            note[1] = note[1].replace('D2 Kingbright APFA3010: pad1 R, pad2 common A (+5V), pad3 G, pad4 B.',
                        'D2: combined SMD 5050 / THT5 footprint. Populate ONE ONLY; pads 1R/2A/3G/4B.')
    # Every wire/label and every other placed component stays byte-for-byte
    # identical as a parsed object, including user changes made in KiCad.
    for tag in ['wire', 'global_label', 'label', 'junction', 'no_connect']:
        assert children(tree, tag) == children(before, tag), tag
    assert [x for x in children(tree, 'symbol') if x is not inst] == [x for x in children(before, 'symbol')
        if not any(p[1] == 'Reference' and p[2] == ref for p in children(x, 'property'))]
    write_tree(path, tree)


def bbox(fp, anchor=None):
    at = one(fp, 'at')
    ax, ay = anchor if anchor is not None else (float(at[1]), float(at[2]))
    angle = math.radians(float(at[3]) if len(at) > 3 else 0)
    points = []
    for obj in fp:
        if isinstance(obj, list) and str(obj[0]).startswith('fp_') and one(obj, 'layer') and one(obj, 'layer')[1] == 'F.CrtYd':
            for coord in ['start', 'end', 'center', 'mid']:
                pos = one(obj, coord)
                if pos:
                    x, y = float(pos[1]), float(pos[2])
                    points.append((ax + x*math.cos(angle) + y*math.sin(angle),
                                   ay - x*math.sin(angle) + y*math.cos(angle)))
    if not points:
        points = [(ax-3, ay-3), (ax+3, ay+3)]
    return min(x for x,y in points), min(y for x,y in points), max(x for x,y in points), max(y for x,y in points)


def patch_board(path, ref, fp):
    tree = parse(path.read_text(encoding='utf8'))
    before = copy.deepcopy(tree)
    old = next(f for f in children(tree, 'footprint') if any(p[1] == 'Reference' and p[2] == ref
                for p in children(f, 'property')))
    new = copy.deepcopy(fp)
    new[1] = FP_ID
    new[:] = [x for x in new if not (isinstance(x, list) and x[0] in ['version', 'generator', 'generator_version'])]
    for key in ['uuid', 'at', 'path', 'sheetname', 'sheetfile', 'locked', 'exclude_from_sim',
                'in_bom', 'on_board', 'dnp', 'property']:
        if key == 'property':
            continue
        item = one(old, key)
        if item:
            new.append(copy.deepcopy(item))
    for p in children(new, 'property'):
        if p[1] == 'Reference': p[2] = ref
        if p[1] == 'Value': p[2] = VALUE
    old_nets = {str(p[1]): one(p, 'net') for p in children(old, 'pad')}
    for pad in children(new, 'pad'):
        assert old_nets[str(pad[1])][1] == NETS[str(pad[1])]
        pad.append(copy.deepcopy(old_nets[str(pad[1])]))
    for item in new[1:]:
        if isinstance(item, list) and item[0] not in ['attr', 'at', 'path', 'sheetname', 'sheetfile',
                                                 'uuid', 'layer', 'descr', 'tags', 'locked']:
            item.append(N('uuid', str(uuid.uuid4())))
    others = [f for f in children(tree, 'footprint') if f is not old]
    old_at = one(old, 'at')
    original = (float(old_at[1]), float(old_at[2]))
    obstacle_boxes = [bbox(f) for f in others]
    candidates = [(original[0]+dx, original[1]+dy)
                  for dx in range(-30, 31, 2) for dy in range(-30, 31, 2)]
    candidates.sort(key=lambda p:(p[0]-original[0])**2+(p[1]-original[1])**2)
    def clear(point):
        x1,y1,x2,y2 = bbox(new, point)
        return all(x2+0.3 < a or c+0.3 < x1 or y2+0.3 < b or d+0.3 < y1
                   for a,b,c,d in obstacle_boxes)
    position = next(p for p in candidates if clear(p))
    one(new, 'at')[1:3] = list(position)
    tree[tree.index(old)] = new
    assert [f for f in children(tree, 'footprint') if f is not new] == [f for f in children(before, 'footprint')
        if not any(p[1] == 'Reference' and p[2] == ref for p in children(f, 'property'))]
    assert [x for x in tree[1:] if not (isinstance(x,list) and x[0]=='footprint')] == [x for x in before[1:]
        if not (isinstance(x,list) and x[0]=='footprint')]
    write_tree(path, tree)
    return {'board': str(path.relative_to(ROOT)), 'ref': ref, 'old_at': original,
            'new_at': position, 'other_footprints_preserved': len(others),
            'existing_segments_preserved': len(children(tree, 'segment'))}


def main():
    backup_dir = ROOT / 'validation' / 'rgb_upgrade_backup'
    projects = [(ROOT, 'data_status.kicad_sch', 'NM27C512_Dumper.kicad_pcb', 'D2'),
                (LITE, 'NM27C512_Dumper_Lite.kicad_sch', 'NM27C512_Dumper_Lite.kicad_pcb', 'D1')]
    for folder, sch, pcb, ref in projects:
        for filename in [sch, pcb, 'ProjectSymbols.kicad_sym', 'fp-lib-table', 'validation/bom.json']:
            backup(folder / filename, backup_dir)
    sym, fp = symbol(), footprint()
    results = []
    for folder, sch, pcb, ref in projects:
        install_library(folder, sym, fp)
        patch_schematic(folder / sch, ref, sym)
        result = patch_board(folder / pcb, ref, fp)
        saved = parse((backup_dir / (folder / pcb).relative_to(ROOT)).read_text(encoding='utf8'))
        first = next(f for f in children(saved, 'footprint') if any(
            p[1] == 'Reference' and p[2] == ref for p in children(f, 'property')))
        result['old_at'] = list(map(float, one(first, 'at')[1:3]))
        results.append(result)
        bom_path = folder / 'validation' / 'bom.json'
        bom = json.loads(bom_path.read_text())
        part = next(p for p in bom if p['ref'] == ref)
        part.update({'value': VALUE, 'symbol': LIB_ID, 'footprint': FP_ID})
        bom_path.write_text(json.dumps(bom, indent=2) + '\n', encoding='utf8')
        csv_path = folder / ('BOM.csv' if folder == LITE else 'validation/BOM.csv')
        with csv_path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['ref', 'value', 'footprint'])
            writer.writeheader()
            writer.writerows({k:p[k] for k in writer.fieldnames} for p in bom)
    (ROOT / 'validation' / 'rgb_upgrade.json').write_text(json.dumps(results, indent=2)+'\n')
    for result in results:
        print(f"{result['board']}: {result['ref']} -> dual mount; "
              f"{result['other_footprints_preserved']} other footprints preserved")


if __name__ == '__main__':
    main()
