"""Freeze source-bound staging metadata; never copies into Assets."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4];DOC=ROOT/'docs/p08/golden/ash/v4'
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def ref(path):return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(name,value):(DOC/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def receipt(name,marker):
    j=json.loads((DOC/name).read_text(encoding='utf-8-sig'));s='\n'.join(x['text'] for x in j['result']['content'] if x['type']=='text')
    return json.JSONDecoder().raw_decode(s[s.index(marker)+len(marker):])[0]
audit=receipt('audit-export-final-mcp.json','ASH_V4_AUDIT_EXPORT ');roundtrip=receipt('roundtrip-final-mcp.json','ASH_V4_ROUNDTRIP ')
preserved=receipt('preserved-gameplay-mcp.json','ASH_V4_PRESERVATION ');maps=load('docs/p08/golden/ash/v4/map-validation.json')
assert audit['passed'] and roundtrip['passed'] and preserved['passed'] and maps['passed']
write('runtime-audit.json',audit);write('roundtrip.json',roundtrip);write('preserved-gameplay.json',preserved)
packed=receipt('packed-images-mcp.json','ASH_V4_PACKED_IMAGES ');packed_rows=[]
for image in packed['images']:
    path=Path(image['path']);data=path.read_bytes();value=14695981039346656037
    for b in data:value=((value^b)*1099511628211)&18446744073709551615
    assert len(data)==image['bytes'] and f'{value:016x}'==image['packedFnv1a64'],path
    packed_rows.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'packedAndExternalFnv1a64':f'{value:016x}','bytes':len(data)})
write('packed-texture-verification.json',{'passed':True,'images':len(packed_rows),'files':packed_rows,'scope':'Packed-byte FNV1a64 plus byte length matches source PNG, external SHA256 binds each file. Not visual acceptance.'})
descriptor=load('docs/p08/golden/ash/v3/descriptor-bind.json');asset=descriptor['assets'][0]
asset['id']='RB_Golden_Ash_V4';asset['source']=ref('ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend');asset['fbx']=ref('_local/p08-ash-v4-staging/RB_Golden_Ash_V4.fbx')
for field in ['forwardMarker','leftMarker','rightMarker','rigRoot']:asset[field]=asset[field].replace('RB_Golden_Ash_V3','RB_Golden_Ash_V4')
for field in ['groundMarkers','requiredBones']:asset[field]=[v.replace('RB_Golden_Ash_V3','RB_Golden_Ash_V4') for v in asset[field]]
for lod in asset['lods']:lod['rendererPaths']=[v.replace('AshV3_L','AshV4_L') for v in lod['rendererPaths']]
role_map={'AshV2_Skin_Baked':'Skin','AshV2_CharcoalLeather_Baked':'LeatherDetails','AshV2_TailoredClothing_Baked':'TailoredLeather','AshV2_IvoryEnamel_Baked':'HelmetEnamel'}
material_maps={m['role']:m for m in maps['materials']}
def material(role):
    m=material_maps[role];files=m['files']
    return {'sourceName':'AshV4_'+role+'_Baked','baseColor':ref(files['BaseColor']['path']),'normal':ref(files['Normal']['path']),
        'metallicSmoothness':ref(files['MetallicSmoothness']['path']),'occlusion':ref(files['Occlusion']['path']),
        'maxSize':m['size'][0],'normalScale':1,'transparent':False,'doubleSided':False}
asset['materials']=[material(role_map[m['sourceName']]) if m['sourceName'] in role_map else m for m in asset['materials']]+[material('Forelocks')]
stacks=load('docs/p08/golden/ash/v4/fbx-inspection.json')['animationStackOrder']
for clip in asset['clips']:
    clip.update(asset['fbx']);assert clip['name'] in stacks
menu=receipt('menu-pose-roll-fixed-mcp.json','ASH_V4_MENU_POSE ')
menu.update(clip='RB_P06_Rider_Rig|RB_MenuHero',fbx=asset['fbx']);assert menu['clip'] in stacks
write('menu-pose.json',menu)
descriptor['purpose']='Unaccepted AshV4 candidate. Staging paths must be copied/rebound by root before native import. Preserve12 gameplay clips; optional menu pose is separate.'
write('descriptor-staged.json',descriptor)
originals=[ref('ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend'),ref('Assets/RacingBois/Art/P08/Golden/Ash/V3/RB_Golden_Ash_V3.fbx'),ref('ArtSource/Weapons/RB_Club.blend')]
assert originals[0]['sha256']=='e03297751d46e2c09143518be4fb054425eb6d0b036006da6e9070c3b8fefe26'
assert originals[1]['sha256']=='4ce1c6d32ccc46a3d9a8773a74f9db4b2aa163f13ef49ad81b4238e01267ca74'
assert originals[2]['sha256']=='553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f'
write('delivery.json',{'source':asset['source'],'fbx':asset['fbx'],'newTextures':[ref(file['path']) for m in maps['materials'] for file in m['files'].values()],
    'packedImageCount':len(packed_rows),'originalsPreserved':originals,'lockedReferences':[ref('ArtSource/Concepts/P08/Golden/ash-v2.png'),ref('ArtSource/Concepts/P08/Golden/UI/main-v2.png')],
    'renders':[ref('docs/p08/golden/ash/v4/'+name+'.png') for name in ['front-baked','side-baked','quarter-baked','portrait-baked','menu-hero-r2-roll-fixed']],
    'finalLodTriangles':[m['triangles'] for m in audit['lods']],'actualFbxAnimationStacks':stacks,'menuPose':'menu-pose.json',
    'stagingOnly':True,'liveAssetsWritten':False,'nativeUnityVerified':False,'visualAccepted':False,'performanceAccepted':False,
    'integration':'Copy the staged FBX and20newPBR files to a fresh V4 Assets location with identical hashes, rebind their paths and all clip references in descriptor-staged. Keep reused V2/V3 maps unchanged. Native probe must confirm actual hierarchy/clip names and bind rest. Do not replace Idle with MenuHero or promote production masks.'})
print(json.dumps({'source':asset['source'],'fbx':asset['fbx'],'packedImages':len(packed_rows),'newMaps':20,'gameplayClips':len(asset['clips']),'allFbxClips':len(stacks),'visualAccepted':False}))
