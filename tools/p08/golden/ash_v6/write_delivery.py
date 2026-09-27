"""Freeze verified candidate metadata; never writes live Assets or acceptance."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[4]
DOC=ROOT/'docs/p08/golden/ash/v6'
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def ref(path):return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(name,value):(DOC/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def receipt(name,marker):
 j=json.loads((DOC/name).read_text(encoding='utf-8-sig'));s='\n'.join(x['text'] for x in j['result']['content'] if x['type']=='text')
 return json.JSONDecoder().raw_decode(s[s.index(marker)+len(marker):])[0]
audit=receipt('audit-export-frozen-receipt.json','ASH_V6_AUDIT_EXPORT ')
roundtrip=receipt('roundtrip-frozen-receipt.json','ASH_V6_ROUNDTRIP ')
preserved=receipt('preservation-final-receipt.json','ASH_V6_PRESERVATION ')
maps=load('docs/p08/golden/ash/v6/map-validation.json')
assert audit['passed'] and roundtrip['passed'] and preserved['passed'] and maps['passed']
write('runtime-audit.json',audit);write('roundtrip.json',roundtrip);write('preserved-gameplay.json',preserved)
packed=receipt('packed-maps-receipt.json','ASH_V6_PACKED_IMAGES ');packed_rows=[]
for image in packed['images']:
 path=Path(image['path']);data=path.read_bytes();value=14695981039346656037
 for byte in data:value=((value^byte)*1099511628211)&18446744073709551615
 assert len(data)==image['bytes'] and f'{value:016x}'==image['packedFnv1a64'],path
 packed_rows.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'packedAndExternalFnv1a64':f'{value:016x}','bytes':len(data)})
write('packed-texture-verification.json',{'passed':True,'images':len(packed_rows),'files':packed_rows,'scope':'Packed byte fingerprints and lengths match source PNGs; external SHA256 binds each file. Not visual acceptance.'})
policy_path='docs/p08/golden/ash/v4/descriptor-native.json'
descriptor=load(policy_path);asset=descriptor['assets'][0]
asset['id']='RB_Golden_Ash_V6';asset['source']=ref('ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend');asset['fbx']=ref('_local/p08-ash-v6-staging/RB_Golden_Ash_V6.fbx')
for field in ['forwardMarker','leftMarker','rightMarker','rigRoot']:asset[field]=asset[field].replace('RB_Golden_Ash_V4','RB_Golden_Ash_V6')
for field in ['groundMarkers','requiredBones']:asset[field]=[v.replace('RB_Golden_Ash_V4','RB_Golden_Ash_V6') for v in asset[field]]
for lod in asset['lods']:lod['rendererPaths']=[v.replace('AshV4_L','AshV6_L') for v in lod['rendererPaths']]
roles={m['role']:m for m in maps['materials']}
def material(role):
 m=roles[role];files=m['files']
 return {'sourceName':'AshV6_'+role+'_Baked','baseColor':ref(files['BaseColor']['path']),'normal':ref(files['Normal']['path']),
  'metallicSmoothness':ref(files['MetallicSmoothness']['path']),'occlusion':ref(files['Occlusion']['path']),
  'maxSize':m['size'][0],'normalScale':1,'transparent':False,'doubleSided':False,'opacity':1}
removed={'AshV2_AmberLens_Baked','AshV4_HelmetEnamel_Baked','AshV2_HairFibers_Baked'}
asset['materials']=[material('Skin') if m['sourceName']=='AshV4_Skin_Baked' else m for m in asset['materials'] if m['sourceName'] not in removed]
asset['materials'] += [material('EquipmentL'+str(i)) for i in range(3)]
stacks=load('docs/p08/golden/ash/v6/fbx-inspection.json')['animationStackOrder']
for clip in asset['clips']+asset['previewClips']:clip.update(asset['fbx']);assert clip['name'] in stacks
assert len(asset['clips'])==12 and len(asset['previewClips'])==1 and len(asset['loopClips'])==6 and len(stacks)==13
assert asset['restPose']=='bind'
descriptor['purpose']='Unaccepted Ash V6 candidate for native review. Preserve12 gameplay bindings, six explicit loops and separate MenuHero preview; only MenuHero Head quaternion curves changed. Staged inputs require hash-preserving publication.'
write('descriptor-staged.json',descriptor)
write('native-policy-baseline.json',{'source':ref(policy_path),'loopClips':asset['loopClips'],'previewClips':asset['previewClips'],'gameplayBindings':12,'restPose':'bind'})
originals=[ref(p) for p in ['ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend','ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend','ArtSource/Weapons/RB_Club.blend']]
assert [v['sha256'] for v in originals]==['a42a84a423fb158eb84995bbe2d842d7925c23a872fe36902f5566570cf64a30','20ed1963ccf7f7f537a2899a89b59d84a62924b98e7bf94bfeb339e61d9cd5c9','553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f']
write('delivery.json',{'source':asset['source'],'fbx':asset['fbx'],'descriptor':ref('docs/p08/golden/ash/v6/descriptor-staged.json'),
 'newTextures':[ref(f['path']) for m in maps['materials'] for f in m['files'].values()],
 'packedImageCount':len(packed_rows),'originalsPreserved':originals,
 'lockedReferences':[ref('ArtSource/Concepts/P08/Golden/ash-v2.png'),ref('ArtSource/Concepts/P08/Golden/UI/main-v2.png')],
 'renders':[ref('docs/p08/golden/ash/v6/'+n+'.png') for n in ['baked-front-final','baked-quarter-final','baked-side-final','menu-gaze-r2','menu-gaze-portrait']],
 'lodTriangles':[m['triangles'] for m in audit['lods']],'actualFbxAnimationStacks':stacks,'gameplayActionsExact':12,
 'menuChange':'Head quaternion only, +30 degree world yaw and4 degree upward pitch; all other menu curves exact',
 'stagingOnly':True,'liveAssetsWritten':False,'nativeUnityVerified':False,'visualAccepted':False,'performanceAccepted':False,
 'integration':'Copy staged FBX and16newmaps into a fresh V6 Assets location with identical hashes, rebind only those paths including all clip references. Keep reusedV2/V3/V4 material map paths. Require native Generic hierarchy, bind rest, exact13clip imports and six loop flags. Do not promote production masks.'})
print(json.dumps({'source':asset['source'],'fbx':asset['fbx'],'newMaps':16,'packedImages':len(packed_rows),'materials':len(asset['materials']),'visualAccepted':False}))
