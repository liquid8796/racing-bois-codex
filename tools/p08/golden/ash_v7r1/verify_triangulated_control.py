"""Independent diagnostic export audit; source and production files remain unchanged."""
from inspect_uv import ROOT, parse, audit, child
import array
import collections
import hashlib
import json


def digest_node(node, root=False):
    result = hashlib.sha256()
    result.update(node['name'].encode())
    for index, value in enumerate(node['properties']):
        if root and index == 0:
            continue  # FBX object IDs are randomized between Blender processes.
        if isinstance(value, str):
            value = value.replace('_RetainedBody.001\x00', '_RetainedBody\x00')
            value = value.replace('_local\\p08-ash-v7r1-staging\\', '_local\\p08-ash-v7-staging\\')
        if isinstance(value, array.array):
            result.update(value.typecode.encode())
            result.update(value.tobytes())
        elif isinstance(value, bytes):
            result.update(value)
        else:
            result.update(json.dumps(value, ensure_ascii=False).encode())
        result.update(b'\x00')
    for nested in node['children']:
        result.update(digest_node(nested).encode())
    return result.hexdigest()


def inspect_objects(path):
    objects = next(n for n in parse(path) if n['name'] == 'Objects')['children']
    stable = {}
    positions = {}
    ordinal = collections.Counter()
    for obj in objects:
        index = ordinal[obj['name']]
        ordinal[obj['name']] += 1
        if obj['name'] == 'Geometry' and obj['properties'][2] == 'Mesh':
            positions[obj['properties'][1].replace('_RetainedBody.001\x00', '_RetainedBody\x00')] = hashlib.sha256(child(obj, 'Vertices')['properties'][0].tobytes()).hexdigest()
            continue
        if obj['name'] in {'Model', 'NodeAttribute', 'Deformer', 'Geometry', 'AnimationCurve', 'AnimationCurveNode', 'AnimationLayer', 'AnimationStack', 'Material', 'Texture', 'Video'}:
            digest = obj['name'] + ':' + digest_node(obj, root=True)
            stable[digest] = stable.get(digest, 0) + 1
    return stable, positions


def main():
    original = ROOT / 'Assets/RacingBois/Art/P08/Golden/Ash/V7/RB_Golden_Ash_V7.fbx'
    control = ROOT / '_local/p08-ash-v7r1-staging/triangulated-diagnostic.fbx'
    before, before_positions = inspect_objects(original)
    after, after_positions = inspect_objects(control)
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    result = audit(control)
    report = {'control': result, 'nonMeshObjectCount': sum(before.values()), 'changedNonMeshObjects': changed,
              'comparisonNormalization': 'Ignore randomized root object IDs/order; remove exporter temporary mesh-name suffix .001; normalize expected absolute STRIP texture folder between export destinations. All remaining scalar/array data compared exactly as a multiset; connection mapping is a separate gate.',
              'meshPositionsExact': before_positions == after_positions,
              'originalSourceSha256': hashlib.sha256((ROOT / 'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend').read_bytes()).hexdigest(),
              'originalExportSha256': hashlib.sha256(original.read_bytes()).hexdigest(),
              'nativePending': True, 'visualAccepted': False}
    if changed or before_positions != after_positions:
        report['passed'] = False
        (ROOT / 'docs/p08/golden/ash/v7r1/triangulated-control-preservation-failed.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'changedNonMeshCount': len(changed), 'firstChangedNonMeshObjects': changed[:20], 'meshPositionsExact': before_positions == after_positions}))
    assert not changed and before_positions == after_positions
    assert all(not m['failures'] and m['nonTrianglePolygons'] == 0 for m in result['meshes'])
    report['passed'] = True
    (ROOT / 'docs/p08/golden/ash/v7r1/triangulated-control-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    descriptor = json.loads((ROOT / 'docs/p08/golden/ash/v7/descriptor.json').read_text())
    descriptor['purpose'] = 'Diagnostic triangulated export of unchanged frozen AshV7; native UV causal control pending; no visual acceptance.'
    asset = descriptor['assets'][0]
    asset['id'] = 'RB_Golden_Ash_V7R1_UvControl'
    old = asset['fbx']['path']
    asset['fbx'] = {'path': control.relative_to(ROOT).as_posix(), 'sha256': result['sha256']}
    for clip in asset['clips'] + asset.get('previewClips', []):
        if clip['path'].startswith(old):
            clip['path'] = clip['path'].replace(old, asset['fbx']['path'], 1)
            clip['sha256'] = result['sha256']
    (ROOT / 'docs/p08/golden/ash/v7r1/descriptor-control-staged.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('passed', 'nonMeshObjectCount', 'changedNonMeshObjects', 'meshPositionsExact', 'originalSourceSha256', 'originalExportSha256')}))
    print(result['sha256'])
    print([(m['name'], m['triangles'], m['nonTrianglePolygons'], len(m['failures'])) for m in result['meshes']])


if __name__ == '__main__':
    main()
