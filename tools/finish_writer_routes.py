"""Finish the narrow USB/MCU power escapes without changing the routed design."""
from pathlib import Path
import pcbnew as k

root=Path(__file__).resolve().parents[1]
path=root/'Lunar-Writer/Lunar_Writer.kicad_pcb'
b=k.LoadBoard(str(path)); fps={f.GetReference():f for f in b.GetFootprints()}
drawings=b.GetDrawings()
def xy(x,y):return k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def route(net,points,width=.25,layer=k.F_Cu):
    for a,z in zip(points,points[1:]):
        t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*z));t.SetWidth(k.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)

if k.ToMM(fps['R70'].GetPosition().y)>115:
    # Remove only the old resistor-pad branches; keep the rest of these nets.
    for t in list(b.GetTracks()):
        pts={(round(k.ToMM(p.x),4),round(k.ToMM(p.y),4)) for p in [t.GetStart(),t.GetEnd()]}
        if (t.GetNetname()=='BOOST_30V' and ((83.0,117.825) in pts or (83.175,118.0) in pts)) or (t.GetNetname()=='BOOST_FB' and (83.0,116.175) in pts):b.Delete(t)
    fps['R70'].SetPosition(xy(83,112));fps['R70'].SetOrientationDegrees(180)
    route('BOOST_FB',[(82.175,112),(81,112),(79.8899,113.1101),(79.8899,114.1445)])
    route('BOOST_30V',[(83.825,112),(85,113.175),(85,118)],.6)
    route('+5V',[(91.8375,73.6),(89.825,73.6),(89,72.775)])
    route('USB_VBUS',[(54.4625,79.7),(56.5,79.7)])
    route('USB_VBUS',[(56.5,79.7),(57.9375,81.1375),(59,81.1375)],.6)

legends={
 'STATUS RGB - ONE ONLY':('RGB / 5050 OR THT',79,100.6,.8),
 'EXTERNAL POWER / HV':('HV SUPPLY',62,107,.8),
 'J4: +12...24V DC':('12-24V DC',66,152,1),
 '+':('+',58,149,.9),'GND':('GND',62,149,.9),
}
for t in drawings:
    if isinstance(t,k.PCB_TEXT) and t.GetText() in legends:
        s,x,y,size=legends[t.GetText()];t.SetText(s);t.SetPosition(xy(x,y));t.SetTextSize(xy(size,size))
for f in fps.values():
    for item in f.GraphicalItems():
        if isinstance(item,k.PCB_TEXT): item.SetLayer(k.F_Fab)
k.SaveBoard(str(path),b)
print('Finished power escapes and resistor clearance; verify DRC next.')
