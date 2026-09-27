"""Publish V2's exact material-partition compatibility variant, preserving V1."""
from pathlib import Path
import hashlib
import importlib.util
import json
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/menu-environment/v2'
spec=importlib.util.spec_from_file_location('menu_publish_helpers',ROOT/'tools/p08/golden/menu_publish.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
def sha(path):return helpers.digest(path)
def row(name):return {'path':name,'sha256':sha(ROOT/name)}
def marker(filename,key):
    receipt=json.loads((DOC/filename).read_text());text=next(x['text'] for x in receipt['result']['content'] if x['type']=='text' and key in x['text'])
    return json.JSONDecoder().raw_decode(text.split(key,1)[1])[0]
original=json.loads((ROOT/'docs/p08/golden/menu-environment/v1/delivery.json').read_text())
for key in ['source','fbx']:
    assert sha(ROOT/original[key]['path'])==original[key]['sha256'],'Frozen V1 changed'
roundtrip=marker('material-roundtrip-mcp.json','MENU_V2_MATERIAL_ROUNDTRIP ')
audit=marker('geometry-audit-mcp.json','MENU_GEOMETRY_AUDIT ')
assert roundtrip['passed'] and audit['physicalFailures']==audit['uvFailures']==audit['surfaceFrontFaceFailures']==0
repair=marker('material-repair-mcp.json','MENU_V2_MATERIAL_REPAIR ')
export=marker('export-mcp.json','MENU_EXPORTED ')
target='Assets/RacingBois/Art/P08/Golden/MenuEnvironment/V2/RB_Golden_MenuEnvironment.fbx'
staged='_local/p08-menu-environment-v2-staging/RB_Golden_MenuEnvironment.fbx'
descriptor=json.loads((ROOT/'docs/p08/golden/menu-environment/v1/descriptor.json').read_text())
asset=descriptor['assets'][0];asset['id']='RB_Golden_MenuEnvironment_v2';asset['source']=row('ArtSource/P08/Golden/MenuEnvironment/V2/RB_Golden_MenuEnvironment.blend')
asset['fbx']={'path':target,'sha256':sha(ROOT/staged)}
mapping=json.loads((ROOT/'docs/p08/golden/menu-environment/v1/module-lod-mapping.json').read_text());mapping['assetId']=asset['id'];mapping['source']=asset['fbx']
split={name:[r['object'] for r in repair['objects'] if r['sourceObject']==name] for name in {r['sourceObject'] for r in repair['objects']}}
def expand(paths):return [item for path in paths for item in split.get(path,[path])]
for level in asset['lods']:level['rendererPaths']=expand(level['rendererPaths'])
for module in mapping['modules']:
    for level in module['lods']:level['rendererPaths']=expand(level['rendererPaths'])
all_paths=[path for module in mapping['modules'] for level in module['lods'] for path in level['rendererPaths']]
assert len(all_paths)==len(set(all_paths))==419 and set(all_paths)=={r['name'] for r in export['objects']}
map_path='docs/p08/golden/menu-environment/v2/module-lod-mapping.json'
map_bytes=(json.dumps(mapping,indent=2)+'\n').encode();asset['moduleLodMap']={'path':map_path,'sha256':hashlib.sha256(map_bytes).hexdigest()}
descriptor_bytes=(json.dumps(descriptor,indent=2)+'\n').encode()
outputs=[(ROOT/target,(ROOT/staged).read_bytes()),(ROOT/map_path,map_bytes),(DOC/'descriptor.json',descriptor_bytes)]
for path,data in outputs:
    helpers.safe(path.relative_to(ROOT).as_posix())
    if path.exists() and path.read_bytes()!=data:raise RuntimeError('Refuse different existingV2 publication')
for path,data in outputs:helpers.publish_bytes(path,data)
helpers.check_inputs(descriptor)
delivery={'schema':1,'published':True,'nativeUnityVerified':False,'visualAccepted':False,'sourceV1Preserved':True,
    'source':asset['source'],'fbx':asset['fbx'],'descriptor':row('docs/p08/golden/menu-environment/v2/descriptor.json'),
    'moduleLodMap':asset['moduleLodMap'],'meshes':419,'modules':139,'triangles':roundtrip['triangles'],
    'proofs':[row('docs/p08/golden/menu-environment/v2/'+name) for name in ['raw-fbx-materials.json','material-repair-mcp.json','geometry-audit-mcp.json','material-roundtrip-mcp.json']],
    'lightingPolicy':'Realtime menu; no baked GI is requested. Root is independently testing whether Unity secondary-UV generation caused the V1 failure. No invalid UV0 or missing-material gate is waived.',
    'scope':'TwoLOD0 stones split into explicit existing-material renderers. V1 Blender assignments/rawFBX connections were valid; this compatibility variant is not proof of the Unity failure cause.'}
helpers.publish_bytes(DOC/'delivery.json',(json.dumps(delivery,indent=2)+'\n').encode())
print(json.dumps({key:delivery[key] for key in ['fbx','source','meshes','modules','triangles','nativeUnityVerified']},indent=2))
