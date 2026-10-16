"""Verify the two physical RGB options and preserve all unrelated user objects."""
from pathlib import Path
import json
from kicad_sexpr import parse, one, children

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'validation/rgb_upgrade_backup'
NETS = {'1': 'RGB_R_K', '2': '+5V', '3': 'RGB_G_K', '4': 'RGB_B_K'}


def main():
    checks = []

    def check(condition, message):
        if not condition:
            raise AssertionError(message)
        checks.append(message)

    def ref_of(item):
        return next(p[2] for p in children(item, 'property') if p[1] == 'Reference')

    for folder, ref, sch, pcb in [
        (ROOT, 'D2', 'data_status.kicad_sch', 'NM27C512_Dumper.kicad_pcb'),
        (ROOT / 'Dumper-Lite', 'D1', 'NM27C512_Dumper_Lite.kicad_sch', 'NM27C512_Dumper_Lite.kicad_pcb'),
    ]:
        fp = parse((folder / 'ProjectFootprints.pretty/RGB_CA_5050_or_THT5.kicad_mod').read_text())
        pads = children(fp, 'pad')
        check(len(pads) == 10, f'{ref}: six SMD lands plus four THT lands')
        # Manufacturer pin positions, not the logical 1R/2A/3G/4B convention.
        smd = {(round(float(one(p,'at')[1]),3), round(float(one(p,'at')[2]),3)): p
               for p in pads if p[2] == 'smd'}
        expected = {(2.4,1.6):'1', (2.4,0.0):'3', (2.4,-1.6):'4',
                    (-2.4,-1.6):'2', (-2.4,0.0):'2', (-2.4,1.6):'2'}
        check(set(smd) == set(expected), f'{ref}: KAAF recommended p7 row pitch and horizontal gap')
        for pos, number in expected.items():
            check(smd[pos][1] == number, f'{ref}: KAAF land {pos} has logical pad {number}')
            check(list(map(float,one(smd[pos],'size')[1:])) == [2.2,1.1], f'{ref}: SMD land size 2.2x1.1')
        tht = sorted((p for p in pads if p[2] == 'thru_hole'), key=lambda p:float(one(p,'at')[1]))
        check([str(p[1]) for p in tht] == ['1','2','4','3'], f'{ref}: THT physical 1R/2A/3B/4G')
        check(all(abs(float(one(tht[i+1],'at')[1])-float(one(tht[i],'at')[1])-1.27)<1e-6
                  for i in range(3)), f'{ref}: THT lead pitch 1.27mm')
        check(all(float(one(p,'drill')[1]) == 0.9 for p in tht), f'{ref}: four 0.9mm drilled holes')
        check(abs(sum(float(one(p,'at')[1]) for p in tht)/4-8.5)<1e-6,
              f'{ref}: mount centers 8.5mm apart, no overlapping lands')

        current = parse((folder / pcb).read_text())
        original = parse((BACKUP / (folder / pcb).relative_to(ROOT)).read_text())
        led = next(f for f in children(current,'footprint') if ref_of(f) == ref)
        old = next(f for f in children(original,'footprint') if ref_of(f) == ref)
        check(led[1] == 'ProjectFootprints:RGB_CA_5050_or_THT5', f'{ref}: combined footprint installed on PCB')
        check(one(led,'uuid') == one(old,'uuid'), f'{ref}: existing PCB object identity retained')
        check(one(led,'path') == one(old,'path'), f'{ref}: schematic link retained')
        for p in children(led,'pad'):
            check(one(p,'net')[1] == NETS[str(p[1])], f'{ref}: installed PCB pad {p[1]} carries {NETS[str(p[1])]}')
        check([f for f in children(current,'footprint') if ref_of(f)!=ref]
              == [f for f in children(original,'footprint') if ref_of(f)!=ref],
              f'{ref}: every unrelated PCB footprint/placement/property retained')
        check([x for x in current if not (isinstance(x,list) and x[0]=='footprint')]
              == [x for x in original if not (isinstance(x,list) and x[0]=='footprint')],
              f'{ref}: tracks/vias/zones/outline/settings retained')
        now_sch = parse((folder / sch).read_text())
        old_sch = parse((BACKUP / (folder / sch).relative_to(ROOT)).read_text())
        check([s for s in children(now_sch,'symbol') if ref_of(s)!=ref]
              == [s for s in children(old_sch,'symbol') if ref_of(s)!=ref],
              f'{ref}: every unrelated schematic component retained')
        for tag in ['wire','global_label','junction','no_connect','label']:
            check(children(now_sch,tag) == children(old_sch,tag), f'{ref}: existing schematic {tag} unchanged')
    (ROOT / 'validation/rgb_mount_audit.json').write_text(json.dumps({'passed_checks':len(checks),'checks':checks},indent=2)+'\n')
    print(f'RGB mounting audit: {len(checks)} checks passed; both existing boards and schematics preserved.')


if __name__ == '__main__':
    main()
