"""Settings/source mutation controls only; no Unity, native process or network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import native_probe_runner as runner


class NativeProbeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rb-probe-settings-tests-')
        self.root = Path(self.temp.name).resolve(); self.build = self.root / 'player'; self.build.mkdir()
        (self.root / 'source.cs').write_text('unchanged source', encoding='utf8')
        (self.build / 'player.dll').write_bytes(b'explicit non-executable fixture')
        rows = [self.row(self.root / 'source.cs', 'source.cs')]
        for name in sorted(runner.SETTINGS):
            filename = Path(name).name
            original, effective = ('original ' + filename).encode(), ('effective ' + filename).encode()
            live = self.root / name; live.parent.mkdir(exist_ok=True); live.write_bytes(original)
            for phase in ('original', 'restored', 'effective', 'before', 'after'):
                file = self.build / 'BuildEvidence' / phase / filename; file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(original if phase in ('original', 'restored') else effective)
            rows.append(self.row(self.build / 'BuildEvidence/effective' / filename, name))
        rows.sort(key=lambda row: row['path'])
        self.receipt = {'sources': rows, 'sourcesAfter': copy.deepcopy(rows), 'changedDuringBuild': [],
                        'sourceFingerprint': runner.fingerprint(rows), 'protocolVersion': 6,
                        'playerFiles': [self.row(path, path.relative_to(self.build).as_posix()) for path in sorted(self.build.rglob('*')) if path.is_file()]}

    def tearDown(self):
        if self.root.parent != Path(tempfile.gettempdir()).resolve() or not self.root.name.startswith('rb-probe-settings-tests-'):
            raise RuntimeError('Test cleanup escaped its explicitly owned temporary root')
        self.temp.cleanup()

    @staticmethod
    def row(path, name):
        return {'path': name, 'bytes': path.stat().st_size, 'sha256': runner.digest(path)}

    def check(self):
        return runner.source_binding_changes(self.root, self.build, self.receipt)

    def test_restored_live_settings_can_differ_from_bound_effective_settings(self):
        self.assertEqual(sorted(runner.SETTINGS), sorted(runner.changed_files(self.root, self.receipt['sources'])))
        result = self.check()
        self.assertEqual([], result['changedSources']); self.assertEqual([], result['settingsEvidenceIssues'])
        self.assertTrue(result['settingsEvidencePassed'])

    def test_each_effective_phase_mutation_is_rejected(self):
        for phase in ('effective', 'before', 'after'):
            with self.subTest(phase=phase):
                path = self.build / 'BuildEvidence' / phase / 'GraphicsSettings.asset'; original = path.read_bytes()
                try:
                    path.write_bytes(b'mutated effective evidence')
                    self.assertFalse(self.check()['settingsEvidencePassed'])
                finally:
                    path.write_bytes(original)

    def test_original_copy_mutation_is_rejected(self):
        (self.build / 'BuildEvidence/original/ProjectSettings.asset').write_bytes(b'mutated original')
        self.assertFalse(self.check()['settingsEvidencePassed'])

    def test_restored_copy_mutation_is_rejected(self):
        (self.build / 'BuildEvidence/restored/QualitySettings.asset').write_bytes(b'mutated restored')
        self.assertFalse(self.check()['settingsEvidencePassed'])

    def test_current_live_original_mutation_is_reported(self):
        (self.root / 'ProjectSettings/GraphicsSettings.asset').write_bytes(b'new user settings')
        result = self.check(); self.assertEqual(['ProjectSettings/GraphicsSettings.asset'], result['changedSources'])
        self.assertTrue(result['settingsEvidencePassed'])

    def test_rebasing_both_copies_and_live_does_not_bypass_bound_player_manifest(self):
        for path in (self.build / 'BuildEvidence/original/QualitySettings.asset',
                     self.build / 'BuildEvidence/restored/QualitySettings.asset', self.root / 'ProjectSettings/QualitySettings.asset'):
            path.write_bytes(b'identical tampered copies')
        self.assertFalse(self.check()['settingsEvidencePassed'])

    def test_non_settings_sources_remain_exact_live(self):
        (self.root / 'source.cs').write_text('changed source', encoding='utf8')
        self.assertEqual(['source.cs'], self.check()['changedSources'])

    def test_missing_settings_source_row_cannot_downgrade_to_legacy(self):
        self.receipt['sources'] = [row for row in self.receipt['sources'] if row['path'] != 'ProjectSettings/ProjectSettings.asset']
        self.receipt['sourcesAfter'] = copy.deepcopy(self.receipt['sources'])
        self.receipt['sourceFingerprint'] = runner.fingerprint(self.receipt['sources'])
        with self.assertRaisesRegex(ValueError, 'complete_effective_settings'):
            self.check()

    def test_before_after_source_mismatch_is_rejected(self):
        self.receipt['sourcesAfter'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'complete_effective_settings'):
            self.check()

    def test_settings_evidence_must_be_registered_player_bytes(self):
        self.receipt['playerFiles'] = [row for row in self.receipt['playerFiles'] if row['path'] != 'BuildEvidence/original/QualitySettings.asset']
        self.assertFalse(self.check()['settingsEvidencePassed'])

    def test_missing_snapshot_is_rejected(self):
        (self.build / 'BuildEvidence/after/ProjectSettings.asset').unlink()
        self.assertFalse(self.check()['settingsEvidencePassed'])

    def test_final_runtime_pass_still_requires_unchanged_settings(self):
        path = self.build / 'NativeProbe.build.json'; path.write_text(json.dumps(self.receipt), encoding='utf8')
        receipt_hash = runner.digest(path)
        payload = {'status': 'PASS', 'sourceFingerprint': self.receipt['sourceFingerprint'], 'protocolVersion': 6,
                   'monoDetected': True, 'platform': 'WindowsPlayer', 'backend': 'Mono2x', 'endpoint': 'wss://example.test/multiplayer'}
        before = runner.final_verification(self.root, self.build, self.receipt, receipt_hash, payload, payload['endpoint'], 0)
        self.assertEqual('PASS', before['status'])
        (self.root / 'ProjectSettings/ProjectSettings.asset').write_bytes(b'changed during run')
        after = runner.final_verification(self.root, self.build, self.receipt, receipt_hash, payload, payload['endpoint'], 0)
        self.assertEqual('FAIL', after['status']); self.assertFalse(after['sourceStillMatches'])


if __name__ == '__main__':
    unittest.main()
