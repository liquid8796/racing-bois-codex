"""Freeze a staged menu environment handoff; never copies into live Assets."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/p08/golden/menu-environment/v1'
def read_marker(name,marker):
    data=json.loads((OUT/name).read_text(encoding='utf-8-sig'))
    text=next(row['text'] for row in data['result']['content'] if row['type']=='text' and marker in row['text'])
    return json.JSONDecoder().raw_decode(text.split(marker,1)[1])[0]
def file(name):
    path=ROOT/name
    return {'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
audit=read_marker('geometry-audit-frontface-mcp.json','MENU_GEOMETRY_AUDIT ')
assert audit['physicalFailures']==audit['uvFailures']==audit['surfaceFrontFaceFailures']==0
export=read_marker('export-mcp.json','MENU_EXPORTED ')
template=json.loads((ROOT/'docs/p08/golden/canyon/v16/descriptor.json').read_text())['assets'][0]
asset={'id':'RB_Golden_MenuEnvironment_v1','kind':'environment',
 'concept':file('ArtSource/Concepts/P08/Golden/UI/main-v2.png'),
 'conceptReview':file('ArtSource/Concepts/P08/Golden/UI/main-v2-review.md'),
 'source':file('ArtSource/P08/Golden/MenuEnvironment/V1/RB_Golden_MenuEnvironment.blend'),
 'fbx':file('_local/p08-menu-environment-v1-staging/RB_Golden_MenuEnvironment.fbx'),
 'modelRotationEuler':{'x':0,'y':0,'z':0},'restPose':'file',
 'materials':template['materials'],'forwardMarker':'Forward','leftMarker':'LeftRoadMarker','rightMarker':'RightRoadMarker',
 'groundMarkers':['Ground_Origin'],'colliders':[],'isStatic':True,
 'maximumBelowGround':max(0,-export['boundsMinUnity'][1])+.01,
 'minimumSize':dict(zip('xyz',[hi-lo-.05 for hi,lo in zip(export['boundsMaxUnity'],export['boundsMinUnity'])])),
 'maximumSize':dict(zip('xyz',[hi-lo+.05 for hi,lo in zip(export['boundsMaxUnity'],export['boundsMinUnity'])])),
 'lods':[{'height':h,'rendererPaths':[o['name'] for o in export['objects'] if '_L%d_'%level in o['name']]} for level,h in enumerate([.5,.15,.025])]}
modules=[{'id':o['name'].split('_L0_',1)[1], 'lods':[{'height':height,'rendererPaths':[o['name'].replace('_L0_','_L%d_'%level)]} for level,height in enumerate([.5,.15,.025])]}
 for o in export['objects'] if '_L0_' in o['name']]
mapping={'schema':1,'assetId':asset['id'],'source':asset['fbx'],'scope':'Passive menu overlook; independent module LOD/culling. Not a playable authority route.','modules':modules}
(OUT/'module-lod-mapping-staged.json').write_text(json.dumps(mapping,indent=2)+'\n')
asset['moduleLodMap']=file('docs/p08/golden/menu-environment/v1/module-lod-mapping-staged.json')
(OUT/'descriptor-staged.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n')
delivery={'schema':1,'source':asset['source'],'fbx':asset['fbx'],'descriptor':file('docs/p08/golden/menu-environment/v1/descriptor-staged.json'),
 'stagingOnly':True,'visualAccepted':False,'nativeImported':False,'modules':len(modules),'meshes':len(export['objects']),
 'sourceTriangles':sum(o['triangles'] for o in export['objects']),'geometryAudit':file('docs/p08/golden/menu-environment/v1/geometry-audit-frontface-mcp.json'),
 'integration':'Root must publish to a fresh Assets path then rebind FBX + module-map and descriptor hashes. Do not import the staging-only descriptor as production.',
 'camera':{'positionUnity':{'x':2.97608256,'y':1.50701666,'z':1.88716865},'cameraDirectionFromHero':[1.6,.32,1], 'verticalFov':35,'aspect':16/9,'blenderShiftX':-.2219,'blenderShiftY':0,'note':'Same fixed bike view as root fixture; Unity computes off-center projection from actual posed actors. Blender shift approximates that current framing.'},
 'derivedFrom':file('ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend'),
 'scripts':[file('tools/p08/golden/'+name) for name in ['menu_environment_v3.py','menu_finish_v4.py','menu_surface_frontfaces.py','menu_geometry_audit.py','menu_export.py']],
 'limits':['Actual camera comparison required in Unity with root HDR/fog calibration.','No contact colliders: passive menu display; actor root remains at origin on the pullout.','Cliff silhouette/bedding, ground-edge detail and final lighting remain visually unaccepted.']}
(OUT/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps({k:delivery[k] for k in ['fbx','modules','meshes','sourceTriangles','visualAccepted']},indent=2))
