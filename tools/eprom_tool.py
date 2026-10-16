"""Profile-aware UART EPROM tool; Python 3.10+, pyserial only for real serial I/O."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
import sys

ROOT = Path(__file__).resolve().parents[1]

def crc16(data: bytes, crc: int = 0xffff) -> int:
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xffff
    return crc

def load_profiles(path=ROOT/'device_profiles.json'):
    raw=Path(path).read_bytes()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()[:16]

def resolve(manifest, name):
    candidates=[p for p in manifest['profiles'] if name.casefold() in {v.casefold() for v in [p['name'],*p['aliases']]}]
    if len(candidates)!=1:raise ValueError(f'Unknown or ambiguous device: {name}')
    return candidates[0]

def checked_image(path, profile):
    data=Path(path).read_bytes()
    if len(data)!=profile['size_bytes']:
        raise ValueError(f"Image is {len(data)} bytes; {profile['name']} requires exactly {profile['size_bytes']}.")
    return data

class Transport:
    def __init__(self, serial_port):self.port=serial_port
    def command(self, line):self.port.write((line+'\n').encode('ascii'))
    def line(self, timeout=45, heartbeat=False):
        deadline=time.monotonic()+timeout; next_heartbeat=time.monotonic()+0.1; buffer=bytearray()
        while time.monotonic()<deadline:
            b=self.port.read(1)
            if b:
                if b==b'\n':
                    result=buffer.decode('ascii',errors='strict').rstrip('\r')
                    if result.startswith('ERR '):raise RuntimeError(result[4:])
                    return result
                buffer.extend(b)
                if len(buffer)>512:raise RuntimeError('Invalid overlong firmware response.')
            if heartbeat and time.monotonic()>=next_heartbeat:
                self.port.write(b'\x06');next_heartbeat=time.monotonic()+0.1
        raise TimeoutError('Firmware response timeout; close/reset returns hardware to READ.')
    def exact(self, count, timeout=300):
        deadline=time.monotonic()+timeout;data=bytearray()
        while len(data)<count:
            part=self.port.read(min(4096,count-len(data)))
            if part:data.extend(part);deadline=time.monotonic()+5
            elif time.monotonic()>deadline:raise TimeoutError('Truncated ROM data stream.')
        return bytes(data)
    def handshake(self, expected_hash):
        self.command('INFO');line=self.line(3)
        values=dict(piece.split('=',1) for piece in line.split()[1:])
        if not line.startswith('INFO ') or values.get('protocol')!='1':raise RuntimeError('Unsupported firmware protocol.')
        if values.get('profile_hash')!=expected_hash:raise RuntimeError('Host and firmware device profiles differ; rebuild/reflash before continuing.')
        return values
    def voltages(self):
        self.command('VOLTAGES');line=self.line(3)
        if not line.startswith('VOLTAGES '):raise RuntimeError('Invalid voltage response.')
        return dict(word.split('=',1) for word in line.split()[1:])
    def receive_image(self, profile):
        self.command('READ '+profile['name'])
        if self.line(3)!=f"DATA {profile['size_bytes']}":raise RuntimeError('Unexpected ROM size announced by firmware.')
        data=self.exact(profile['size_bytes'])
        if self.exact(1)!=b'\n':raise RuntimeError('Missing stream terminator.')
        self.result(data);return data
    def result(self,data):
        if self.line()!=f'OK {crc16(data):04X}':raise RuntimeError('Image CRC or verification result mismatch.')
    def send_frames(self,data):
        for offset in range(0,len(data),128):
            block=data[offset:offset+128]
            body=struct.pack('<IH',offset,len(block))+block
            self.port.write(b'\xa5\x5a'+body+struct.pack('<H',crc16(body)))
            if self.line(45,heartbeat=True)!=f'ACK {offset+len(block)}':raise RuntimeError('Unexpected firmware ACK offset.')
    def verify_image(self,profile,data):
        self.command('VERIFY '+profile['name'])
        if self.line(3)!='READY 128':raise RuntimeError('Firmware did not accept VERIFY.')
        self.send_frames(data);self.result(data)
    def write_image(self,profile,data):
        self.command('WRITE '+profile['name'])
        if self.line(5,heartbeat=True)!='READY 128':raise RuntimeError('Firmware did not accept WRITE.')
        self.send_frames(data)
        if self.line(3)!='VERIFY_READY 128':raise RuntimeError('Firmware did not enter final 5V verification.')
        self.send_frames(data);self.result(data)

def open_port(name,baud):
    try:import serial
    except ImportError as error:raise RuntimeError('Install pyserial: python -m pip install -r tools/requirements.txt') from error
    port=serial.Serial(port=None,baudrate=baud,timeout=0.02,write_timeout=2)
    port.dtr=False;port.port=name;port.open()
    # A falling edge on DTR# resets the AVR through C13, also removing hardware VPP.
    port.dtr=True;time.sleep(0.05);port.dtr=False;time.sleep(0.2);port.reset_input_buffer()
    return port

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles',type=Path,default=ROOT/'device_profiles.json')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    for command in ['read','verify','write','voltages','info']:
        s=sub.add_parser(command);s.add_argument('--port',required=True);s.add_argument('--baud',type=int,default=57600)
        if command in ('read','verify','write'):s.add_argument('--device',required=True)
        if command=='read':s.add_argument('--out',type=Path,required=True)
        if command in ('verify','write'):s.add_argument('--file',type=Path,required=True)
        if command=='write':s.add_argument('--yes',action='store_true');s.add_argument('--ambient-c',type=float,required=True)
    return p

def main(argv=None):
    args=parser().parse_args(argv);manifest,digest=load_profiles(args.profiles)
    if args.command=='list':
        for p in manifest['profiles']:
            print(f"{p['name']:16} {p['size_bytes']:8} bytes  read={p['read_supported']}  algorithm_verified={p['program_algorithm_verified']}  adapter={p['adapter']}")
        return 0
    profile=data=None
    if args.command in ('read','verify','write'):
        profile=resolve(manifest,args.device)
        if not profile['read_supported']:raise ValueError(f"{profile['name']}: read profile unverified; command disabled.")
        if args.command in ('verify','write'):data=checked_image(args.file,profile)
        if args.command=='write':
            if not profile['program_supported'] or not profile['program_algorithm_verified']:
                raise ValueError(f"{profile['name']}: programming algorithm unverified/disabled; no generic write will be attempted.")
            lo,hi=profile['program_temperature_c']
            if not lo<=args.ambient_c<=hi:raise ValueError(f'Programming requires ambient temperature {lo}...{hi} C for this profile.')
        if args.command=='read' and args.out.exists():raise ValueError(f'Refusing to overwrite existing dump: {args.out}')
    port=open_port(args.port,args.baud);transport=Transport(port)
    try:
        info=transport.handshake(digest)
        if args.command=='info':print(info)
        elif args.command=='voltages':print(transport.voltages())
        elif args.command=='read':
            result=transport.receive_image(profile)
            args.out.parent.mkdir(parents=True,exist_ok=True)
            # Only publish a file after the exact size and UART CRC have passed.
            with args.out.open('xb') as output:output.write(result)
            print(f'Read {len(result)} bytes; SHA256 {hashlib.sha256(result).hexdigest()}')
        elif args.command=='verify':transport.verify_image(profile,data);print('Every byte matches.')
        elif args.command=='write':
            if info.get('commissioned')!='1':raise RuntimeError('WRITE locked: firmware hardware commissioning flag is not enabled. See docs/bringup.md.')
            voltages=transport.voltages()
            print(f"Device: {profile['name']} | {len(data)} bytes | socket/adapter: {profile['adapter']}")
            print(f"Expected programming VCC {profile['program_vcc']} V; VPP {profile['program_vpp']} V")
            print(f"Measured READ target VCC: {int(voltages['target_mv'])/1000:.3f} V; VPP_SW: {int(voltages['vpp_sw_mv'])/1000:.3f} V")
            print('VPP_IN is checked through the switch with the socket isolated AFTER confirmation. Set a regulated supply for this profile.')
            if not args.yes and input('Type PROGRAM to enable programming voltage: ').strip()!='PROGRAM':
                print('Cancelled.');return 1
            transport.write_image(profile,data);print('Programming and whole-image verification at 5V passed.')
    finally:
        # Even on Ctrl-C/errors, send a physical reset edge; the hardware interlock removes VPP.
        try:port.dtr=True;time.sleep(0.05);port.dtr=False
        finally:port.close()
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,RuntimeError,TimeoutError,OSError) as error:print(f'Error: {error}',file=sys.stderr);sys.exit(2)
