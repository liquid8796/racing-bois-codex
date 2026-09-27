"""Prepare/recheck a frozen review descriptor; only root may invoke explicit publish.

No Unity commands, production mappings, masks, acceptance files or existing assets
are modified. The publish command copies one new, hash-bound FBX into Assets.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT / 'docs/p08/golden/canyon/v17'
SOURCE = 'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.blend'
FBX = 'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.fbx'
DESTINATION = 'Assets/RacingBois/Art/P08/Golden/Canyon/V17/RB_Golden_Canyon.fbx'
ASSET_ID = 'RB_Golden_Canyon_v17'
HANDOFF = DOC / 'candidate05-publication.json'
LOCKED = {
    'ArtSource/Concepts/P08/Golden/canyon-v2.png': '83273dae6721d9f2c6f5d6bf4a6f39146322d8efeabc5cec0cb332e5a1cfa610',
    'ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend': 'c7681657df4666b13d22a15adbfaa17b42fd7413b8d4294a3cada4eb485cc01c',
    'ArtSource/Weapons/RB_Club.blend': '553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f',
}


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def row(path: str | Path) -> dict:
    target = (ROOT / path).resolve()
    require(target.is_relative_to(ROOT.resolve()) and target.is_file(), f'Missing/outside input: {path}')
    return {'path': target.relative_to(ROOT).as_posix(), 'sha256': digest(target)}


def verify(item: dict) -> None:
    require(row(item['path']) == item, f'Bound input changed: {item["path"]}')


def verify_locked() -> None:
    for path, expected in LOCKED.items():
        require(digest(ROOT/path) == expected, f'Locked/protected input changed: {path}')


def decode_mcp(path: Path, marker: str) -> dict:
    payload = json.loads(path.read_text(encoding='utf-8'))
    require(not payload['result'].get('isError', False), f'MCP result failed: {path}')
    output = payload['result']['structuredContent']['result']
    require(marker in output, f'Expected native result marker absent: {path}')
    return json.loads(output.split(marker, 1)[1])


def write_fresh_json(path: Path, value: dict) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode('utf-8')
    if path.exists():
        require(path.read_bytes() == payload, f'Frozen output exists with different bytes: {path}')
    else:
        with path.open('xb') as stream:
            stream.write(payload)


def prepare() -> dict:
    verify_locked()
    require(not HANDOFF.exists(), 'Publication is already frozen; use verify, never regenerate it in place.')
    audit = decode_mcp(DOC/'candidate05-source-audit.json', 'CANYON_SOURCE_AUDIT05 ')
    fbx_audit = decode_mcp(DOC/'candidate05-fbx-roundtrip.json', 'CANYON_V17_ROUNDTRIP05 ')
    require(audit['geometryChecksPassed'] and not audit['visualAccepted'], 'Source audit failed or wrongly accepted.')
    require(fbx_audit['passed'] and not fbx_audit['visualAccepted']
            and not fbx_audit['exportedToAssets'] and fbx_audit['exactRendererCoverage']
            and fbx_audit['exactPerMeshTriangleCounts'] and fbx_audit['exactObjectMeshMaterialImageMembershipRestored'],
            'Strict actual FBX audit/restoration must pass first.')
    require(fbx_audit['collapsedUvTriangles'] == 0 and fbx_audit['degeneratePhysicalTriangles'] == 0
            and fbx_audit['uvThresholdStrictlyGreaterThan'] == 1e-14
            and fbx_audit['physicalCrossSquaredThresholdStrictlyGreaterThan'] == 1e-16,
            'Native geometry/UV thresholds differ from the reviewed contract.')
    require(audit['source'].replace('\\', '/') == str(ROOT/SOURCE).replace('\\', '/'), 'Audit source differs.')
    require(fbx_audit['source'].replace('\\', '/') == str(ROOT/SOURCE).replace('\\', '/')
            and fbx_audit['fbx'].replace('\\', '/') == str(ROOT/FBX).replace('\\', '/'), 'FBX audit identity differs.')
    image = (DOC/'candidate05-gameplay.png').read_bytes()
    require(image[:8] == b'\x89PNG\r\n\x1a\n' and int.from_bytes(image[16:20], 'big') == 1536
            and int.from_bytes(image[20:24], 'big') == 717, 'Frozen corresponding-view render dimensions differ.')
    old_descriptor_path = ROOT/'docs/p08/golden/canyon/v16/descriptor.json'
    old_descriptor = json.loads(old_descriptor_path.read_text(encoding='utf-8'))
    asset = copy.deepcopy(old_descriptor['assets'][0])
    require(asset['concept']['sha256'] == LOCKED[asset['concept']['path']], 'Reference binding changed.')
    for material in asset['materials']:
        for value in material.values():
            if isinstance(value, dict) and 'path' in value:
                verify(value)
    actual_materials = {name for mesh in audit['objects'] for name in mesh['materials']}
    require(actual_materials == {material['sourceName'] for material in asset['materials']}, 'Material map coverage changed.')
    require(len(audit['objects']) == 651 and sum(audit['lodTriangles']) == fbx_audit['triangles'], 'Mesh/LOD coverage differs.')
    source = row(SOURCE)
    local_fbx = row(FBX)
    published_fbx = {'path': DESTINATION, 'sha256': local_fbx['sha256']}
    asset.update(id=ASSET_ID, source=source, fbx=published_fbx,
        minimumSize=dict(zip('xyz', [value-.05 for value in audit['boundsSize']])),
        maximumSize=dict(zip('xyz', [value+.05 for value in audit['boundsSize']])),
        maximumBelowGround=abs(min(0, audit['boundsMin'][1]))+.01)
    heights = [.5, .15, .025]
    asset['lods'] = [{'height': height, 'rendererPaths': sorted(mesh['name'] for mesh in audit['objects']
                     if f'_L{level}_' in mesh['name'])} for level, height in enumerate(heights)]
    all_names = {mesh['name'] for mesh in audit['objects']}
    modules = []
    for name in sorted(all_names):
        if '_L0_' not in name:
            continue
        levels = [{'height': height, 'rendererPaths': [name.replace('_L0_', f'_L{level}_')]}
                  for level, height in enumerate(heights)]
        require(all(level['rendererPaths'][0] in all_names for level in levels), 'Missing corresponding LOD module.')
        modules.append({'id': name.replace('Canyon_L0_', ''), 'lods': levels})
    require(len(modules) == 217, 'Expected exactly217 independent module LOD groups.')
    mapping_path = DOC/'candidate05-module-lod-map.json'
    write_fresh_json(mapping_path, {'schema': 1, 'assetId': ASSET_ID, 'source': published_fbx,
        'scope': 'Independent per-module Unity LODGroups/culling bounds. Review only; no production acceptance.', 'modules': modules})
    asset['moduleLodMap'] = row(mapping_path)
    descriptor_path = DOC/'candidate05-descriptor.json'
    write_fresh_json(descriptor_path, {'schema': 1, 'assets': [asset]})

    original_recipe = ROOT/'docs/p08/golden/canyon/v14/unity-lighting-v1.json'
    recipe = json.loads(original_recipe.read_text(encoding='utf-8'))
    verify({'path': recipe['hdri'], 'sha256': recipe['hdriSha256']})
    camera = audit['cameraBlender']
    require(camera['resolution'] == [1536, 717] and camera['resolutionPercentage'] == 100
            and camera['clipEnd'] == 2500 and camera['sensorFit'] == 'HORIZONTAL', 'Frozen camera changed.')
    px, py, pz = camera['position']
    pitch, roll, yaw = camera['rotationEulerRadians']
    # Blender camera -Z direction for the recorded Euler XYZ rotation; the
    # near-zero roll is explicitly bounded. Unity coordinates are x,z,y here.
    require(abs(roll) < 1e-7, 'Unexpected camera roll requires explicit projection review.')
    direction = [-math.sin(yaw)*math.sin(pitch), math.cos(yaw)*math.sin(pitch), -math.cos(pitch)]
    target = [camera['position'][index]+direction[index]*30 for index in range(3)]
    recipe.update(cameraPositionUnity=[px,pz,py], cameraTargetUnity=[target[0],target[2],target[1]],
        cameraFocalLengthMm=camera['focalLengthMm'], sensorWidthMm=camera['sensorWidthMm'], aspect=1536/717,
        scope='Unaccepted Canyon05 comparison recipe. Same locked reference and V14 lighting, measured05 camera. '
              'Run at1536x717. Existing Unity environment builder/controller use clips0.05/2000; '
              'Blender05 uses0.1/2500. Both cover measured geometry, but clip values are not identical.')
    recipe_path = DOC/'candidate05-camera-recipe.json'
    write_fresh_json(recipe_path, recipe)
    inputs = [source, local_fbx, row(old_descriptor_path), row(original_recipe), row(descriptor_path),
              row(mapping_path), row(recipe_path), row(DOC/'candidate05-source-audit.json'),
              row(DOC/'candidate05-fbx-roundtrip.json'), row(DOC/'candidate05-gameplay.png'), row(Path(__file__))]
    inputs.extend(row(path) for path in LOCKED)
    inputs.extend([asset['conceptReview'], {'path': recipe['hdri'], 'sha256': recipe['hdriSha256']}])
    for material in asset['materials']:
        inputs.extend(value for value in material.values() if isinstance(value, dict) and 'path' in value)
    unique = {item['path']: item for item in inputs}
    for item in unique.values():
        verify(item)
    handoff = {'schema': 1, 'reviewOnly': True, 'visualAccepted': False, 'productionMasksExpected': [1,1,1],
        'source': source, 'localFbx': local_fbx, 'destinationFbx': published_fbx,
        'descriptor': row(descriptor_path), 'moduleMap': row(mapping_path), 'cameraRecipe': row(recipe_path),
        'measuredBoundsUnity': {'minimum': audit['boundsMin'], 'maximum': audit['boundsMax'], 'size': audit['boundsSize']},
        'cameraClipDifference': {'blender': [camera['clipStart'], camera['clipEnd']], 'existingUnity': [.05,2000],
                                 'exactCameraParityClaimed': False},
        'inputs': [unique[path] for path in sorted(unique)],
        'scope': 'Frozen review import handoff only. Native Unity import/validation and visual review remain root-owned.'}
    write_fresh_json(HANDOFF, handoff)
    return handoff


def check() -> dict:
    verify_locked()
    handoff = json.loads(HANDOFF.read_text(encoding='utf-8'))
    require(handoff['schema'] == 1 and handoff['reviewOnly'] and not handoff['visualAccepted'], 'Not a review-only handoff.')
    require(handoff['destinationFbx']['path'] == DESTINATION and handoff['localFbx']['path'] == FBX
            and handoff['source']['path'] == SOURCE, 'Publication destination/source differs.')
    require(handoff['destinationFbx']['sha256'] == handoff['localFbx']['sha256'], 'Copy identity differs.')
    for item in handoff['inputs']:
        verify(item)
    for key in ['source', 'localFbx', 'descriptor', 'moduleMap', 'cameraRecipe']:
        verify(handoff[key])
    return handoff


def publish() -> dict:
    handoff = check()
    destination = ROOT/DESTINATION
    require(not destination.exists() and not destination.with_suffix('.fbx.meta').exists(), 'Fresh FBX and meta destination required.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (ROOT/FBX).open('rb') as source, destination.open('xb') as target:
        shutil.copyfileobj(source, target, length=1024*1024)
    verify(handoff['destinationFbx'])
    check()
    return {'published': handoff['destinationFbx'], 'nativeUnityValidationPerformed': False, 'visualAccepted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify', 'publish'])
    args = parser.parse_args()
    result = prepare() if args.command == 'prepare' else check() if args.command == 'verify' else publish()
    print(json.dumps({'command': args.command, 'reviewOnly': True, 'visualAccepted': False,
        'descriptor': result.get('descriptor'), 'published': result.get('published'),
        'verifiedInputCount': len(result.get('inputs', []))}, indent=2))
