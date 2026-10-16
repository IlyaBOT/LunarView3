"""Incident raster energy only; does not model MFP sensitivity at 455 nm."""
import argparse,json
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--power-w',type=float,default=3.0,help='Full optical output in W (nominal unless measured)')
p.add_argument('--percent',type=float,required=True)
p.add_argument('--feed',type=float,default=1000,help='mm/min')
p.add_argument('--pitch',type=float,default=0.05,help='Raster row spacing in mm')
p.add_argument('--passes',type=int,default=1)
a=p.parse_args()
if a.power_w<=0 or not 0<a.percent<=100 or a.feed<=0 or a.pitch<=0 or a.passes<1: p.error('All physical parameters must be positive; percent <= 100')
optical_mw=a.power_w*1000*a.percent/100
speed=a.feed/60
dose=100*optical_mw/(speed*a.pitch)*a.passes
print(json.dumps({'assumes_linear_pwm_and_uniform_raster':True,'optical_mw_nominal':optical_mw,'speed_mm_s':speed,'incident_mJ_cm2':dose,'spectral_compatibility_455nm':'UNVERIFIED'},indent=2))
