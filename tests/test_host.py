"""Host protocol tests with a deterministic serial simulator; no connected hardware."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import eprom_tool as host

class Serial:
    def __init__(self,response=b''):self.response=bytearray(response);self.writes=[];self.closed=False;self.dtr=False
    def read(self,count):
        data=bytes(self.response[:min(count,17)]);del self.response[:len(data)];return data
    def write(self,data):self.writes.append(data);return len(data)
    def close(self):self.closed=True

class ProtocolTests(unittest.TestCase):
    def setUp(self):self.manifest,self.digest=host.load_profiles();self.profile=host.resolve(self.manifest,'NM27C512')
    def test_crc_known_vector(self):self.assertEqual(host.crc16(b'123456789'),0x29b1)
    def test_alias_exact_manufacturer(self):self.assertEqual(host.resolve(self.manifest,'nm27c512q')['name'],'NM27C512')
    def test_generic_profile_cannot_program(self):self.assertFalse(host.resolve(self.manifest,'27C512')['program_supported'])
    def test_no_unverified_writes(self):
        self.assertEqual([p['name'] for p in self.manifest['profiles'] if p['program_supported']],['NM27C512'])
        self.assertFalse(host.resolve(self.manifest,'КР573РФ5')['read_supported'])
    def test_all_profile_maps_have_correct_dimensions(self):
        for p in self.manifest['profiles']:
            self.assertEqual(p['size_bytes'],1<<p['address_bits'])
            if p['pinout_verified']:
                self.assertEqual(len(p['address_pin_map']),p['address_bits']);self.assertEqual(len(p['data_pin_map']),8)
                self.assertEqual(len(set(p['address_pin_map'].values())),p['address_bits'])
                self.assertFalse(set(p['address_pin_map'].values())&set(p['data_pin_map'].values()))
    def test_firmware_hash_matches(self):
        header=(host.ROOT/'firmware/profiles.h').read_text();self.assertIn('#define PROFILE_HASH "'+self.digest+'"',header)
    def test_handshake_rejects_stale_profiles(self):
        t=host.Transport(Serial(b'INFO protocol=1 profile_hash=bad commissioned=1\n'))
        with self.assertRaisesRegex(RuntimeError,'profiles differ'):t.handshake(self.digest)
    def test_handshake_checks_version(self):
        t=host.Transport(Serial(b'INFO protocol=2 profile_hash=bad\n'))
        with self.assertRaisesRegex(RuntimeError,'protocol'):t.handshake(self.digest)
    def test_read_exact_length_crc_and_partial_serial_reads(self):
        data=bytes(range(256))*256
        s=Serial(b'DATA 65536\n'+data+b'\n'+f'OK {host.crc16(data):04X}\n'.encode())
        self.assertEqual(host.Transport(s).receive_image(self.profile),data)
        self.assertEqual(s.writes,[b'READ NM27C512\n'])
    def test_corrupt_read_rejected(self):
        data=b'\xff'*65536
        s=Serial(b'DATA 65536\n'+data+b'\n'+f'OK {host.crc16(data)^1:04X}\n'.encode())
        with self.assertRaisesRegex(RuntimeError,'CRC'):host.Transport(s).receive_image(self.profile)
    def test_verify_frame_offsets_lengths_and_crc(self):
        data=bytes(range(256))+b'abc';s=Serial(b'READY 128\nACK 128\nACK 256\nACK 259\n'+f'OK {host.crc16(data):04X}\n'.encode())
        host.Transport(s).verify_image(self.profile,data)
        self.assertEqual(s.writes[0],b'VERIFY NM27C512\n')
        offset=0
        for frame in s.writes[1:]:
            self.assertEqual(frame[:2],b'\xa5\x5a');off,size=struct.unpack('<IH',frame[2:8])
            self.assertEqual(off,offset);self.assertEqual(frame[8:-2],data[offset:offset+size])
            self.assertEqual(struct.unpack('<H',frame[-2:])[0],host.crc16(frame[2:-2]));offset+=size
        self.assertEqual(offset,len(data))
    def test_write_requires_final_verification_pass(self):
        data=b'abc';s=Serial(b'READY 128\nACK 3\nVERIFY_READY 128\nACK 3\n'+f'OK {host.crc16(data):04X}\n'.encode())
        host.Transport(s).write_image(self.profile,data)
        self.assertEqual(s.writes[0],b'WRITE NM27C512\n');self.assertEqual(s.writes[1],s.writes[2])
    def test_wrong_ack_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'ACK'):host.Transport(Serial(b'ACK 7\n')).send_frames(b'abc')
    def test_firmware_error_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'PROGRAM_VOLTAGE'):host.Transport(Serial(b'ERR PROGRAM_VOLTAGE\n')).line()
    def test_timeout_and_keepalive(self):
        s=Serial();t=host.Transport(s)
        with patch('eprom_tool.time.monotonic',side_effect=[0,0,0.05,0.15,0.15,0.3]):
            with self.assertRaises(TimeoutError):t.line(0.2,heartbeat=True)
        self.assertEqual(s.writes,[b'\x06'])
    def test_invalid_image_before_opening_port(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.bin';path.write_bytes(b'bad')
            with patch('eprom_tool.open_port') as open_port:
                with self.assertRaisesRegex(ValueError,'exactly'):host.main(['verify','--device','NM27C512','--port','COM5','--file',str(path)])
                open_port.assert_not_called()
    def test_unsupported_write_never_opens_port(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'image.bin';path.write_bytes(b'\xff'*2048)
            with patch('eprom_tool.open_port') as open_port:
                with self.assertRaisesRegex(ValueError,'algorithm'):host.main(['write','--device','2716','--port','COM5','--file',str(path),'--ambient-c','25','--yes'])
                open_port.assert_not_called()
    def test_read_error_produces_no_file_and_resets(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'dump.bin';s=Serial(f'INFO protocol=1 profile_hash={self.digest} commissioned=0\nERR READ_VOLTAGE\n'.encode())
            with patch('eprom_tool.open_port',return_value=s),patch('eprom_tool.time.sleep'):
                with self.assertRaisesRegex(RuntimeError,'READ_VOLTAGE'):host.main(['read','--device','NM27C512','--port','COM5','--out',str(out)])
            self.assertTrue(s.closed);self.assertFalse(out.exists());self.assertFalse(s.dtr)
    def test_safe_firmware_lock_before_any_voltage_command(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'image.bin';path.write_bytes(b'\xff'*65536)
            s=Serial(f'INFO protocol=1 profile_hash={self.digest} commissioned=0\n'.encode())
            with patch('eprom_tool.open_port',return_value=s),patch('eprom_tool.time.sleep'):
                with self.assertRaisesRegex(RuntimeError,'commissioning'):host.main(['write','--device','NM27C512','--port','COM5','--file',str(path),'--ambient-c','25','--yes'])
            self.assertEqual(s.writes,[b'INFO\n']);self.assertTrue(s.closed)

if __name__=='__main__':unittest.main(verbosity=2)
