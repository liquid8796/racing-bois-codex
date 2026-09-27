"""Hash-bound R4 candidate handoff. Publication is an explicit root-owned step."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/p08/golden/apex/r4'
NAME = 'RB_Golden_Apex_r4'
DEST = 'Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/'
SOURCE = 'ArtSource/P08/Golden/Apex/V8/R4/'
STAGED = '_local/p08-apex-r4-staging/' + NAME + '.fbx'
parser = argparse.ArgumentParser()
parser.add_argument('--publish', action='store_true')
args = parser.parse_args()

def bind(path):
    file = ROOT / path
    return {'path': file.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}

def receipt(path, marker):
    raw = json.loads((DOC / path).read_text(encoding='utf8'))
    text = '\n'.join(block.get('text', '') for block in raw['result']['content'])
    return json.JSONDecoder().raw_decode(text.partition(marker)[2])[0]

audit = receipt('audit-final-clean-mcp.json', 'APEX_R4_GEOMETRY_AUDIT ')
roundtrip = receipt('roundtrip-final-mcp.json', 'APEX_R4_ROUNDTRIP ')
for mesh in audit['meshes']:
    assert mesh['unityDegenerateTriangles'] == mesh['zeroAreaUVTriangles'] == mesh['nonManifoldEdges'] == 0, mesh['name']
assert roundtrip['passed'] and roundtrip['exactPerMeshTriangleCounts'] and roundtrip['exactRendererCoverage']
intent = json.loads((ROOT / SOURCE / 'Textures/surface-intent.json').read_text())
declared = {row['material']: row for row in intent['materials']}
copies = [{'source': bind(STAGED), 'destination': DEST + NAME + '.fbx'}]
materials = []
for name in sorted({m for mesh in audit['meshes'] for m in mesh['materials']}):
    assert name in declared and '.' not in name
    material = {'sourceName': name, 'normalScale': .25, 'maxSize': declared[name]['size'],
                'transparent': name in ['Apex_Glass', 'Apex_Lens'],
                'opacity': .42 if name == 'Apex_Glass' else .08 if name == 'Apex_Lens' else 1,
                'doubleSided': False}
    for field in ['baseColor', 'normal', 'metallicSmoothness', 'emission']:
        source = declared[name]['maps'].get(field)
        if source is None:
            continue
        assert bind(source['path']) == source, 'Texture changed after surface-intent receipt'
        target = DEST + Path(source['path']).name
        material[field] = {'path': target, 'sha256': source['sha256']}
        copies.append({'source': source, 'destination': target})
    if 'emission' in material:
        material['emissionIntensity'] = 2 if name == 'Apex_Lamp' else 1.5
    materials.append(material)

size = audit['unityIntendedSize']
asset = {'id': NAME, 'kind': 'bike', 'concept': bind('ArtSource/Concepts/P08/Golden/apex-v2.png'),
         'conceptReview': bind('ArtSource/Concepts/P08/Golden/apex-v2-review.md'),
         'source': bind(SOURCE + NAME + '_assembled.blend'),
         'fbx': {'path': DEST + NAME + '.fbx', 'sha256': bind(STAGED)['sha256']},
         'restPose': 'file', 'modelRotationEuler': dict.fromkeys('xyz', 0),
         'minimumSize': dict(zip('xyz', [v - .02 for v in size])),
         'maximumSize': dict(zip('xyz', [v + .02 for v in size])), 'materials': materials,
         'lods': [{'height': height, 'rendererPaths': ['Apex_L%d_Body' % level,
                   NAME + '_Wheel_Front/Apex_L%d_Front' % level, NAME + '_Wheel_Rear/Apex_L%d_Rear' % level]}
                  for level, height in enumerate([.30, .115, .018])],
         'forwardMarker': 'Forward', 'leftMarker': 'Semantic_Left', 'rightMarker': 'Semantic_Right',
         'groundMarkers': ['Ground_Front', 'Ground_Rear'],
         'wheelPivots': [NAME + '_Wheel_Front', NAME + '_Wheel_Rear'],
         'colliders': [{'type': 'box', 'center': {'x': 0, 'y': .51, 'z': 0}, 'size': {'x': .45, 'y': 1.02, 'z': 1.95}}],
         'isStatic': False}
descriptor = {'schema': 1, 'assets': [asset]}
before = json.loads((DOC / 'before-manifest.json').read_text())
preserved = [{**item, 'unchanged': bind(item['path']) == item} for item in before['paths']]
assert all(item['unchanged'] for item in preserved), 'A bound concept/R3/Club input changed'
recipe = ['apex_r4_prepare.py', 'apex_r4_tank_fairing.py', 'apex_r4_cowl.py', 'apex_r4_tail.py',
          'apex_r4_seat_clearance.py', 'apex_r4_textures.py', 'apex_r4_materials.py',
          'apex_r4_surface_detail.py', 'apex_r4_finish_surfaces.py', 'apex_r4_source_cleanup.py',
          'apex_r4_assemble.py', 'apex_r4_audit_final.py', 'apex_r4_export_staged.py', 'apex_r4_roundtrip.py']
manifest = {'schema': 1, 'status': 'staged_for_native_comparison', 'visualAccepted': False,
            'licensedGeometryImported': False, 'stagedFbx': bind(STAGED), 'copiesForPublication': copies,
            'descriptorAfterCopy': descriptor, 'editableSource': bind(SOURCE + NAME + '_editable.blend'),
            'surfaceIntent': bind(SOURCE + 'Textures/surface-intent.json'), 'preservedInputs': preserved,
            'physicalRoundtripTriangles': roundtrip['triangles'], 'minimumRoundtripCrossSquared': roundtrip['minimumWorldCrossSquared'],
            'actualLodTriangles': [sum(mesh['triangles'] for mesh in audit['meshes'] if '_L%d_' % level in mesh['name']) for level in range(3)],
            'code': [bind('tools/p08/golden/' + name) for name in recipe],
            'scope': 'Original project-authored candidate, using external models only as references. Native Unity/visual/performance acceptance pending; no promotion masks changed.'}
(DOC / 'handoff-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
if args.publish:
    # Validate every destination before the first copy; never replace a different
    # published candidate or any older version.
    for item in copies:
        target = ROOT / item['destination']
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest() == item['source']['sha256'], str(target)
    for item in copies:
        target = ROOT / item['destination']
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(ROOT / item['source']['path'], target)
        assert bind(item['destination'])['sha256'] == item['source']['sha256']
    (DOC / 'descriptor.json').write_text(json.dumps(descriptor, indent=2) + '\n')
    print('R4 published for root-owned native comparison; NOT accepted.')
else:
    print('R4 staged only. Root may publish with --publish when Unity is ready.')
print(json.dumps({'fbx': manifest['stagedFbx'], 'lodTriangles': manifest['actualLodTriangles'], 'materials': len(materials),
                  'copies': len(copies), 'protectedInputsUnchanged': True, 'visualAccepted': False}))
