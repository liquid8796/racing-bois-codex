"""Prepare a hash-bound R3 handoff; optional publication is root-controlled."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];DOC=ROOT/'docs/p08/golden/apex/r3'
STAGED='_local/p08-apex-r3-staging/RB_Golden_Apex_r3.fbx'
DEST='Assets/RacingBois/Art/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3.fbx'
NAME='RB_Golden_Apex_r3';TEXTURES='Assets/RacingBois/Art/P08/Golden/Apex/V8/R2/'
parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');args=parser.parse_args()

def bind(path):
    p=ROOT/path;return {'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

j=json.loads((DOC/'audit-final-clean-mcp.json').read_text())
audit=json.loads(j['result']['structuredContent']['result'].split('APEX_R3_GEOMETRY_AUDIT ',1)[1])
for mesh in audit['meshes']:
    assert mesh['unityDegenerateTriangles']==mesh['zeroAreaUVTriangles']==mesh['nonManifoldEdges']==0,mesh['name']
j=json.loads((DOC/'roundtrip-final-mcp.json').read_text());roundtrip=json.loads(j['result']['structuredContent']['result'].split('APEX_R3_ROUNDTRIP ',1)[1]);assert roundtrip['passed'] and roundtrip['exactPerMeshTriangleCounts']
materials=[]
for name in sorted({m for mesh in audit['meshes'] for m in mesh['materials']}):
    assert '.' not in name,name
    spec={'sourceName':name,'baseColor':bind(TEXTURES+name+'_BaseColor.png'),'normal':bind(TEXTURES+name+'_Normal.png'),'metallicSmoothness':bind(TEXTURES+name+'_MetallicSmoothness.png'),'normalScale':.38,'maxSize':2048 if name=='Apex_Pearl' else 512 if name in ['Apex_Glass','Apex_Lens','Apex_Lamp','Apex_RedLamp'] else 1024,'transparent':name in ['Apex_Glass','Apex_Lens'],'opacity':.68 if name=='Apex_Glass' else .20 if name=='Apex_Lens' else 1,'doubleSided':False}
    if name in ['Apex_Lamp','Apex_RedLamp']:spec.update(emission=bind(TEXTURES+name+'_Emission.png'),emissionIntensity=.8 if name=='Apex_Lamp' else 1.5)
    materials.append(spec)
size=audit['unityIntendedSize'];fbx=bind(STAGED)
asset={'id':NAME,'kind':'bike','concept':bind('ArtSource/Concepts/P08/Golden/apex-v2.png'),'conceptReview':bind('ArtSource/Concepts/P08/Golden/apex-v2-review.md'),'source':bind('ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_assembled.blend'),'fbx':{'path':DEST,'sha256':fbx['sha256']},'restPose':'file','modelRotationEuler':dict.fromkeys('xyz',0),'minimumSize':dict(zip('xyz',[v-.02 for v in size])),'maximumSize':dict(zip('xyz',[v+.02 for v in size])),'materials':materials,'lods':[{'height':height,'rendererPaths':['Apex_L%d_Body'%level,NAME+'_Wheel_Front/Apex_L%d_Front'%level,NAME+'_Wheel_Rear/Apex_L%d_Rear'%level]} for level,height in enumerate([.30,.115,.018])],'forwardMarker':'Forward','leftMarker':'Semantic_Left','rightMarker':'Semantic_Right','groundMarkers':['Ground_Front','Ground_Rear'],'wheelPivots':[NAME+'_Wheel_Front',NAME+'_Wheel_Rear'],'colliders':[{'type':'box','center':{'x':0,'y':.51,'z':0},'size':{'x':.45,'y':1.02,'z':1.95}}],'isStatic':False}
descriptor={'schema':1,'assets':[asset]}
manifest={'schema':1,'status':'staged_for_root_review','visualAccepted':False,'stagedFbx':fbx,'destinationFbx':DEST,'descriptorAfterCopy':descriptor,'editableSource':bind('ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend'),'physicalRoundtripTriangles':roundtrip['triangles'],'actualLodTriangles':[sum(m['triangles'] for m in audit['meshes'] if '_L%d_'%level in m['name']) for level in range(3)],'code':[bind('tools/p08/golden/'+name) for name in ['apex_r3_author.py','apex_r3_nose.py','apex_r3_cdt_helpers.py','apex_r3_assemble.py','apex_r3_export_staged.py','apex_r3_roundtrip.py']],'scope':'Structural and authoring candidate only; native Unity/visual/performance acceptance pending. No production masks or previous assets are replaced.'}
(DOC/'handoff-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if args.publish:
    target=ROOT/DEST;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==fbx['sha256'],'Refuse replacing another published candidate'
    else:shutil.copy2(ROOT/STAGED,target)
    assert bind(DEST)==asset['fbx']
    (DOC/'descriptor.json').write_text(json.dumps(descriptor,indent=2)+'\n')
    print('R3 published for native inspection; visualAccepted=false')
else:print('R3 staged only; root may publish with --publish when Unity is ready')
print(json.dumps({'fbx':fbx,'lodTriangles':manifest['actualLodTriangles'],'materials':len(materials),'visualAccepted':False}))
