"""Bind the unaccepted Fall-only candidate and independently inspect its binary FBX."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools/p08/golden/ash_v7r1'))
from inspect_uv import parse, audit
from verify_export_connections import semantic
from verify_triangulated_control import digest_node


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_hashes(path):
    objects = next(n for n in parse(path) if n['name'] == 'Objects')['children']
    return {n['properties'][1]: digest_node(n, root=True) for n in objects if n['name'] == 'Geometry' and n['properties'][2] == 'Mesh'}


original = ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.fbx'
candidate = ROOT / '_local/p08-ash-v7r2-staging/RB_Golden_Ash_V7R2.fbx'
source = ROOT / 'ArtSource/P08/Golden/Ash/V7R2/RB_Golden_Ash_V7R2.blend'
before = semantic(original)
after = semantic(candidate)
assert mesh_hashes(original) == mesh_hashes(candidate), 'FBX mesh geometry, UV, normal or material-index data changed'
for field in ['skinClusters', 'shapeDeltas', 'orderedMaterialBindings']:
    assert before[field] == after[field], field
assert before['animationChannels'].keys() == after['animationChannels'].keys()
changed = [key for key in before['animationChannels'] if before['animationChannels'][key] != after['animationChannels'][key]]
assert changed and all(key.split('|')[1] == 'RB_Fall' for key in changed)
other_takes = sorted({key.split('|')[1] for key in before['animationChannels'] if key.split('|')[1] != 'RB_Fall'})
assert len(other_takes) == 12
numerical = audit(candidate)
assert all(not mesh['failures'] and not mesh['alternativeTriangulationFailures'] for mesh in numerical['meshes'])
descriptor = json.loads((ROOT / 'docs/p08/golden/ash/v7r1/descriptor-ground-origin.json').read_text())
descriptor['purpose'] = 'Unaccepted V7R2 Fall-only articulation/ground-placement candidate. Explicit fallenRootOffset0; unchanged character geometry/UV/maps/weights and other12actions. Source dense floor checks pass; actual native import/BakeMesh, transition/contact/visual/performance acceptance remain pending.'
asset = descriptor['assets'][0]
asset['id'] = 'RB_Golden_Ash_V7R2'
asset['source'] = {'path': source.relative_to(ROOT).as_posix(), 'sha256': sha(source)}
asset['fbx'] = {'path': candidate.relative_to(ROOT).as_posix(), 'sha256': sha(candidate)}
asset['fallenRootOffset'] = 0
for clip in asset['clips'] + asset.get('previewClips', []):
    clip['path'] = asset['fbx']['path']
    clip['sha256'] = asset['fbx']['sha256']
maps = {}
for material in asset['materials']:
    for value in material.values():
        if isinstance(value, dict) and 'path' in value and 'sha256' in value:
            assert sha(ROOT / value['path']) == value['sha256']
            maps[value['path']] = value['sha256']
for key in ['concept', 'conceptReview']:
    assert sha(ROOT / asset[key]['path']) == asset[key]['sha256']
frozen = {
    'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend': '3981a210d2e79ca9d5a2aa4cb511e174b81cf49c1f50280b4e8322be1e601578',
    'ArtSource/P08/Golden/Ash/V7R1/RB_Golden_Ash_V7R1.blend': '2fc56084ea261c46109e49ad6d76f515665d7b22d3e11daa9785c51179d74d6b',
    'ArtSource/Weapons/RB_Club.blend': '553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f'}
assert all(sha(ROOT / path) == digest for path, digest in frozen.items())
output = ROOT / 'docs/p08/golden/ash/v7r2/descriptor-staged.json'
data = json.dumps(descriptor, indent=2) + '\n'
if output.exists():
    assert output.read_text() == data
else:
    output.write_text(data)
report = {'passed': True, 'source': asset['source'], 'sourceBytes': source.stat().st_size, 'nativeCompressedSource': True,
          'fbx': asset['fbx'], 'descriptor': {'path': output.relative_to(ROOT).as_posix(), 'sha256': sha(output)},
          'fullMeshRecordsExactIncludingUvsNormals': True, 'skinClustersExact': len(before['skinClusters']),
          'shapeDeltasExact': len(before['shapeDeltas']), 'orderedMaterialBindingsExact': True,
          'otherAnimationTakesExact': other_takes, 'changedAnimationChannels': changed, 'changesOnlyInTake': 'RB_Fall',
          'numericMeshAudit': numerical, 'unchangedMapHashes': maps, 'preservedOriginals': frozen,
          'actualRenders': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in sorted((ROOT / 'docs/p08/golden/ash/v7r2/renders').glob('*.png'))],
          'nativePending': True, 'visualAccepted': False, 'performanceAccepted': False,
          'scope': 'Independent FBX mesh/skin/shape/animation binding preservation and source/render pins. Changes limited to exported Fall take; all other12takes unchanged. Actual native comparison is a separate gate.'}
assert len(report['actualRenders']) == 9
(ROOT / 'docs/p08/golden/ash/v7r2/handoff.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': True, 'source': report['source'], 'sourceBytes': report['sourceBytes'], 'fbx': report['fbx'], 'descriptor': report['descriptor'], 'otherTakesExact': len(other_takes), 'changedFallExportChannels': len(changed)}))
