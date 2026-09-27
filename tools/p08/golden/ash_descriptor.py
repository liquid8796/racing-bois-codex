"""Write a descriptor only after all actual saved/exported inputs exist."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Ash'
EVIDENCE=ROOT/'docs/p08/golden/ash'
def input_file(path):
    full=ROOT/path
    return {'path':full.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(full.read_bytes()).hexdigest()}
audit=json.loads((EVIDENCE/'source-observations.json').read_text())
surface_spec={s['material']:s for s in json.loads((OUT/'surface-layout.json').read_text())['surfaces']}
materials=[]
for name in sorted({name for mesh in audit['meshes'] for name in mesh['materials']}):
    logical=name.split('.')[0];prefix='Assets/RacingBois/Art/P08/Golden/Ash/'+logical
    materials.append({'sourceName':name,'baseColor':input_file(prefix+'_BaseColor.png'),'normal':input_file(prefix+'_Normal.png'),
      'metallicSmoothness':input_file(prefix+'_MetallicSmoothness.png'),'maxSize':surface_spec[logical]['resolution'],
      'normalScale':.35 if logical=='Ash_Skin' else .55,'transparent':False})
clip_source=input_file('Assets/RacingBois/Art/P06/Hero/RB_P06_Rider.fbx')
clips=[dict(clip_source,name=name) for name in ['RB_Ride','RB_LeanLeft','RB_LeanRight','RB_AttackLeft','RB_AttackRight','RB_KickLeft','RB_KickRight','RB_Hit','RB_Fall','RB_Run','RB_Remount','RB_Idle']]
asset={'id':'RB_Golden_Ash','kind':'rider','concept':input_file('ArtSource/Concepts/P08/Golden/ash-v2.png'),
  'conceptReview':input_file('ArtSource/Concepts/P08/Golden/ash-v2-review.md'),
  'source':input_file('ArtSource/P08/Golden/Ash/RB_Golden_Ash.blend'),'fbx':input_file('Assets/RacingBois/Art/P08/Golden/Ash/RB_Golden_Ash.fbx'),
  'modelRotationEuler':{'x':0,'y':0,'z':0},'minimumSize':{'x':.50,'y':1.74,'z':.25},'maximumSize':{'x':.65,'y':1.84,'z':.40},
  'materials':materials,'lods':[{'height':height,'rendererPaths':[mesh['path'] for mesh in audit['meshes'] if '_L'+str(level)+'_' in mesh['name']]} for level,height in enumerate([.32,.13,.02])],
  'forwardMarker':'Forward','groundMarkers':['Ground_L','Ground_R'],'rigRoot':audit['rigPath'],'requiredBones':audit['bonePaths'],'clips':clips,
  'colliders':[{'type':'capsule','center':{'x':0,'y':.90,'z':0},'radius':.25,'height':1.80,'direction':1}],'isStatic':False}
(EVIDENCE/'descriptor.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n')
print('ASH_ACTUAL_DESCRIPTOR_WRITTEN',len(materials),'material slots; visual and Unity acceptance pending')
