"""Add filled GND pours only, preserving every existing non-zone PCB node."""
from pathlib import Path
import copy, hashlib, json, shutil
import pcbnew as k
from kicad_sexpr import parse, dump, children, one

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'Adapter-KR573RF5'
PCB=FOLDER/'KR573RF5_Adapter.kicad_pcb'

def non_zones(tree):
    return [n for n in tree if not(isinstance(n,list) and n and n[0]=='zone')]

def main():
    assert not (FOLDER/('~'+PCB.name+'.lck')).exists(),'Adapter PCB is open'
    source=PCB.read_bytes()
    before=parse(source.decode('utf8'))
    original_tree=copy.deepcopy(before)
    previous_audit=FOLDER/'validation'/'gnd_zones_audit.json'
    if children(before,'zone'):
        audit=json.loads(previous_audit.read_text(encoding='utf8'))
        assert hashlib.sha256(source).hexdigest()==audit['sha256_after'],'PCB changed after previous pour'
        baseline_path=ROOT/audit['backup']/PCB.name
        before=parse(baseline_path.read_text(encoding='utf8'))
        source=baseline_path.read_bytes()
    assert not children(before,'zone'),'Existing zones need manual review'
    digest=hashlib.sha256(source).hexdigest()
    backup=FOLDER/'backups'/'2026-10-07-before-gnd-zones'/digest[:12]
    backup.mkdir(parents=True,exist_ok=True)
    for p in [PCB,PCB.with_suffix('.kicad_pro'),PCB.with_suffix('.kicad_dru')]:
        dest=backup/p.name
        if not dest.exists():shutil.copy2(p,dest)
    b=k.LoadBoard(str(backup/PCB.name))
    ds=b.GetDesignSettings()
    ds.m_MinClearance=k.FromMM(0.2)
    ds.m_CopperEdgeClearance=k.FromMM(0.5)
    ds.m_HoleClearance=k.FromMM(0.25)
    ds.m_MinResolvedSpokes=2
    ground=b.FindNet('GND')
    assert ground is not None
    via=k.PCB_VIA(b)
    via.SetPosition(k.VECTOR2I(k.FromMM(61.43),k.FromMM(55.08)))
    via.SetWidth(k.FromMM(1.20))
    via.SetDrill(k.FromMM(0.60))
    via.SetViaType(k.VIATYPE_THROUGH)
    via.SetLayerPair(k.F_Cu,k.B_Cu)
    via.SetNet(ground)
    b.Add(via)
    settings={'clearance_mm':0.25,'minimum_width_mm':0.25,
              'thermal_gap_mm':0.25,'thermal_spoke_width_mm':0.30,
              'edge_inset_mm':0.55,'remove_unconnected_islands':'always'}
    for layer,label in [(k.F_Cu,'F.Cu'),(k.B_Cu,'B.Cu')]:
        z=k.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(ground)
        z.SetZoneName('GND pour '+label)
        z.SetFillMode(k.ZONE_FILL_MODE_POLYGONS)
        z.SetLocalClearance(k.FromMM(settings['clearance_mm']))
        z.SetMinThickness(k.FromMM(settings['minimum_width_mm']))
        z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(k.FromMM(settings['thermal_gap_mm']))
        z.SetThermalReliefSpokeWidth(k.FromMM(settings['thermal_spoke_width_mm']))
        z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        p=z.Outline();p.NewOutline()
        for x,y in [(50.55,50.55),(72.31,50.55),(72.31,87.55),(50.55,87.55)]:
            p.Append(k.FromMM(x),k.FromMM(y))
        b.Add(z)
    b.BuildConnectivity()
    filler=k.ZONE_FILLER(b)
    assert filler.Fill(b.Zones()),'Zone filling failed'
    scratch=ROOT/'tmp'/'rf5_gnd_zones_native.kicad_pcb'
    k.SaveBoard(str(scratch),b)
    native=parse(scratch.read_text(encoding='utf8'))
    zones=copy.deepcopy(children(native,'zone'))
    via_tree=copy.deepcopy(next(v for v in children(native,'via') if str(one(v,'uuid')[1])==str(via.m_Uuid.AsString())))
    assert len(zones)==2
    assert all(children(z,'filled_polygon') for z in zones),'Empty zone'
    after=copy.deepcopy(before)
    after.extend(zones)
    after.append(via_tree)
    assert [n for n in non_zones(after) if n is not via_tree]==non_zones(before)
    assert parse(PCB.read_text(encoding='utf8'))==original_tree,'PCB changed during preparation'
    PCB.write_text('('+dump(after[0])+'\n'+'\n'.join('  '+dump(x) for x in after[1:])+'\n)\n',encoding='utf8')
    reread=parse(PCB.read_text(encoding='utf8'))
    added_uuid=str(one(via_tree,'uuid')[1])
    preserved=[n for n in non_zones(reread) if not(isinstance(n,list) and n[0]=='via' and str(one(n,'uuid')[1])==added_uuid)]
    assert preserved==non_zones(before)
    report={'board':str(PCB.relative_to(ROOT)),'sha256_before':digest,
            'sha256_after':hashlib.sha256(PCB.read_bytes()).hexdigest(),
            'backup':str(backup.relative_to(ROOT)),'existing_non_zone_nodes_unchanged':True,
            'added_ground_via':{'uuid':added_uuid,'x_mm':61.43,'y_mm':55.08,'pad_mm':1.20,'drill_mm':0.60},
            'zones':2,'net':'GND','layers':['F.Cu','B.Cu'],'settings':settings,
            'filled_polygon_count':{str(one(z,'layer')[1]):len(children(z,'filled_polygon')) for z in zones}}
    (FOLDER/'validation'/'gnd_zones_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
