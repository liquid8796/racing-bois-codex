"""Bind the real Spark export to a staged Unity descriptor; never write Assets."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/p08/golden/spark/v1'
STAGE = ROOT / '_local/p08-spark-v1-staging'
TEXTURES = ROOT / 'ArtSource/P08/Golden/Spark/V1/Textures'
ASSET_DESTINATION = Path('Assets/RacingBois/Art/P08/Golden/Spark/V1')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)}


def receipt_result(filename, prefix):
    receipt = json.loads((DOC / filename).read_text(encoding='utf-8'))
    for content in receipt['result']['content']:
        if content.get('type') == 'text' and prefix in content['text']:
            return json.JSONDecoder().raw_decode(content['text'].split(prefix, 1)[1])[0]
    raise RuntimeError('Missing actual MCP observation: ' + prefix)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    source_audit = receipt_result('audit-export-03-mcp.json', 'SPARK_SOURCE_AUDIT=')
    roundtrip = receipt_result('roundtrip-03-mcp.json', 'SPARK_FBX_ROUNDTRIP=')
    if not source_audit['passed'] or not roundtrip['passed']:
        raise RuntimeError('Source and real FBX roundtrip must both pass before staging')
    before = json.loads((DOC / 'before-manifest.json').read_text())
    for item in before['inputs']:
        if digest(ROOT / item['path']) != item['sha256']:
            raise RuntimeError('Protected/reference input changed: ' + item['path'])
    write(DOC / 'source-audit-final.json', source_audit)
    write(DOC / 'fbx-roundtrip-final.json', roundtrip)
    failed = receipt_result('roundtrip-02-mcp.json', 'SPARK_FBX_ROUNDTRIP=')
    write(DOC / 'fbx-roundtrip-failed-01.json', failed)
    staged = []
    constant_maps = []
    material_specs = []
    STAGE.mkdir(parents=True, exist_ok=True)
    fbx = STAGE / 'RB_Golden_Spark_v1.fbx'
    staged.append({'staged': file_ref(fbx), 'destination': (ASSET_DESTINATION / fbx.name).as_posix()})
    for material in source_audit['materials']:
        name = material['name']
        spec = {'sourceName': name, 'maxSize': 512, 'normalScale': 1.0,
                'transparent': name == 'Spark_Lens', 'opacity': .18 if name == 'Spark_Lens' else 1.0,
                'doubleSided': False, 'emissionIntensity': material['emissionStrength']}
        roles = {'baseColor': 'BaseColor', 'normal': 'Normal', 'metallicSmoothness': 'MetallicSmoothness'}
        if (TEXTURES / (name + '_Emission.png')).exists():
            roles['emission'] = 'Emission'
        for role, suffix in roles.items():
            original = TEXTURES / (name + '_' + suffix + '.png')
            destination = STAGE / original.name
            shutil.copyfile(original, destination)
            assert digest(original) == digest(destination)
            spec[role] = {'path': (ASSET_DESTINATION / original.name).as_posix(), 'sha256': digest(original)}
            with Image.open(original) as image:
                dimensions = list(image.size)
                extrema = image.getextrema()
                if image.mode not in ('RGB', 'RGBA'):
                    raise RuntimeError('Unexpected runtime map channels: ' + str(original))
                constant = all(minimum == maximum for minimum, maximum in extrema)
                spec['maxSize'] = max(spec['maxSize'], *dimensions)
                if min(dimensions) < 256:
                    if not constant:
                        raise RuntimeError('Undersized map is not a constant field: ' + str(original))
                    constant_maps.append({'material': name, 'role': role, 'input': file_ref(original),
                                          'destination': spec[role]['path'], 'dimensions': dimensions,
                                          'mode': image.mode, 'channelValues': [lo for lo, hi in extrema],
                                          'allPixelsIdentical': True})
            staged.append({'source': file_ref(original), 'staged': file_ref(destination),
                           'destination': spec[role]['path'], 'dimensions': dimensions})
        material_specs.append(spec)
    size = source_audit['intendedUnitySize']
    spec = {'id': 'RB_Golden_Spark_v1', 'kind': 'bike',
            'concept': file_ref(ROOT / 'ArtSource/Concepts/P08/Golden/spark-v1.png'),
            'conceptReview': file_ref(DOC / 'DESIGN_REVIEW.md'),
            'source': file_ref(ROOT / 'ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_export.blend'),
            'fbx': {'path': staged[0]['destination'], 'sha256': digest(fbx)},
            'restPose': 'file', 'lightmapUv': 'generated', 'modelRotationEuler': {'x': 0, 'y': 0, 'z': 0},
            'minimumSize': dict(zip('xyz', [v - .02 for v in size])),
            'maximumSize': dict(zip('xyz', [v + .02 for v in size])),
            'maximumBelowGround': .04, 'materials': material_specs,
            'lods': [{'height': height, 'rendererPaths': ['Spark_L%d_Body' % level,
                      'RB_Golden_Spark_v1_Wheel_Front/Spark_L%d_Front' % level,
                      'RB_Golden_Spark_v1_Wheel_Rear/Spark_L%d_Rear' % level]}
                     for level, height in enumerate((.3, .115, .018))],
            'forwardMarker': 'Forward', 'leftMarker': 'Semantic_Left', 'rightMarker': 'Semantic_Right',
            'groundMarkers': ['Ground_Front', 'Ground_Rear'],
            'wheelPivots': ['RB_Golden_Spark_v1_Wheel_Front', 'RB_Golden_Spark_v1_Wheel_Rear'],
            'colliders': [{'type': 'box', 'center': {'x': 0, 'y': .6, 'z': 0},
                           'size': {'x': .95, 'y': 1.2, 'z': 2.14}}], 'isStatic': False}
    descriptor = {'schema': 1, 'assets': [spec]}
    write(DOC / 'descriptor.json', descriptor)
    write(DOC / 'constant-map-declarations.json', {'schema': 1, 'maps': constant_maps,
          'sourceBytesPreserved': True, 'importerCurrentlyRejectsDimensionsBelow256': True,
          'visualAccepted': False})
    delivery = {'schema': 1, 'status': 'staged; Unity import blocked by explicit constant-map size contract',
                'assetsWritten': False, 'visualAccepted': False, 'unityImportVerified': False,
                'descriptor': file_ref(DOC / 'descriptor.json'), 'payload': staged,
                'source': spec['source'], 'protectedAndReferenceInputsVerified': before['inputs'],
                'sourceAuditReceipt': file_ref(DOC / 'audit-export-03-mcp.json'),
                'roundtripReceipt': file_ref(DOC / 'roundtrip-03-mcp.json'),
                'originalAssembledSource': file_ref(ROOT / 'ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_assembled.blend'),
                'lodTriangles': source_audit['lodTriangles'], 'constantMapsBelow256': len(constant_maps),
                'maximumRoundtripVertexDeltaMetres': max(r['maximumBidirectionalVertexDistanceMetres'] for r in roundtrip['objects']),
                'materialTranslationLimits': [
                    'Blender Copper/Cream coat response is not represented by the current URP Lit descriptor.',
                    'Blender Lens transmission=1/IOR=1.46 is not represented by URP Lit alpha blending. Descriptor alpha0.18 is an explicitly unverified preview trial.',
                    'Normal/roughness maps and emission numeric strengths are preserved; renderer and compression appearance remain unverified.'],
                'requiredNextChecks': ['Root-owned explicit constant-map importer contract',
                    'Root-owned exact-hash copy to Assets and actual Unity import',
                    'Unity forward/left/right, wheel/rider clearance, compressed material and LOD renders',
                    'Actual corresponding-view concept comparison; native performance validation']}
    write(DOC / 'staged-delivery.json', delivery)
    print(json.dumps({'passedSourceAndRoundtrip': True, 'payloadFiles': len(staged),
                      'constantMapsBelow256': len(constant_maps), 'lodTriangles': source_audit['lodTriangles'],
                      'descriptor': file_ref(DOC / 'descriptor.json'), 'assetsWritten': False,
                      'visualAccepted': False}, indent=2))


if __name__ == '__main__':
    main()
