"""Correct descriptor measurement scope to consumed LOD0; never widen tolerance."""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT/'docs/p08/golden/canyon/v17'
spec = importlib.util.spec_from_file_location('canyon05_publisher', ROOT/'tools/p08/golden/canyon_v17/publish_candidate05.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
HANDOFF = DOC/'candidate05-publication-r1.json'


def prepare() -> dict:
    publisher.require(not HANDOFF.exists(), 'Revision is frozen; use verify, never overwrite it.')
    original_handoff = publisher.check()
    publisher.verify(original_handoff['destinationFbx'])
    audit_path = DOC/'candidate05-lod-bounds-r1.json'
    audit = publisher.decode_mcp(audit_path, 'CANYON_V17_LOD_BOUNDS_R1 ')
    publisher.require(audit['nativeEnvelopeConsumesLevel'] == 0 and not audit['sourceSaved']
        and not audit['fbxExported'] and audit['exactDatablockMembershipRestored'] and not audit['visualAccepted'],
        'Bounds audit must be read-only with complete owned-state restoration.')
    source, fbx = audit['sourceLods'][0], audit['fbxLods'][0]
    publisher.require(source['level'] == fbx['level'] == 0 and source['meshCount'] == fbx['meshCount'] == 217,
        'Expected exact217 LOD0 meshes.')
    native_path = DOC/'native-lod0-bounds.json'
    native_payload = json.loads(native_path.read_text(encoding='utf-8'))
    publisher.require(native_payload['success'], 'Root native bounds probe failed.')
    native = native_payload['data']['result']
    publisher.require(native['rendererCount'] == 217, 'Native LOD0 coverage differs.')
    for source_key,native_key in [('minimumUnity','min'),('maximumUnity','max'),('sizeUnity','size')]:
        for a,b,c in zip(source[source_key],fbx[source_key],native[native_key]):
            publisher.require(abs(a-b) < .001 and abs(b-c) < .001, 'Independent physical vertex measurements disagree.')

    original_path = DOC/'candidate05-descriptor.json'
    original = json.loads(original_path.read_text(encoding='utf-8'))
    revised = copy.deepcopy(original)
    old_asset, asset = original['assets'][0], revised['assets'][0]
    for index,axis in enumerate('xyz'):
        old_size = original_handoff['measuredBoundsUnity']['size'][index]
        publisher.require(abs(old_asset['minimumSize'][axis]-(old_size-.05)) < 1e-8
            and abs(old_asset['maximumSize'][axis]-(old_size+.05)) < 1e-8, 'Original envelope tolerance is not the expected0.05m.')
    asset['minimumSize'] = dict(zip('xyz',[value-.05 for value in fbx['sizeUnity']]))
    asset['maximumSize'] = dict(zip('xyz',[value+.05 for value in fbx['sizeUnity']]))
    asset['maximumBelowGround'] = abs(min(0,fbx['minimumUnity'][1]))+.01
    changed_keys = sorted(key for key in asset if asset[key] != old_asset[key])
    publisher.require(changed_keys == ['maximumBelowGround','maximumSize','minimumSize'], 'Revision changed more than bounds fields.')
    revised_path = DOC/'candidate05-descriptor-r1.json'
    publisher.write_fresh_json(revised_path,revised)
    failure_path = ROOT/'docs/p08/golden/unity/import-f1fae1f4f9f241669d004ad4f1295d20.json'
    failure = json.loads(failure_path.read_text(encoding='utf-8'))
    publisher.require(not failure['passed'] and 'Physical model dimensions outside declared envelope' in failure['failure'],
        'Expected preserved native envelope failure missing.')
    inputs = {item['path']:item for item in original_handoff['inputs']}
    for path in [revised_path,audit_path,native_path,DOC/'native-lod0-y-extrema.json',failure_path,
                 Path(__file__),Path(__file__).with_name('audit_lod_bounds.py'),
                 ROOT/'Assets/RacingBois/Editor/GoldenSampleBuilder.Validation.cs']:
        item = publisher.row(path)
        inputs[item['path']] = item
    handoff = {
        'schema':1,'revision':'bounds-r1','reviewOnly':True,'visualAccepted':False,
        'descriptor':publisher.row(revised_path),'previousDescriptor':publisher.row(original_path),
        'preservedFailedImport':publisher.row(failure_path),'originalPublication':publisher.row(publisher.HANDOFF),
        'source':original_handoff['source'],'fbx':original_handoff['destinationFbx'],
        'moduleMap':original_handoff['moduleMap'],'cameraRecipe':original_handoff['cameraRecipe'],
        'changedFields':changed_keys,'boundsToleranceMetres':.05,'belowGroundMarginMetres':.01,
        'measurementBasis':'Same frozen FBX, exact transformed LOD0 vertices, independently matched to native Unity LOD0 bounds.',
        'fbxLod0':{key:value for key,value in fbx.items() if key!='meshes'},
        'nativeLod0':native,'sourceFbxMapsRecipeUnchanged':True,
        'inputs':[inputs[path] for path in sorted(inputs)],
        'nativeImportValidationPassed':False,
        'scope':'Corrected measurement population only: all-LOD union to native-consumed LOD0. Same tolerance; no geometry, UV, material, module map or camera changes.'
    }
    publisher.write_fresh_json(HANDOFF,handoff)
    return handoff


def verify() -> dict:
    publisher.check()
    handoff=json.loads(HANDOFF.read_text(encoding='utf-8'))
    publisher.require(handoff['reviewOnly'] and not handoff['visualAccepted'] and handoff['boundsToleranceMetres']==.05
        and handoff['belowGroundMarginMetres']==.01 and handoff['sourceFbxMapsRecipeUnchanged'], 'Revision scope changed.')
    for item in handoff['inputs']:
        publisher.verify(item)
    for key in ['descriptor','previousDescriptor','preservedFailedImport','originalPublication','source','fbx','moduleMap','cameraRecipe']:
        publisher.verify(handoff[key])
    return handoff


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','verify'])
    args=parser.parse_args()
    handoff=prepare() if args.command=='prepare' else verify()
    print(json.dumps({'command':args.command,'descriptor':handoff['descriptor'],
        'boundsToleranceMetres':handoff['boundsToleranceMetres'],'verifiedInputs':len(handoff['inputs']),
        'visualAccepted':False},indent=2))
