"""Synthetic receipt/file contracts only; never native build, preservation or acceptance proof."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import audit_desktop as candidate


class ScopedDesktopReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = patch.object(candidate, 'PROJECT', self.root)
        self.project.start()
        self.attempt = 'a' * 32
        self.owned = candidate.OWNED_PREFIX + self.attempt
        self.player = self.root / 'Build/contract-player'
        self.rows = {}
        roots = [self.owned + '/Race.unity', self.owned + '/DesktopPipeline.asset']
        originals = ['Assets/RacingBois/UI/Race.uxml', 'Assets/RacingBois/Settings/MainPanel.asset']
        originals += ['Assets/RacingBois/UI/Fonts/NotoSans-' + weight + suffix for weight in ['Regular', 'ExtraBold'] for suffix in ['.ttf', ' SDF.asset']]
        for path in originals:
            self.source(path)
            self.source(path + '.meta')
        original_rows = [self.rows[path] for path in sorted(self.rows)]
        copied = {path: self.owned + '/Ui/Mirror/' + path for path in originals}
        dependencies = roots + list(copied.values()) + [self.owned + '/Ui/OwnedPanelTextSettings.asset']
        for path in dependencies:
            self.source(path)
        for path in candidate.SOURCE_SETTINGS | {candidate.UNITY_DEPENDENCY_ROOTS[1], 'ProjectSettings/ProjectVersion.txt', candidate.CORPUS}:
            self.source(path, b'{"dependencies":{}}' if path == 'Packages/packages-lock.json' else None)
        for logical in candidate.SCOPED_SETTINGS:
            leaf = Path(logical).name
            original = (self.root / logical).read_bytes()
            self.file('Build/contract-player/BuildEvidence/original/' + leaf, original)
            self.file('Build/contract-player/BuildEvidence/restored/' + leaf, original)
            effective = b'effective settings fixture: ' + logical.encode()
            self.file('Build/contract-player/BuildEvidence/effective/' + leaf, effective)
            self.rows[logical] = self.row(logical, effective)
        self.source('Assets/RacingBois/Client/Fixture.cs')
        self.source('Assets/RacingBois/Client/Fixture.asmdef')
        self.source('Packages/com.racingbois.foundation/Fixture.cs')
        assemblies = []
        for name in candidate.DESKTOP_ASSEMBLIES:
            path = 'Library/ScriptAssemblies/' + name + '.dll'
            self.source(path); self.source(path[:-4] + '.pdb')
            assemblies.append({'name': name, 'path': path, 'passed': True, 'pdbMatchesAssembly': True, 'sha256': self.rows[path]['sha256'], 'pdbSha256': self.rows[path[:-4] + '.pdb']['sha256'], 'documents': [dict(self.rows['Assets/RacingBois/Client/Fixture.cs'], matches=True)]})
        proof = 'docs/p08/desktop/contract-compiled.json'
        self.source(proof, json.dumps({'schema': 1, 'passed': True, 'assemblies': assemblies}).encode())
        self.source('Build/Content-desktop/manifest.json')
        self.source('tools/p08/desktop/RacingBois.runtime.json')
        self.ui = {'ownedRoot': self.owned + '/Ui', 'protectedOriginalsPreserved': True, 'dependencyClosurePassed': True, 'failure': '',
                   'originalInputs': {row['path']: row['sha256'] for row in original_rows}, 'copiedPaths': copied, 'fonts': []}
        for weight in ['Regular', 'ExtraBold']:
            self.ui['fonts'].append({'path': copied['Assets/RacingBois/UI/Fonts/NotoSans-' + weight + ' SDF.asset'],
                                     'sourceFontPath': copied['Assets/RacingBois/UI/Fonts/NotoSans-' + weight + '.ttf'], 'missing': [], 'ownershipPassed': True, 'corpusAdded': True})
        self.save_ui()
        self.file('Build/contract-player/BuildEvidence/font-preservation.json', json.dumps({'state': 'restored', 'globalSelection': True, 'restored': True, 'sourceBytesPreserved': True, 'memoryAndAtlasPreserved': True, 'failures': []}).encode())
        self.receipt = {'unityDependencySchema': 3, 'attemptId': self.attempt, 'ownedRoot': self.owned, 'scene': roots[0], 'pipeline': roots[1],
                        'unityDependencyRoots': roots, 'unityVersion': '6000.5.7f1', 'unityPackages': [], 'unityBuiltInDependencies': [],
                        'unityDependencies': [dict(self.rows[path], assetPath=path) for path in sorted(dependencies)],
                        'output': 'Build/contract-player', 'ownedUiEvidence': 'BuildEvidence/owned-ui.json', 'originalUiInputs': original_rows,
                        'restorationErrors': [], 'changedDuringBuild': [], 'failureCode': '', 'compileProof': proof,
                        'p08Accepted': False, 'releaseAccepted': False}
        self.receipt['loadedScenesBefore'] = self.receipt['loadedScenesAfter'] = '{"setup":[],"savedFiles":[]}'
        self.receipt['manifestSha256'] = self.rows['Build/Content-desktop/manifest.json']['sha256']
        for flag in ['editorStateRestored', 'unrelatedDirtyAssetsPreserved', 'fontPreservationPassed', 'originalUiPreserved', 'ownedFontStatePreserved', 'loadedScenesPreserved', 'sourceBindingPassed']:
            self.receipt[flag] = True
        self.receipt['sourceFiles'] = [self.rows[path] for path in sorted(self.rows)]
        self.receipt['sourceFilesAfter'] = copy.deepcopy(self.receipt['sourceFiles'])
        self.receipt['sourceFingerprint'] = hashlib.sha256('\n'.join(row['path'] + ' ' + row['sha256'] for row in self.receipt['sourceFiles']).encode()).hexdigest()
        self.receipt['unityDependencyFingerprint'] = candidate.dependency_fingerprint(self.receipt)

    def tearDown(self):
        self.project.stop(); self.temp.cleanup()

    def row(self, path, data):
        return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def file(self, path, data):
        target = self.root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)

    def source(self, path, data=None):
        data = data if data is not None else b'explicit synthetic file: ' + path.encode()
        self.file(path, data); self.rows[path] = self.row(path, data)

    def save_ui(self):
        self.file('Build/contract-player/BuildEvidence/owned-ui.json', json.dumps(self.ui).encode())

    def reject(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            candidate.audit_sources(self.receipt)

    def test_effective_settings_bound_with_original_restored(self):
        candidate.audit_sources(self.receipt)

    def test_original_scene_cannot_be_consumed(self):
        self.receipt['unityDependencies'].append(dict(self.rows[candidate.UNITY_DEPENDENCY_ROOTS[0]], assetPath=candidate.UNITY_DEPENDENCY_ROOTS[0]))
        self.reject()

    def test_original_font_cannot_be_consumed(self):
        path = 'Assets/RacingBois/UI/Fonts/NotoSans-Regular SDF.asset'
        self.receipt['unityDependencies'].append(dict(self.rows[path], assetPath=path)); self.reject()

    def test_owned_root_cannot_be_reassigned(self):
        self.receipt['ownedRoot'] = candidate.OWNED_PREFIX + 'b' * 32; self.reject()

    def test_original_font_drift_rejected(self):
        self.file('Assets/RacingBois/UI/Fonts/NotoSans-Regular SDF.asset', b'changed'); self.reject()

    def test_effective_settings_drift_rejected(self):
        self.file('Build/contract-player/BuildEvidence/effective/QualitySettings.asset', b'changed'); self.reject()

    def test_restored_settings_drift_rejected(self):
        self.file('Build/contract-player/BuildEvidence/restored/GraphicsSettings.asset', b'changed'); self.reject()

    def test_current_settings_must_equal_restored_original(self):
        self.file('ProjectSettings/ProjectSettings.asset', b'changed'); self.reject()

    def test_pack_changed_since_build_rejected(self):
        self.file('Build/Content-desktop/manifest.json', b'changed'); self.reject()

    def test_installed_pack_cannot_come_from_another_valid_manifest(self):
        self.receipt['manifestSha256'] = 'b' * 64; self.reject()

    def test_missing_source_after_or_changed_union_rejected(self):
        self.receipt['sourceFilesAfter'].pop(); self.reject()

    def test_missing_glyphs_rejected(self):
        self.ui['fonts'][0]['missing'] = [65]; self.save_ui(); self.reject()

    def test_original_ttf_reference_rejected(self):
        self.ui['fonts'][0]['sourceFontPath'] = 'Assets/RacingBois/UI/Fonts/NotoSans-Regular.ttf'; self.save_ui(); self.reject()

    def test_preservation_failure_cannot_pass(self):
        self.receipt['restorationErrors'] = ['fonts:failed']; self.reject()

    def test_cannot_grant_release_acceptance(self):
        self.receipt['releaseAccepted'] = True; self.reject()

    def test_changed_compiled_dll_rejected(self):
        self.file('Library/ScriptAssemblies/RacingBois.Authoring.Editor.dll', b'changed'); self.reject()

    def test_loaded_scene_setup_change_rejected(self):
        self.receipt['loadedScenesAfter'] = '{"setup":[{"path":"","loaded":true,"active":true}],"savedFiles":[]}'
        self.reject()

    def test_unverified_owned_font_memory_rejected(self):
        self.receipt['ownedFontStatePreserved'] = False; self.reject()

    def test_original_font_meta_drift_rejected(self):
        self.file('Assets/RacingBois/UI/Fonts/NotoSans-Regular SDF.asset.meta', b'changed'); self.reject()


if __name__ == '__main__':
    unittest.main()
