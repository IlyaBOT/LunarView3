"""Single source of truth: generate JSON profiles and a compact AVR flash table."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
NATIONAL='https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/National%20Semiconductor/Memory%20Components/'
INTEL='https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/'

def profile(name, bits, package, adapter, source=None, aliases=(), verified=False):
    return dict(name=name,aliases=list(aliases),package=package,adapter=adapter,size_bytes=1<<bits,data_bits=8,address_bits=bits,
        read_supported=verified,read_vcc=5.0,read_vpp=5.0,program_supported=False,program_vcc=None,program_vpp=None,vpp_tolerance=None,
        address_pin_map={},data_pin_map={},ce_role=None,oe_role=None,pgm_role=None,vpp_pin_role=None,
        program_pulse_us=None,max_program_pulses=None,verify_algorithm=None,power_sequence=['USB logic first','controls inactive','VPP off','READ relay'],
        sources=[source] if source else [],pinout_verified=verified,read_profile_verified=verified,program_algorithm_verified=False,
        hardware_commissioned=False,read_access_delay_us=10,notes=[])

def map24(p, is2732=False):
    p['address_pin_map']={f'A{i}':8-i for i in range(8)}
    p['address_pin_map'].update(A8=23,A9=22,A10=19)
    if is2732:p['address_pin_map']['A11']=21
    p['data_pin_map']={f'D{i}':n for i,n in enumerate([9,10,11,13,14,15,16,17])}
    p.update(ce_role={'pin':18,'net':'TARGET_CE_PGM#','read_active':0},oe_role={'pin':20,'net':'TARGET_OE#','read_active':0},
        pgm_role={'pin':18,'note':'manufacturer-specific; write disabled'},vpp_pin_role={'pin':20 if is2732 else 21,'read':'OE logic' if is2732 else 'tie to TARGET_VCC (+5V)'},
        vcc_pin=24,gnd_pin=12)

def map28(p,bits):
    full={0:10,1:9,2:8,3:7,4:6,5:5,6:4,7:3,8:25,9:24,10:21,11:23,12:2,13:26,14:27,15:1}
    p['address_pin_map']={f'A{i}':full[i] for i in range(bits)}
    p['data_pin_map']={f'D{i}':n for i,n in enumerate([11,12,13,15,16,17,18,19])}
    p.update(ce_role={'pin':20,'net':'TARGET_CE_PGM#','read_active':0},oe_role={'pin':22,'net':'TARGET_OE#','read_active':0},
        pgm_role={'pin':20 if bits>=15 else 27,'net':'TARGET_CE_PGM#' if bits>=15 else 'TARGET_PGM#','inactive':1},
        vpp_pin_role={'pin':22 if bits==16 else 1,'read':'OE logic' if bits==16 else 'tie to TARGET_VCC (+5V)'},vcc_pin=28,gnd_pin=14)
    if bits==13:p['unused_pins']={'26':'NC'}

def map32(p,bits):
    full={0:12,1:11,2:10,3:9,4:8,5:7,6:6,7:5,8:27,9:26,10:23,11:25,12:4,13:28,14:29,15:3,16:2,17:30,18:31,19:1}
    p['address_pin_map']={f'A{i}':full[i] for i in range(bits)}
    p['data_pin_map']={f'D{i}':n for i,n in enumerate([13,14,15,17,18,19,20,21])}
    p.update(ce_role={'pin':22,'net':'TARGET_CE_PGM#','read_active':0},oe_role={'pin':24,'net':'TARGET_OE#','read_active':0},
        pgm_role={'pin':31 if bits<=18 else 22,'note':'National package comparison only; programming disabled'},
        vpp_pin_role={'pin':24 if bits==20 else 1,'read':'OE logic' if bits==20 else 'tie to TARGET_VCC (+5V)'},vcc_pin=32,gnd_pin=16)

def generate():
    profiles=[]
    p=profile('NM27C512',16,'DIP-28 600mil','onboard_U6',NATIONAL+'National%20NM27C512.pdf',['NM27C512Q','NM27C512N'],True)
    map28(p,16)
    p.update(program_supported=True,program_vcc=6.25,program_vpp=12.75,vpp_tolerance=0.25,
        program_vcc_min=6.0,program_vcc_max=6.5,program_vpp_min=12.5,program_vpp_max=13.0,program_vpp_absolute_max=14.0,
        program_temperature_c=[20,30],program_pulse_us=100,max_program_pulses=25,program_algorithm_verified=True,
        verify_algorithm='National Fast Algorithm: verify after every pulse at VCC=6.25V / OE-VPP=VIL; final whole-image compare at VCC=5V',
        power_sequence=['inactive controls and input data','arm internal HV with relay READ','test VPP_SW with socket isolated','VPP off and discharge verified',
            'relay PROGRAM; check 6.25V','for each byte: enable VPP; drive data; CE low 100us; CE high; input data; VPP off; discharge; verify byte',
            'VPP off; internal HV off; relay READ; compare all bytes at 5V'],
        notes=['Source: National TL/D/10834 February 1994, pages 2,5,6,7.',
            'Default firmware WRITE lock requires bench commissioning; algorithm verified does not mean hardware tested.',
            'Source OCR renders microseconds as ms; original page images explicitly show 100 us.',
            'Source final verification is 5.0V +/-5%; no universal overprogram pulse is specified.'])
    profiles.append(p)
    p=profile('27C512',16,'DIP-28 600mil','onboard_U6 (read compatibility only)',NATIONAL+'National%20NM27C512.pdf',[],True);map28(p,16)
    p['notes']=['Generic compatible read pinout only. WRITE requires an explicit manufacturer profile; use NM27C512 only for a marked National/Fairchild part.'];profiles.append(p)
    for name,bits in [('2716',11),('2732',12),('2764',13),('27128A',14),('27256',15)]:
        p=profile('INTEL'+name,bits,'DIP-'+('24' if bits<13 else '28'),'adapter_'+('2716_KR573RF5' if bits<13 else '28pin_27xx'),
            INTEL+'Intel%20'+name+'.pdf',[name]+(['27128'] if bits==14 else []),True)
        (map24(p,bits==12) if bits<13 else map28(p,bits))
        p['notes']=['Read mode and physical pinout verified against this Intel datasheet. Exact write algorithm is not implemented; WRITE disabled.']
        profiles.append(p)
    p=profile('KR573RF5',11,'DIP-24','adapter_2716_KR573RF5',None,['K573RF5','KR573RF5','КР573РФ5','К573РФ5'],False)
    p.update(expected_programming_vpp=25.0,verification_pending='Original manufacturer pinout/read specification and algorithm have not been located.')
    p['notes']=['Requested 2KiB x8 / A0-A10 profile is present but READ and WRITE are quarantined. No Intel pinout is silently substituted for KR573RF5.']
    profiles.append(p)
    for bits in range(17,21):
        suffix={17:'010',18:'020',19:'040',20:'080'}[bits]
        sources={17:'https://datasheets.pl/elementy_czynne/IC/NM/NM27C010-2.pdf',
                 18:'https://www.pselectronic.cz/pdf/1125/11250125.pdf',
                 19:'https://docs.rs-online.com/a680/0900766b80025540.pdf',
                 20:NATIONAL+'National%20NM27C512.pdf'}
        p=profile('NM27C'+suffix,bits,'DIP-32','adapter_32pin_JEDEC',sources[bits],['27C'+suffix],bits<20)
        map32(p,bits);p['pinout_verified']=True
        p['notes']=['Pinout and 5V read mode verified against the exact National/Fairchild datasheet. VPP pin1 tied to TARGET_VCC for READ; WRITE disabled.'] if bits<20 else [
            'Package roles verified in NM27C512 family comparison on page 2. Individual read operating limits/algorithm require an exact device datasheet; commands disabled.']
        if bits==17:p['unused_pins']={'30':'XX / do not connect on read adapter'}
        profiles.append(p)
    result={'schema_version':1,'hardware_revision':'A','profiles':profiles,
        'unsupported':{'2708':'Requires +12V and -5V in addition to +5V even for read; unsupported power architecture.',
                       '27C160':'16-bit data bus; Rev A is 8-bit only.'}}
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    # Keep canonical LF bytes on Windows: firmware hash must match the actual host file.
    (ROOT/'device_profiles.json').write_bytes(text.encode('utf8'))
    digest=hashlib.sha256(text.encode()).hexdigest()[:16]
    header=['/* Generated from device_profiles.json by tools/generate_profiles.py. */', '#pragma once', '#include <stdint.h>','#include <avr/pgmspace.h>',
        '#define PROFILE_HASH "'+digest+'"', '#define PROFILE_COUNT '+str(len(profiles)),
        'typedef struct { char name[16]; uint32_t size; uint8_t address_bits, read_ok, program_ok, algorithm; uint16_t read_min_mv, read_max_mv, vcc_min_mv, vcc_max_mv, vpp_min_mv, vpp_max_mv, pulse_us; uint8_t max_pulses; } profile_t;',
        'static const profile_t profiles[PROFILE_COUNT] PROGMEM = {']
    for p in profiles:
        values=[p['size_bytes'],p['address_bits'],int(p['read_supported']),int(p['program_supported']),int(p['program_algorithm_verified']),4750,5250,
            int(p.get('program_vcc_min',0)*1000),int(p.get('program_vcc_max',0)*1000),int(p.get('program_vpp_min',0)*1000),
            int(p.get('program_vpp_max',0)*1000),p['program_pulse_us'] or 0,p['max_program_pulses'] or 0]
        header.append('  {"'+p['name']+'", '+', '.join(map(str,values))+'},')
    header+=['};','']
    (ROOT/'firmware'/'profiles.h').write_text('\n'.join(header),encoding='utf8')
    print('Profile hash:',digest,'profiles:',len(profiles))
if __name__=='__main__':generate()
