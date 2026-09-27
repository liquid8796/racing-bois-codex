"""Hash-bound inspection contract for the authored indoor workshop."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/garage/v1'

def input_file(path):
    p=ROOT/path;return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

receipt=json.loads((DOC/'source-audit-final-mcp.json').read_text())
audit=json.loads(receipt['result']['structuredContent']['result'].split('GARAGE_SOURCE_AUDIT ',1)[1]);assert audit['geometryChecksPassed']
materials=[]
for name in sorted({m for o in audit['objects'] for m in o['materials']}):
    prefix='Assets/RacingBois/Art/P08/Golden/Garage/V1/Textures/'+name
    spec={'sourceName':name,'baseColor':input_file(prefix+'_BaseColor.png'),'normal':input_file(prefix+'_Normal.png'),'metallicSmoothness':input_file(prefix+'_MetallicSmoothness.png'),'maxSize':2048 if name in ['Garage_Floor','Garage_Concrete'] else 512,'normalScale':.55 if name=='Garage_Floor' else .6 if name=='Garage_Concrete' else 1}
    if (ROOT/(prefix+'_Occlusion.png')).exists():spec['occlusion']=input_file(prefix+'_Occlusion.png')
    if name=='Garage_Lamp':spec['emission']=input_file(prefix+'_Emission.png');spec['emissionIntensity']=6
    materials.append(spec)
colliders=[]
def box(center,size):colliders.append({'type':'box','center':dict(zip('xyz',center)),'size':dict(zip('xyz',size))})
box([0,-.09,0],[12,.18,11.998])
box([0,1.6,4.53],[12,3.2,.18])
box([-4.15,1.65,3.5],[3.597,3.3,.3])
box([.82,1.65,4.24],[.44,3.3,.46])
box([0,3.53,.6],[12,.18,7.8])
for x,z,w,h in [(-1.83,3.94,.51,.91),(-1.27,4.04,.30,.90),(-.16,4.04,.30,.90),(2.86,4.03,1.30,.87)]:box([x,h/2,z],[w,h,.46])
box([-1.04,.957,4.02],[2.18,.046,.54])
for y in [.19,.50]:box([-.72,y,4.07],[.75,.026,.40])
for x in [4.70,5.68]:
    for z in [3.86,4.38]:box([x,1.08,z],[.035,2.16,.035])
for y in [.13,.69,1.25,1.85]:box([5.19,y,4.12],[1.04,.035,.58])
size=audit['boundsSize']
asset={'id':'RB_Golden_Garage_v1','kind':'environment','concept':input_file('ArtSource/Concepts/P08/Golden/garage-environment-v1.png'),'conceptReview':input_file('ArtSource/Concepts/P08/Golden/garage-environment-v1-review.md'),'source':input_file('ArtSource/P08/Golden/Garage/V1/RB_Golden_Garage.blend'),'fbx':input_file('Assets/RacingBois/Art/P08/Golden/Garage/V1/RB_Golden_Garage.fbx'),'modelRotationEuler':{'x':0,'y':0,'z':0},'restPose':'file','minimumSize':dict(zip('xyz',[v-.025 for v in size])),'maximumSize':dict(zip('xyz',[v+.025 for v in size])),'maximumBelowGround':.19,'materials':materials,'lods':[{'height':height,'rendererPaths':[o['name'] for o in audit['objects'] if '_L%d_'%level in o['name']]} for level,height in enumerate([.35,.10,.015])],'forwardMarker':'Forward','leftMarker':'LeftRoadMarker','rightMarker':'RightRoadMarker','groundMarkers':['Ground_Origin'],'colliders':colliders,'isStatic':True}
modules=[]
for o in audit['objects']:
    if '_L0_' in o['name']:modules.append({'id':o['name'].replace('Garage_L0_',''),'lods':[{'height':height,'rendererPaths':[o['name'].replace('_L0_','_L%d_'%level)]} for level,height in enumerate([.35,.10,.015])]})
(DOC/'module-lod-mapping.json').write_text(json.dumps({'schema':1,'assetId':asset['id'],'source':asset['fbx'],'scope':'Authored indoor modules with individual LOD and culling; opaque closed geometry.','modules':modules},indent=2)+'\n')
asset['moduleLodMap']=input_file('docs/p08/golden/garage/v1/module-lod-mapping.json')
(DOC/'descriptor.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n')
positions=[[-1.75,2.14,4.09],[-.45,2.02,4.09],[1.51,1.87,4.14],[3.27,2.19,4.09],[5.16,2.02,3.76],[-1.10,3.17,2.41]]
widths=[.73,.36,.25,.76,.54,.42];powers=[60,35,25,65,40,40]
lighting={'schema':1,'source':asset['source'],'descriptor':input_file('docs/p08/golden/garage/v1/descriptor.json'),'lockedUi':input_file('ArtSource/Concepts/P08/Golden/UI/garage-v2.png'),'cameraPositionUnity':[0,.97,-7],'cameraTargetUnity':[0,.13,4.2],'cameraFocalLengthMm':40,'sensorWidthMm':36,'aspect':16/9,'blenderExposure':.3,'blenderViewTransform':'AgX - Medium High Contrast','unitsWarning':'Authored Blender watts and colors are measured source inputs, not a claim of numerically identical Unity light intensity. Native lightmap and reflection response require calibration.','areaLights':[],'ambientColorLinear':[.10,.12,.16],'ambientStrength':.1,'reviewOnly':True,'visualAccepted':False}
for i,p in enumerate(positions):lighting['areaLights'].append({'name':'Practical_%d'%i,'positionUnity':p,'targetUnity':[p[0],.3,p[2]-.5],'widthMetres':widths[i],'heightMetres':.04,'colorLinear':[1,.63,.30],'blenderWatts':powers[i]})
lighting['areaLights'].append({'name':'DoorSoftAmbient','positionUnity':[.2,2.9,-2.8],'targetUnity':[.2,.7,3.7],'widthMetres':5,'heightMetres':3,'colorLinear':[.85,.90,1],'blenderWatts':220})
lighting['reflectionProbe']={'positionUnity':[0,1,0],'sizeMetres':[12,3.8,12],'boxProjection':True,'near':.05,'far':30,'suggestedResolution':256}
(DOC/'lighting.json').write_text(json.dumps(lighting,indent=2)+'\n')
(DOC/'geometry-observations.json').write_text(json.dumps(audit,indent=2)+'\n')
print('GARAGE_DESCRIPTOR',len(modules),'modules',len(materials),'materials',len(colliders),'primitive colliders',audit['lodTriangles'],'visualAccepted false')
