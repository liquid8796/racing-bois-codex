"""Bind the actual Canyon files for root-owned Unity inspection, not production."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
DOC=ROOT/'docs/p08/golden/canyon/v16'
def input_file(path):
    p=ROOT/path
    return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
receipt=json.loads((DOC/'source-audit-mcp.json').read_text())
text=next(i['text'] for i in receipt['result']['content'] if i['type']=='text' and 'CANYON_SOURCE_AUDIT ' in i['text'])
audit=json.loads(text.split('CANYON_SOURCE_AUDIT ',1)[1])
if not audit['geometryChecksPassed']:raise RuntimeError('Fix actual degenerates/nonfinite/missing UV before descriptor generation')
materials=[]
for name in sorted({m for o in audit['objects'] for m in o['materials']}):
    prefix='Assets/RacingBois/Art/P08/Golden/Canyon/Textures/'+name
    spec={'sourceName':name,'baseColor':input_file(prefix+'_BaseColor.png'),'normal':input_file(prefix+'_Normal.png'),'metallicSmoothness':input_file(prefix+'_MetallicSmoothness.png'),'maxSize':2048 if name in ['Canyon_Sandstone','Canyon_Gravel','Canyon_Asphalt','Canyon_Cliff01','Canyon_Cliff02','Canyon_Cliff03'] else 512,'normalScale':.72 if name=='Canyon_Sandstone' else .5}
    if (ROOT/(prefix+'_Occlusion.png')).exists():spec['occlusion']=input_file(prefix+'_Occlusion.png')
    if name in ['Canyon_YellowPaint','Canyon_WhitePaint']:spec['baseColor']=input_file('Assets/RacingBois/Art/P08/Golden/Canyon/V13/Textures/'+name+'_BaseColor.png')
    spec['doubleSided']=name in ['Canyon_Sage','Canyon_DryGrass']
    materials.append(spec)
size=audit['boundsSize']
asset={'id':'RB_Golden_Canyon_v16','kind':'environment','concept':input_file('ArtSource/Concepts/P08/Golden/canyon-v2.png'),'conceptReview':input_file('ArtSource/Concepts/P08/Golden/canyon-v2-review.md'),'source':input_file('ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend'),'fbx':input_file('Assets/RacingBois/Art/P08/Golden/Canyon/V16/RB_Golden_Canyon.fbx'),'modelRotationEuler':{'x':0,'y':0,'z':0},'minimumSize':dict(zip('xyz',[v-.05 for v in size])),'maximumSize':dict(zip('xyz',[v+.05 for v in size])),'materials':materials,'lods':[{'height':height,'rendererPaths':[o['name'] for o in audit['objects'] if '_L%d_'%level in o['name']]} for level,height in enumerate([.5,.15,.025])],'forwardMarker':'Forward','leftMarker':'LeftRoadMarker','rightMarker':'RightRoadMarker','groundMarkers':['Ground_Origin'],'colliders':[],'isStatic':True}
asset['restPose']='file'
asset['maximumBelowGround']=abs(min(0,audit['boundsMin'][1]))+.01
(DOC/'descriptor.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n')
audit['exactInputs']=[asset['concept'],asset['conceptReview'],asset['source'],asset['fbx'],input_file('tools/p08/golden/canyon_normalize_v16.py'),input_file('tools/p08/golden/canyon_textures.py'),input_file('tools/p08/golden/canyon_refresh_images.py'),input_file('ArtSource/P08/Golden/Canyon/SourceModels/PROVENANCE.json')]
audit['scope']='Actual Blender geometry only; not Unity, lighting, visual fidelity, closed-volume, contact or performance acceptance.'
(DOC/'geometry-observations.json').write_text(json.dumps(audit,indent=2)+'\n')
print('CANYON_DESCRIPTOR',len(materials),'materials',audit['lodTriangles'],'visualAccepted false')

modules=[]
for mesh in audit['objects']:
    if '_L0_' not in mesh['name']:continue
    name=mesh['name']
    modules.append({'id':name.replace('Canyon_L0_',''),'lods':[{'height':height,'rendererPaths':[name.replace('_L0_','_L%d_'%level)]} for level,height in enumerate([.5,.15,.025])]})
(DOC/'module-lod-mapping.json').write_text(json.dumps({'schema':1,'assetId':asset['id'],'source':asset['fbx'],'scope':'Each entry needs its own Unity LODGroup/culling bounds. Do not retain one root LODGroup for the full1km scenery.','modules':modules},indent=2)+'\n')
print('CANYON_MODULE_LOD_MAPPING',len(modules),'independent modules')

asset['moduleLodMap']=input_file('docs/p08/golden/canyon/v16/module-lod-mapping.json')
(DOC/'descriptor.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n')

