"""Freeze the seam-only Apex R5 candidate; --publish is a separate root-owned import preparation."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/p08/golden/apex/r5'
SOURCE = 'ArtSource/P08/Golden/Apex/R5/'
NAME = 'RB_Golden_Apex_r5'
STAGED = '_local/p08-apex-r5-staging/' + NAME + '.fbx'
DEST = 'Assets/RacingBois/Art/P08/Golden/Apex/R5/' + NAME + '.fbx'


def bind(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def read_receipt(path, marker):
    raw = json.loads((DOC / path).read_text(encoding='utf8'))
    assert not raw['result'].get('isError', False), path
    text = '\n'.join(block.get('text', '') for block in raw['result']['content'])
    return json.JSONDecoder().raw_decode(text.split(marker, 1)[1])[0]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--publish', action='store_true'); args = parser.parse_args()
    audit = read_receipt('audit01-mcp.json', 'APEX_R5_GEOMETRY_AUDIT ')
    roundtrip = read_receipt('roundtrip01-mcp.json', 'APEX_R5_ROUNDTRIP ')
    seam = read_receipt('seam01-04-mcp.json', 'R5_SEAM=')
    before = json.loads((DOC / 'r4-component-diagnosis.json').read_text(encoding='utf8'))
    assert len(audit['meshes']) == 9 and all(row['nonManifoldEdges'] == row['zeroAreaTriangles'] == row['zeroAreaUVTriangles'] == row['unityDegenerateTriangles'] == 0 for row in audit['meshes'])
    assert roundtrip['passed'] and roundtrip['exactRendererCoverage'] and roundtrip['exactPerMeshTriangleCounts']
    assert seam['nonManifoldEdges'] == 0 and len(seam['intersections']) == 8 and all(row['trianglePairs'] == 0 for row in seam['intersections'])
    frozen = json.loads((DOC / 'preserved-inputs-before.json').read_text(encoding='utf8'))['files']
    assert all(bind(row['path']) == row for row in frozen), 'Original R4/concept/Club bytes changed'
    descriptor = json.loads((ROOT / 'docs/p08/golden/apex/r4/descriptor.json').read_text(encoding='utf8'))
    asset = descriptor['assets'][0]
    assert asset['concept']['sha256'] == 'f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819'
    asset['id'] = NAME
    asset['source'] = bind(SOURCE + NAME + '_assembled.blend')
    asset['fbx'] = {'path': DEST, 'sha256': bind(STAGED)['sha256']}
    asset['wheelPivots'] = [path.replace('RB_Golden_Apex_r4', NAME) for path in asset['wheelPivots']]
    for lod in asset['lods']:
        lod['rendererPaths'] = [path.replace('RB_Golden_Apex_r4', NAME) for path in lod['rendererPaths']]
    for material in asset['materials']:
        for value in material.values():
            if isinstance(value, dict) and 'path' in value:
                assert bind(value['path']) == value, 'Existing R4 finish map changed'
    renders = ['01-quarter.png', '01-side.png', '02-lod0-quarter.png', '02-lod1-quarter.png', '02-lod2-quarter.png']
    manifest = {
        'schema': 1, 'status': 'staged_for_native_comparison', 'visualAccepted': False,
        'scope': 'Only the original project-authored belly shell is replaced to clear unchanged R4 fairing/vent geometry. Native Unity and full concept acceptance remain open.',
        'lockedConcept': asset['concept'], 'editableSource': bind(SOURCE + NAME + '_editable01.blend'),
        'assembledSource': asset['source'], 'stagedFbx': bind(STAGED),
        'copiesForPublication': [{'source': bind(STAGED), 'destination': DEST}],
        'descriptorAfterCopy': descriptor, 'materialPolicy': 'Reuse exact published R4 texture bytes and material declarations; no new paint or shading revision.',
        'r4IntersectingTrianglePairs': sum(row['intersectingTrianglePairs'] for row in before['bellyIntersections']),
        'r5IntersectingTrianglePairs': sum(row['trianglePairs'] for row in seam['intersections']),
        'intersectionScope': 'Editable belly vs both main fairings, both lower diagonal vent walls/plenums and both upper intake returns; not a universal whole-bike intersection audit.',
        'lodTriangles': [sum(row['triangles'] for row in audit['meshes'] if '_L%d_' % i in row['name']) for i in range(3)],
        'exactFbxRoundtrip': roundtrip, 'preservedInputs': frozen,
        'renders': [bind('docs/p08/golden/apex/r5/' + path) for path in renders],
        'recipes': [bind(path.relative_to(ROOT).as_posix()) for path in sorted((ROOT / 'tools/p08/golden').glob('apex_r5*.py'))]
    }
    output = DOC / 'handoff-manifest.json'
    if output.exists():
        assert json.loads(output.read_text(encoding='utf8')) == manifest, 'Frozen handoff changed; use a new revision'
    else:
        output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    if args.publish:
        target = ROOT / DEST
        if target.exists():
            assert bind(DEST)['sha256'] == asset['fbx']['sha256'], 'Refusing to overwrite a different published candidate'
        else:
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / STAGED, target)
        assert bind(DEST) == asset['fbx']
        descriptor_path = DOC / 'descriptor.json'
        if descriptor_path.exists():
            assert json.loads(descriptor_path.read_text(encoding='utf8')) == descriptor, 'Existing descriptor differs'
        else:
            descriptor_path.write_text(json.dumps(descriptor, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': manifest['status'], 'fbx': manifest['stagedFbx'], 'lodTriangles': manifest['lodTriangles'],
                      'intersectionPairsBeforeAfter': [manifest['r4IntersectingTrianglePairs'], manifest['r5IntersectingTrianglePairs']],
                      'published': args.publish, 'visualAccepted': False}))


if __name__ == '__main__':
    main()
