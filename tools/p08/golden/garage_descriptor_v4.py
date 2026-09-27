"""Bind the UV-only V4 source/export; retain all locked concepts and V2 PBR files."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/garage/v4'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def file(path):return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(path,value):(ROOT/path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
assert read('docs/p08/golden/garage/v3/uv-validation.json')['passed']
roundtrip=read('docs/p08/golden/garage/v4/roundtrip-mcp.json')['result']['structuredContent']['result']
assert json.loads(roundtrip.split('GARAGE_V4_ROUNDTRIP ',1)[1])['passed']
target='Assets/RacingBois/Art/P08/Golden/Garage/V4/RB_Golden_Garage.fbx'
(ROOT/target).parent.mkdir(parents=True,exist_ok=True)
assert not (ROOT/target).exists(),'Preserve prior import inputs'
shutil.copyfile(ROOT/'_local/p08-garage-v4-staging/RB_Golden_Garage.fbx',ROOT/target)
descriptor=read('docs/p08/golden/garage/v2/descriptor.json');asset=descriptor['assets'][0]
asset.update(id='RB_Golden_Garage_v4',lightmapUv='authored',source=file('ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend'),fbx=file(target))
mapping=read('docs/p08/golden/garage/v2/module-lod-mapping.json');mapping.update(assetId=asset['id'],source=asset['fbx'])
write('docs/p08/golden/garage/v4/module-lod-mapping.json',mapping)
asset['moduleLodMap']=file('docs/p08/golden/garage/v4/module-lod-mapping.json')
write('docs/p08/golden/garage/v4/descriptor.json',descriptor)
lighting=read('docs/p08/golden/garage/v2/unity-lighting-initial.json')
lighting.update(source=asset['source'],descriptor=file('docs/p08/golden/garage/v4/descriptor.json'),revision='authored-lightmap-uv-v4-initial')
write('docs/p08/golden/garage/v4/unity-lighting-initial.json',lighting)
print('GARAGE_V4_DESCRIPTOR',asset['fbx']['sha256'],'authoredUV1, reusedV2PBR, visualAcceptedFalse')
