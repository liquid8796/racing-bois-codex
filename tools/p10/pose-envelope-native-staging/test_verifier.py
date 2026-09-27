"""Synthetic verifier controls only; no fixture is represented as a native run."""
import struct
import copy
import hashlib
import tempfile
import unittest
import zlib
from pathlib import Path
import verify_run

def encoded_png(varied=True):
    def chunk(kind,payload):return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    row=(b'\x20\x30\x40\xff'*640)+(b'\xc0\xd0\xe0\xff'*640 if varied else b'\x20\x30\x40\xff'*640)
    pixels=(b'\x00'+row)*720
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1280,720,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')

class PreviewVerifierTests(unittest.TestCase):
    def settings_fixture(self,root):
        rows=[]
        for name in ['ProjectSettings','GraphicsSettings','QualitySettings']:
            data=(name+': frozen effective override\n').encode()
            rows.append({'path':'ProjectSettings/'+name+'.asset','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
            for phase in ['effective','before','after']:
                folder=root/'BuildEvidence'/phase;folder.mkdir(parents=True,exist_ok=True)
                (folder/(name+'.asset')).write_bytes(data)
        rows.sort(key=lambda row:row['path'])
        fingerprint=hashlib.sha256('\n'.join(row['path']+' '+row['sha256'] for row in rows).encode()).hexdigest()
        return {'sources':rows,'sourcesAfter':copy.deepcopy(rows),'changedDuringBuild':[],
                'sourceFingerprint':fingerprint,'sourceBindingPassed':True}
    def test_effective_settings_are_bound_before_and_after_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);verify_run.verify_source_binding(root,self.settings_fixture(root))
    def test_rejects_settings_mutation_despite_claimed_binding_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);build=self.settings_fixture(root);build['sourcesAfter'][0]['sha256']='f'*64
            with self.assertRaises(ValueError):verify_run.verify_source_binding(root,build)
    def test_rejects_in_memory_mutation_with_unchanged_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);build=self.settings_fixture(root);build['changedDuringBuild']=['ProjectSettings/QualitySettings.asset']
            with self.assertRaises(ValueError):verify_run.verify_source_binding(root,build)
    def test_rejects_old_settings_bytes_as_effective_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);build=self.settings_fixture(root)
            (root/'BuildEvidence/effective/ProjectSettings.asset').write_text('original settings before overrides')
            with self.assertRaises(ValueError):verify_run.verify_source_binding(root,build)
    def test_rejects_missing_source_after_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);build=self.settings_fixture(root);build['sourcesAfter'].pop()
            with self.assertRaises(ValueError):verify_run.verify_source_binding(root,build)
    def test_decodes_nonuniform_fixture_pixels(self):self.assertTrue(verify_run.png_varied(encoded_png()))
    def test_rejects_uniform_even_if_claimed_varied(self):self.assertFalse(verify_run.png_varied(encoded_png(False)))
    def test_rejects_corrupt_crc(self):
        payload=bytearray(encoded_png());payload[-5]^=1
        with self.assertRaises(ValueError):verify_run.png_varied(bytes(payload))
    def test_rejects_truncation(self):
        with self.assertRaises(ValueError):verify_run.png_varied(encoded_png()[:-8])
    def test_rejects_trailing_payload(self):
        with self.assertRaises(ValueError):verify_run.png_varied(encoded_png()+b'not png')
    def test_unsafe_receipt_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in ['../outside.png','/outside.png']:
                with self.subTest(path=path),self.assertRaises(ValueError):verify_run.contained(Path(folder),path)
    def test_finite_does_not_trust_nested_values(self):
        self.assertFalse(verify_run.finite({'positions':[1,{'z':float('nan')}]}))
        self.assertFalse(verify_run.finite([float('inf')]))
    def test_rejects_wrong_pe_architecture(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.exe';data=bytearray(128);data[:2]=b'MZ';struct.pack_into('<I',data,60,64);data[64:68]=b'PE\x00\x00';struct.pack_into('<H',data,68,0x14c);struct.pack_into('<H',data,88,0x10b);path.write_bytes(data)
            with self.assertRaises(ValueError):verify_run.require_x64(path)

if __name__=='__main__':unittest.main()
