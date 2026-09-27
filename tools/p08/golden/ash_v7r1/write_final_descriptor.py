"""Select ground-origin placement separately from the preserved UV-control import."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


receipt_path = ROOT / 'docs/p08/golden/unity/import-6564375159dc4cda9d727e69a2951f27.json'
receipt = json.loads(receipt_path.read_text())
assert receipt['passed'] and receipt['sourceBindingPassed']
base_path = ROOT / receipt['descriptor']
assert sha(base_path) == receipt['descriptorSha256']
base = json.loads(base_path.read_text())
asset = base['assets'][0]
assert len(base['assets']) == 1 and asset['id'] == 'RB_Golden_Ash_V7R1'
assert 'fallenRootOffset' not in asset
assert receipt['assets'][0]['passed'] and receipt['assets'][0]['clipsSampled'] == 13


def verify_rows(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            assert sha(ROOT / value['path']) == value['sha256'], value['path']
        for nested in value.values():
            verify_rows(nested)
    elif isinstance(value, list):
        for nested in value:
            verify_rows(nested)


verify_rows(asset)
final = copy.deepcopy(base)
final['purpose'] = 'Unaccepted AshV7R1 review candidate: native UV-only control passed separately. Explicit fallenRootOffset=0 selects authored ground origin without modifying geometry, animation, simulation or authoritative state. Mid-fall clip ground penetration and visual fidelity remain open.'
final_asset = final['assets'][0]
final_asset['id'] = 'RB_Golden_Ash_V7R1_GroundOrigin'
final_asset['fallenRootOffset'] = 0
output = ROOT / 'docs/p08/golden/ash/v7r1/descriptor-ground-origin.json'
payload = json.dumps(final, indent=2) + '\n'
if output.exists():
    assert output.read_text() == payload, 'Different final descriptor already exists'
else:
    output.write_text(payload)
handoff = {'schema': 1, 'source': final_asset['source'], 'fbx': final_asset['fbx'],
           'descriptor': {'path': output.relative_to(ROOT).as_posix(), 'sha256': sha(output)},
           'assetId': final_asset['id'], 'fallenRootOffset': 0,
           'preservedUvControlDescriptor': {'path': base_path.relative_to(ROOT).as_posix(), 'sha256': sha(base_path)},
           'preservedUvControlNativeReceipt': {'path': receipt_path.relative_to(ROOT).as_posix(), 'sha256': sha(receipt_path)},
           'uvControlSourceFingerprint': receipt['sourceFingerprint'], 'uvControlLegacyFallenRootOffset': -.55,
           'geometryAnimationTexturesUnchangedByPlacementSelection': True,
           'newDescriptorNativeImportPending': True, 'visualAccepted': False, 'performanceAccepted': False,
           'remainingFallClipDefect': 'Inherited clip reaches approximately -0.153m in the separate native root0 test; this metadata does not repair its articulation or ground contact.',
           'next': 'Root must refresh/recompile/audit changed importer code before importing this distinct descriptor. Keep the legacy placement control prefab/descriptor and native receipt intact.'}
(ROOT / 'docs/p08/golden/ash/v7r1/handoff.json').write_text(json.dumps(handoff, indent=2) + '\n')
print(json.dumps({'descriptor': handoff['descriptor'], 'assetId': handoff['assetId'], 'fallenRootOffset': 0, 'nativeImportPending': True}))
