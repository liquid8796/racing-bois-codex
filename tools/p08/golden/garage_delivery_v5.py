"""Bind a staged V5 handoff without writing anything under Assets."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/garage/v5'
def ref(path):return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(name,value):(DOC/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def receipt(name,marker):
    j=json.loads((DOC/name).read_text(encoding='utf-8-sig'));text='\n'.join(v['text'] for v in j['result']['content'] if v['type']=='text')
    return json.JSONDecoder().raw_decode(text[text.index(marker)+len(marker):])[0]
export=receipt('export-mcp.json','GARAGE_V5_EXPORT ')
roundtrip=receipt('roundtrip-mcp.json','GARAGE_V5_ROUNDTRIP ')
preserved=receipt('preservation-mcp.json','GARAGE_V5_PRESERVATION ')
assert roundtrip['passed'] and preserved['passed']
write('roundtrip.json',roundtrip);write('preservation.json',preserved);write('authored-lighting.json',export['lighting'])
source=ref('ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend');fbx=ref('_local/p08-garage-v5-staging/RB_Golden_Garage.fbx')
descriptor=json.loads((ROOT/'docs/p08/golden/garage/v4/descriptor.json').read_text(encoding='utf-8'))
asset=descriptor['assets'][0];asset.update(id='RB_Golden_Garage_v5',source=source,fbx=fbx)
mapping=json.loads((ROOT/'docs/p08/golden/garage/v4/module-lod-mapping.json').read_text(encoding='utf-8'))
mapping.update(assetId=asset['id'],source=fbx);write('module-lod-mapping-staged.json',mapping)
asset['moduleLodMap']=ref('docs/p08/golden/garage/v5/module-lod-mapping-staged.json')
write('descriptor-staged.json',descriptor)
delivery={'schema':1,'source':source,'fbx':fbx,'stagingOnly':True,'assetsWritten':False,'nativeImported':False,'visualAccepted':False,
    'integration':'Root must copy the FBX to a fresh Assets/RacingBois/Art/P08/Golden/Garage/V5 path, preserve SHA256, and rebind descriptor/mapping FBX paths + mapping hash before Golden importer. Do not import staged descriptor as-is.',
    'uvContract':{'uv0':'UV0_MetricTile: intentional repeated metric texture projection/overlap; finite nondegenerate triangles','uv1':'LightmapUV on60LOD0 meshes only; exact V4 data retained, preserve authored UVs','lowerLods':'One primary UV channel; use actual baked light probes'},
    'triangles':{'lod0':132592,'lod1':28712,'lod2':4508},
    'defaultUnityMaterials':{'shader':'Universal Render Pipeline/Lit','textures':'Identical hash-bound V2 PNGs from reused descriptor; no new textures','metallicWorkflow':1,'smoothnessMultiplier':1,'metallicMultiplier':1,'smoothnessChannel':'metallic map alpha','floorNormalScale':.55,'clearCoat':0,'normalConvention':'OpenGL, imported NormalMap','specularHighlights':True,'environmentReflections':True,'wrapMode':'Repeat for primary metric tiling'},
    'coatComparison':{'source':ref('ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage_CoatComparison.blend'),'render':ref('docs/p08/golden/garage/v5/coated-floor.png'),'accepted':False,'reason':'Visually over-smooth/specular compared with the textured locked floor; retained as comparison only. Do not substitute it to compensate for missing native area-light specular.',
        'shaderIfReproducingComparisonOnly':'Universal Render Pipeline/Complex Lit','clearCoatKeyword':'_CLEARCOAT (no clearcoat texture)','settings':'material-comparison-settings.json'},
    'lockedConcepts':[ref('ArtSource/Concepts/P08/Golden/garage-environment-v1.png'),ref('ArtSource/Concepts/P08/Golden/UI/garage-v2.png')],
    'preservedInputs':[ref('ArtSource/P08/Golden/Garage/V3/RB_Golden_Garage.blend'),ref('ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend'),ref('ArtSource/Weapons/RB_Club.blend')],
    'readme':'docs/p08/golden/garage/v5/README.md'}
final_render='docs/p08/golden/garage/v5/uv-final-original-materials.png'
if (ROOT/final_render).is_file():delivery['finalSourceRender']=ref(final_render)
assert delivery['preservedInputs'][0]['sha256']=='7455c5b8a27371de50b72388dd2668edfdeaaa83664e590cae1f426485c293ea'
assert delivery['preservedInputs'][1]['sha256']=='a676eeab8e63fb4b53d8a277267bee07bc7f206468793395dd537a68d50a1594'
assert delivery['preservedInputs'][2]['sha256']=='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f'
write('delivery.json',delivery)
print(json.dumps({'source':source,'fbx':fbx,'roundtripPassed':True,'preservedV3V4Club':True,'visualAccepted':False}))
