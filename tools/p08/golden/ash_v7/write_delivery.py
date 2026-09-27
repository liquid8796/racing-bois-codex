"""Freeze real V7 source/export/maps and native-policy metadata, outside Assets."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4];DOC=ROOT/'docs/p08/golden/ash/v7'
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def ref(path):return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}
def write(name,value):(DOC/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def receipt(name,marker):
 j=json.loads((DOC/name).read_text(encoding='utf-8-sig'));s='\n'.join(x.get('text','') for x in j['result']['content']);return json.JSONDecoder().raw_decode(s[s.index(marker)+len(marker):])[0]
audit=receipt('audit-export-delivery-receipt.json','ASH_V7_AUDIT_EXPORT ');roundtrip=receipt('roundtrip-delivery-receipt.json','ASH_V7_ROUNDTRIP ')
preserved=receipt('preservation-delivery-receipt.json','ASH_V7_PRESERVATION ');contacts=receipt('pose-contacts-delivery-receipt.json','ASH_V7_POSE_CONTACT_AUDIT ')
menu=receipt('menu-contact-delivery-receipt.json','ASH_V7_FINAL_MENU_CONTACT ');maps=load('docs/p08/golden/ash/v7/map-validation.json')
assert all([audit['passed'],roundtrip['passed'],preserved['passed'],contacts['contactPassed'],menu['passed'],maps['passed']])
for name,value in [('runtime-audit.json',audit),('roundtrip.json',roundtrip),('preserved-gameplay.json',preserved),('pose-contacts.json',contacts),('menu-r4-contacts.json',menu)]:write(name,value)
packed=receipt('packed-maps-receipt.json','ASH_V7_PACKED_IMAGES ');packed_rows=[]
for item in packed['images']:
 path=Path(item['path']);data=path.read_bytes();value=14695981039346656037
 for b in data:value=((value^b)*1099511628211)&18446744073709551615
 assert len(data)==item['bytes'] and f'{value:016x}'==item['packedFnv1a64'],path
 packed_rows.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'packedAndExternalFnv1a64':f'{value:016x}','bytes':len(data)})
write('packed-texture-verification.json',{'passed':True,'images':len(packed_rows),'files':packed_rows})
descriptor=load('docs/p08/golden/ash/v6/descriptor.json');asset=descriptor['assets'][0];asset['id']='RB_Golden_Ash_V7';asset['source']=ref('ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend');asset['fbx']=ref('_local/p08-ash-v7-staging/RB_Golden_Ash_V7.fbx')
for field in ['forwardMarker','leftMarker','rightMarker','rigRoot']:asset[field]=asset[field].replace('RB_Golden_Ash_V6','RB_Golden_Ash_V7')
for field in ['groundMarkers','requiredBones']:asset[field]=[v.replace('RB_Golden_Ash_V6','RB_Golden_Ash_V7') for v in asset[field]]
for lod in asset['lods']:lod['rendererPaths']=[v.replace('AshV6_L','AshV7_L') for v in lod['rendererPaths']]
roles={m['role']:m for m in maps['materials']}
def material(role):
 m=roles[role];f=m['files'];return {'sourceName':'AshV7_'+role+'_Baked','baseColor':ref(f['BaseColor']['path']),'normal':ref(f['Normal']['path']),'metallicSmoothness':ref(f['MetallicSmoothness']['path']),'occlusion':ref(f['Occlusion']['path']),'maxSize':m['size'][0],'normalScale':1,'transparent':role=='AmberGlass','doubleSided':False,'opacity':.38 if role=='AmberGlass' else 1}
asset['materials']=[material(m['sourceName'].removeprefix('AshV6_').removesuffix('_Baked')) if m['sourceName'].startswith('AshV6_Equipment') else m for m in asset['materials']]+[material('AmberGlass')]
stacks=load('docs/p08/golden/ash/v7/fbx-inspection.json')['animationStackOrder']
for clip in asset['clips']+asset['previewClips']:clip.update(asset['fbx']);assert clip['name'] in stacks
assert len(stacks)==13 and len(asset['clips'])==12 and len(asset['loopClips'])==6 and asset['restPose']=='bind'
descriptor['purpose']='Unaccepted AshV7 native-review candidate: explicit transparent optics, repaired collar and menu-only R4 palm/finger contact. Preserve12 gameplay bindings,6 explicit loops, separate MenuHero preview and bind rest. No visual or production acceptance.'
write('descriptor-staged.json',descriptor)
originals=[ref(p) for p in ['ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend','ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend','ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend','ArtSource/Weapons/RB_Club.blend']]
assert [r['sha256'] for r in originals]==['a42a84a423fb158eb84995bbe2d842d7925c23a872fe36902f5566570cf64a30','20ed1963ccf7f7f537a2899a89b59d84a62924b98e7bf94bfeb339e61d9cd5c9','d90115f75d200fc1c37087df6e4bca01457472eec5fba9058d43d303c55aa7b7','553f60a0bd9ab32413c3c584aa61cf5a4076752364efb4b8f0a92b567c67a37f']
poses=[]
for batch in [1,2,3]:poses.extend(receipt('pose-render-delivery-'+str(batch)+'-receipt.json','ASH_V7_FULLBODY_REVIEW ')['poses'])
assert len(poses)==17 and len({p['image'] for p in poses})==17
pose_refs=[ref(Path(p['image']).relative_to(ROOT).as_posix()) for p in poses];write('fullbody-review.json',{'actualRenders':17,'images':pose_refs,'poses':poses,'visualAccepted':False})
reference=ref('Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4.fbx');assert reference['sha256']=='4e57cfeaefe2e27643c17bb083b04acb15dd483276a02058f05e687f69c16841'
write('delivery.json',{'source':asset['source'],'fbx':asset['fbx'],'descriptor':ref('docs/p08/golden/ash/v7/descriptor-staged.json'),
 'newTextures':[ref(f['path']) for m in maps['materials'] for f in m['files'].values()],
 'lockedReferences':[ref('ArtSource/Concepts/P08/Golden/ash-v2.png'),ref('ArtSource/Concepts/P08/Golden/UI/main-v2.png')],
 'canonicalBikeReference':reference,'canonicalBikeDescriptor':ref('docs/p08/golden/apex/r4/descriptor.json'),'originalsPreserved':originals,
 'renders':[ref('docs/p08/golden/ash/v7/'+name+'.png') for name in ['baked-front-final','baked-quarter-final','baked-side-final','menu-r4','menu-gaze-portrait','menu-hand-tail','menu-hand-tank']],
 'fullBodyRenders':pose_refs,'packedImageCount':len(packed_rows),'lodTriangles':[m['triangles'] for m in audit['lods']],
 'actualFbxAnimationStacks':stacks,'menuSampleCount':17,'menuMinimumGloveClearanceMetres':menu['result']['minimumByHand'],
 'menuCentralPalmClearanceMetres':[min(h['centralPalmMinimumDistance'] for r in menu['result']['samples'] for l in r['lods'] for h in l['hands']),max(h['centralPalmMinimumDistance'] for r in menu['result']['samples'] for l in r['lods'] for h in l['hands'])],
 'stagingOnly':True,'v7LiveAssetsWritten':False,'nativeUnityVerified':False,'visualAccepted':False,'performanceAccepted':False,
 'integration':'Copy only staged FBX and16new maps to fresh V7 Assets paths with identical hashes; rebind those paths plus gameplay/preview clip references. Keep all reusedV2/V3/V4/V6 maps and bind-rest/native loop policy. AmberGlass must remain transparent opacity0.38; never include it in an opaque atlas. Native13clip, loop, menu contact and actual visual checks remain required.'})
print(json.dumps({'source':asset['source'],'fbx':asset['fbx'],'materials':len(asset['materials']),'newMaps':16,'packedImages':len(packed_rows),'fullbodyImages':17,'visualAccepted':False}))
