"""Bind concept/source/export and QA receipts without reading reference-game art."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'docs/p03/assets/source-manifest.json'


def file_record(path):
    data = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def receipt_payload(path):
    receipt = json.loads(path.read_text(encoding='utf-8'))
    for block in receipt['result']['content']:
        if block.get('type') == 'text' and '{' in block.get('text', ''):
            text = block['text']
            try:
                return json.loads(text[text.index('{'):])
            except json.JSONDecodeError:
                continue
    raise RuntimeError('Missing audit payload: ' + str(path))


files = []
for folder, patterns in [
    ('Assets/RacingBois/Art/Vehicles', ('*.fbx', '*.png', '*.meta')),
    ('Assets/RacingBois/Art/Characters', ('*.fbx', '*.png', '*.meta')),
    ('Assets/RacingBois/Art/Props/Canyon', ('*.fbx', '*.png', '*.meta')),
    ('ArtSource/Vehicles', ('*.blend',)),
    ('ArtSource/Characters', ('*.blend',)),
    ('ArtSource/Props/Canyon', ('*.blend',)),
    ('ArtSource/Concepts/P03P04', ('*-concept-v1.png', 'PROMPTS.md')),
    ('tools/p03/assets', ('*.py',)),
]:
    for pattern in patterns:
        files.extend(file_record(path) for path in sorted((ROOT / folder).glob(pattern)))

for name in ['RB_Motorcycle', 'RB_PoliceMotorcycle', 'RB_Rider', 'RB_TrafficCoupe',
             'RB_TrafficVan', 'RB_Pedestrian', 'RB_Sandstone', 'RB_SageScrub']:
    files.append(file_record(ROOT / 'Assets/RacingBois/Prefabs' / (name + '.prefab')))
for name in ['RB_RacePalette', 'RB_PolicePalette', 'RB_PedestrianPalette', 'RB_CanyonPalette']:
    files.append(file_record(ROOT / 'Assets/RacingBois/Materials' / (name + '.mat')))
files.append(file_record(ROOT / 'Assets/RacingBois/Editor/RaceAssetBuilder.cs'))

audits = []
for name, expected_meshes in [('independent-mesh-audit.json', 48),
                              ('independent-pedestrian-audit.json', 33),
                              ('independent-canyon-audit.json', 6)]:
    path = ROOT / 'docs/p03/assets' / name
    payload = receipt_payload(path)
    if not payload['passed'] or payload['mesh_count'] != expected_meshes:
        raise RuntimeError('Audit did not pass with expected coverage: ' + name)
    audits.append({**file_record(path), 'passed': True, 'mesh_count': payload['mesh_count'],
                   'bounds': payload['bounds']})

unity_path = ROOT / 'docs/p03/assets/unity-validation.json'
unity = json.loads(unity_path.read_text(encoding='utf-8'))
if not unity['passed'] or len(unity['assets']) != 8 or not all(asset['passed'] for asset in unity['assets']):
    raise RuntimeError('Unity did not validate all eight prefabs')

manifest = {
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'phase': 'P03/P04 concept-guided gameplay art',
    'authorship': 'Newly authored procedural geometry and palette textures; no reference-game art copied',
    'concept_model': 'Unspecified by exposed image-generation provider; not a verified GPT Image 2.5 identity',
    'sequence': 'Initial graybox archived; concept PNGs generated and visually inspected; geometry revised from concepts; Blender MCP export and independent geometry audit; Unity import validation separately recorded',
    'coordinate_contract': {
        'meters': True, 'unity_root': 'position0 rotationidentity scale1',
        'authoring_helper': 'Unity-intended (x,y,z) -> Blender (-x,-z,y)',
        'fbx': 'axis_forward=-Z, axis_up=Y, apply_unit_scale=True, FBX_SCALE_ALL, bake_space_transform=False',
        'unity': 'identity prefab root; Model child preserves imported rotation then premultiplies Y180; imported child scale1',
        'animation': 'Conjugate desired Unity rotation through Model local rotation; do not overwrite the conversion basis',
    },
    'material_budget': {'distinct_materials': 4, 'race_and_police_maps': 256,
                        'pedestrian_maps': 128, 'canyon_base': 128, 'canyon_surface_maps': 32},
    'qa': {'mesh_count': sum(audit['mesh_count'] for audit in audits), 'audits': audits,
           'unity': {**file_record(unity_path), 'passed': True, 'prefabs': 8, 'version': unity['unityVersion']}},
    'limitations': [
        'Gameplay art, not photoreal concept-render parity or complete P06 art acceptance',
        'Rigid articulated character parts, not final deforming Humanoid rig/cleaned animation clips',
        'Flat authored palette maps intentionally share UV tiles; no unique detail texture atlas claimed',
        'Geometry audit does not prove final browser frame-rate, memory or action-silhouette acceptance',
    ],
    'files': files,
}
DEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'manifest': str(DEST), 'files': len(files), 'audited_meshes': manifest['qa']['mesh_count']}))
