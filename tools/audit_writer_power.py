"""Electrical ratings calculations and local mechanical envelope models."""
from pathlib import Path
import json,math,sys
import pcbnew as k
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kicad_sexpr import parse,dump,children

p=Path(__file__).resolve().parents[1]/'Lunar-Writer'
def box(x,y,z,sx,sy,sz,color):
    return f'Transform {{ translation {x} {y} {z} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }} geometry Box {{ size {sx} {sy} {sz} }} }} ] }}\n'
f2='#VRML V2.0 utf8\n# Visual envelope, NOT factory CAD. Bourns MF-R090, pitch 5.1 mm.\n'
f2+=box(2.55,0,9.3,11.7,3.1,14.7,'0.7 0.36 0.07')
for x in [0,5.1]: f2+=box(x,0,1,.51,.51,2,'0.7 0.7 0.72')
(p/'3DModels/PTC_MFR090_envelope.wrl').write_text(f2,encoding='utf8')
l1='#VRML V2.0 utf8\n# Visual envelope, NOT factory CAD. Bourns SRR1210A, nominal 12 x 12 x 10 mm.\n'
l1+=box(0,0,5.15,12,12,9.7,'0.12 0.13 0.14')
for x in [-5.05,5.05]:l1+=box(x,0,.15,2.4,5.3,.3,'0.7 0.7 0.73')
(p/'3DModels/SRR1210A_envelope.wrl').write_text(l1,encoding='utf8')
b=k.LoadBoard(str(p/'Lunar_Writer.kicad_pcb'))
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref not in ['F2','L1']:continue
    name='PTC_MF_R090' if ref=='F2' else 'Writer_L1_L_Bourns_SRR1210A'
    f.SetFPIDAsString('ProjectFootprints:'+name)
    f.Models().clear();m=k.FP_3DMODEL();m.m_Filename='${KIPRJMOD}/3DModels/'+('PTC_MFR090_envelope.wrl' if ref=='F2' else 'SRR1210A_envelope.wrl')
    m.m_Scale.x=m.m_Scale.y=m.m_Scale.z=1/2.54;f.Models().push_back(m)
    clone=k.FOOTPRINT(f);clone.SetPosition(k.VECTOR2I(0,0));clone.SetOrientationDegrees(0);clone.SetReference('REF**');clone.SetValue(name)
    for pad in clone.Pads():pad.SetNetCode(0)
    k.FootprintSave(str(p/'ProjectFootprints.pretty'),clone)
    for path in p.glob('*.kicad_sch'):
        tree=parse(path.read_text(encoding='utf8'));changed=False
        for sym in children(tree,'symbol'):
            props={a[1]:a for a in children(sym,'property')}
            if props['Reference'][2]==ref:props['Footprint'][2]='ProjectFootprints:'+name;changed=True
        if changed:path.write_text('('+dump(tree[0])+'\n'+'\n'.join('  '+dump(x) for x in tree[1:])+'\n)\n',encoding='utf8')
k.SaveBoard(str(p/'Lunar_Writer.kicad_pcb'),b)

vin=10.5;vout=1.23*(1+47000/2000);iload=.1;L=100e-6;rc=470;cout=680e-6
rcmax=750*iload*vout**2/vin**2
coutmin=max(.19*L*rc*iload/(vin*vout),vin*rc*(vin+3.74e5*L)/(487800*vout**3))
ccmin=58.5*vout**2*cout/(rc**2*vin)
# Conservative ripple bound at Vin=Vout/2, lowest L and oscillator frequency.
delta=vout/(4*(L*.8)*42000);peak=iload*vout/(.75*vin)+delta/2
report={'nominal_boost_v':vout,'minimum_protected_input_assumed_v':vin,'boost_output_design_current_a':iload,
 'target_vcc_design_current_a':.1,'assumed_efficiency':.75,'calculated_input_current_a':vout*iload/(.75*vin)+.1+.0105,
 'compensation_rc_max_ohm':rcmax,'chosen_rc_ohm':rc,'minimum_cout_uf':coutmin*1e6,'chosen_cout_uf':680,
 'minimum_cc_uf':ccmin*1e6,'chosen_cc_uf':47,'minimum_cc_with_cout_tolerance_uf':ccmin*1.2e6,'conservative_inductor_peak_bound_a':peak,'inductor_isat_a':2.2,
 'vcc_regulator_loss_at_24v_100ma_w':(24-6.25)*(.1+.0105),
 'vpp_regulator_loss_at_30v_100ma_w':(vout-12.75)*(.1+.0105),
 'input_ptc_hold_a_23c':.9,'input_ptc_hold_a_50c':.65,'bulk_capacitor_rating_v':50,
 'diode_rating_v':60,'input_tvS_standoff_v':24,'input_tvS_max_clamp_v':38.9,
 'formula_source':'https://www.ti.com/lit/ds/symlink/lm2577.pdf (page 19, equations 8-10)',
 'switch_net_track_length_mm':sum(k.ToMM(t.GetLength()) for t in b.GetTracks() if t.GetNetname()=='BOOST_SW' and not isinstance(t,k.PCB_VIA)),
 'physical_stability_and_temperature_tested':False,'3d_envelopes_mechanically_verified':False}
assert rc*1.05<=rcmax and cout*.8>=coutmin and 47e-6*.8>=ccmin*1.2 and peak<2.2
(p/'validation/power_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
