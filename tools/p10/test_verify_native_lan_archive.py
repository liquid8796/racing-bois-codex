"""Synthetic archive controls; no host/player/network execution."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import struct
import tempfile
import unittest
import zipfile

import package_desktop_candidate as common
import verify_native_lan_archive as verifier


def fixture_pe():
    data = bytearray(128); data[:2] = b'MZ'; struct.pack_into('<I', data, 0x3C, 64)
    data[64:68] = b'PE\0\0'; struct.pack_into('<H', data, 68, 0x8664); struct.pack_into('<H', data, 88, 0x20B)
    return bytes(data)


class NativeLanArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rb-lan-archive-tests-'); self.root = Path(self.temp.name).resolve()
        self.archive = self.root / 'candidate.zip'
        self.files = {name: b'explicit synthetic fixture' for name in verifier.REQUIRED}
        for name in verifier.PE_FILES:
            self.files[name] = fixture_pe()
        self.files['RacingBois.Server.Host.runtimeconfig.json'] = common.json_bytes({'runtimeOptions': {'includedFrameworks': [{'name': 'Microsoft.NETCore.App', 'version': '10.0.0'}]}})

    def tearDown(self):
        if self.root.parent != Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('rb-lan-archive-tests-'):
            raise RuntimeError('Test cleanup escaped its explicitly owned temporary root')
        self.temp.cleanup()

    def write(self, change_manifest=None, extra=None):
        rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} for name, data in sorted(self.files.items())]
        manifest = {'schema': 1, 'kind': 'native-lan-host-candidate', 'runtime': 'win-x64', 'realmKind': 'offline',
                    'releaseAccepted': False, 'sourceSha256': 'a' * 64, 'protocolVersion': 6, 'contentHash': 'fixture-content', 'files': rows}
        if change_manifest:
            change_manifest(manifest)
        entries = {verifier.PREFIX + name: data for name, data in self.files.items()}
        entries[verifier.MANIFEST] = common.json_bytes(manifest)
        if extra:
            entries.update(extra)
        with zipfile.ZipFile(self.archive, 'x', compression=zipfile.ZIP_STORED) as output:
            for name, data in sorted(entries.items()):
                output.writestr(common.zip_info(name), data)

    def verify(self, **kwargs):
        return verifier.verify_archive(self.archive, common.digest(self.archive), **kwargs)

    def rewrite(self, transform):
        with zipfile.ZipFile(self.archive) as source:
            entries = [(info, source.read(info)) for info in source.infolist()]
        self.archive = self.root / 'changed.zip'
        with zipfile.ZipFile(self.archive, 'x') as output:
            for info, data in transform(entries):
                output.writestr(info, data)

    def test_valid_exact_archive_and_explicit_candidate_scope(self):
        self.write(); result = self.verify(expected_protocol=6, expected_content_hash='fixture-content')
        self.assertTrue(result['archiveIntegrityPassed']); self.assertFalse(result['releaseAccepted'])
        self.assertFalse(result['physicalLanAccepted']); self.assertEqual(len(self.files), result['verifiedPayloadFiles'])
        self.assertEqual(['candidate.zip'], [path.name for path in self.root.iterdir()])

    def test_external_digest_is_required(self):
        self.write()
        for value in (None, '', 'A' * 64, '0' * 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verifier.verify_archive(self.archive, value)

    def test_protocol_mismatch_is_rejected(self):
        self.write()
        with self.assertRaisesRegex(ValueError, 'protocol'):
            self.verify(expected_protocol=5)

    def test_content_mismatch_is_rejected(self):
        self.write()
        with self.assertRaisesRegex(ValueError, 'content hash'):
            self.verify(expected_content_hash='other')

    def test_online_realm_is_rejected(self):
        self.write(lambda manifest: manifest.update(realmKind='online'))
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.verify()

    def test_false_release_acceptance_is_rejected(self):
        self.write(lambda manifest: manifest.update(releaseAccepted=True))
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.verify()

    def test_boolean_protocol_is_rejected(self):
        self.write(lambda manifest: manifest.update(protocolVersion=True))
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.verify()

    def test_changed_same_size_payload_is_rejected(self):
        self.write()
        self.rewrite(lambda entries: [(info, b'x' * len(data) if info.filename.endswith('/README.txt') else data) for info, data in entries])
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.verify()

    def test_unregistered_file_is_rejected(self):
        self.write(extra={verifier.PREFIX + 'unexpected.txt': b'unregistered'})
        with self.assertRaisesRegex(ValueError, 'file set'):
            self.verify()

    def test_missing_required_runtime_binary_is_rejected(self):
        del self.files['coreclr.dll']; self.write()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.verify()

    def test_external_runtime_dependency_is_rejected(self):
        self.files['RacingBois.Server.Host.runtimeconfig.json'] = common.json_bytes({'runtimeOptions': {'framework': {'name': 'Microsoft.NETCore.App', 'version': '10.0.0'}}})
        self.write()
        with self.assertRaisesRegex(ValueError, 'external runtime'):
            self.verify()

    def test_wrong_pe_architecture_is_rejected(self):
        data = bytearray(fixture_pe()); struct.pack_into('<H', data, 68, 0x14C)
        self.files['RacingBois.Server.Host.exe'] = bytes(data); self.write()
        with self.assertRaisesRegex(ValueError, 'x64'):
            self.verify()

    def test_out_of_range_pe_offset_is_rejected(self):
        data = bytearray(fixture_pe()); struct.pack_into('<I', data, 0x3C, 100000)
        self.files['RacingBois.Server.Host.exe'] = bytes(data); self.write()
        with self.assertRaisesRegex(ValueError, 'offset'):
            self.verify()

    def test_private_sqlite_wal_is_rejected_even_when_manifested(self):
        self.files['realm.sqlite3-wal'] = b'private fixture'; self.write()
        with self.assertRaisesRegex(ValueError, 'Private realm'):
            self.verify()

    def test_case_alias_is_rejected(self):
        self.write(extra={verifier.PREFIX + 'readme.txt': b'case alias'})
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            self.verify()

    def test_file_directory_prefix_collision_is_rejected(self):
        self.files['collision'] = b'file'; self.files['collision/child'] = b'child'; self.write()
        with self.assertRaisesRegex(ValueError, 'prefix collision'):
            self.verify()

    def test_link_entry_is_rejected(self):
        self.write()
        def changed(entries):
            info = copy.copy(entries[0][0]); info.external_attr = (stat.S_IFLNK | 0o777) << 16
            return [(info, entries[0][1])] + entries[1:]
        self.rewrite(changed)
        with self.assertRaisesRegex(ValueError, 'entry has unexpected'):
            self.verify()

    def test_traversal_entry_is_rejected(self):
        self.write()
        self.rewrite(lambda entries: entries + [(zipfile.ZipInfo(verifier.PREFIX + '../escape'), b'bad')])
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate_json_keys_are_rejected(self):
        self.write()
        self.rewrite(lambda entries: [(info, data.replace(b'"schema": 1', b'"schema": 2, "schema": 1') if info.filename == verifier.MANIFEST else data) for info, data in entries])
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            self.verify()

    def test_archive_can_be_verified_after_relocation(self):
        self.write(); moved = self.root / 'transferred.zip'; moved.write_bytes(self.archive.read_bytes())
        self.assertTrue(verifier.verify_archive(moved, common.digest(self.archive))['archiveIntegrityPassed'])


if __name__ == '__main__':
    unittest.main()
