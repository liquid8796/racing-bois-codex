"""Bind exact V8 candidate files for root-owned Unity import, never acceptance."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'docs/p08/golden/apex/v8/r2'
PREFIX='Assets/RacingBois/Art/P08/Golden/Apex/V8/R2/'
NAME='RB_Golden_Apex_v8_r2'
def bound(path):
    path=ROOT/path
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

receipt=json.loads((EVIDENCE/'audit-mcp.json').read_text(encoding='utf8'))
texts=[b['text'] for b in receipt['result']['content'] if b['type']=='text']
audit=json.loads(next(t for t in texts if 'APEX_V8_R2_GEOMETRY_AUDIT ' in t).split('APEX_V8_R2_GEOMETRY_AUDIT ',1)[1].strip())
bindings=[]
for name in sorted({m for item in audit['meshes'] for m in item['materials']}):
    if '.' in name:raise RuntimeError('Unexpected duplicate material name '+name)
    size=2048 if name=='Apex_Pearl' else 512 if name in ['Apex_Glass','Apex_Lens','Apex_Lamp','Apex_RedLamp'] else 1024
    material={'sourceName':name,'baseColor':bound(PREFIX+name+'_BaseColor.png'),
        'normal':bound(PREFIX+name+'_Normal.png'),'metallicSmoothness':bound(PREFIX+name+'_MetallicSmoothness.png'),
        'normalScale':.38,'maxSize':size,'transparent':name in ['Apex_Glass','Apex_Lens'],
        'opacity':.68 if name=='Apex_Glass' else .20 if name=='Apex_Lens' else 1,'doubleSided':False}
    if name in ['Apex_Lamp','Apex_RedLamp']:
        material.update(emission=bound(PREFIX+name+'_Emission.png'),emissionIntensity=.8 if name=='Apex_Lamp' else 1.5)
    bindings.append(material)
asset={'id':NAME,'kind':'bike',
    'concept':bound('ArtSource/Concepts/P08/Golden/apex-v2.png'),
    'conceptReview':bound('ArtSource/Concepts/P08/Golden/apex-v2-review.md'),
    'source':bound('ArtSource/P08/Golden/Apex/V8/R2/'+NAME+'.blend'),
    'fbx':bound(PREFIX+NAME+'.fbx'),
    'modelRotationEuler':{'x':0,'y':0,'z':0},
    'minimumSize':{'x':.79,'y':1.14,'z':2.02},'maximumSize':{'x':.88,'y':1.23,'z':2.12},
    'materials':bindings,
    'lods':[{'height':height,'rendererPaths':['Apex_L%d_Body'%level,NAME+'_Wheel_Front/Apex_L%d_Front'%level,NAME+'_Wheel_Rear/Apex_L%d_Rear'%level]} for level,height in enumerate([.30,.115,.018])],
    'forwardMarker':'Forward','leftMarker':'Semantic_Left','rightMarker':'Semantic_Right',
    'groundMarkers':['Ground_Front','Ground_Rear'],'wheelPivots':[NAME+'_Wheel_Front',NAME+'_Wheel_Rear'],
    'colliders':[{'type':'box','center':{'x':0,'y':.51,'z':0},'size':{'x':.45,'y':1.02,'z':1.95}}],
    'isStatic':False}
(EVIDENCE/'descriptor.json').write_text(json.dumps({'schema':1,'assets':[asset]},indent=2)+'\n',encoding='utf8')
audit['exactInputs']=[asset['concept'],asset['conceptReview'],asset['source'],asset['fbx']]+[bound('tools/p08/golden/'+file) for file in ['apex_v8_r2_prepare.py', 'apex_v8_r2_surfaces.py', 'apex_v8_r2_model.py', 'apex_v8_r2_textures.py', 'apex_v8_r2_finalize.py', 'apex_v8_r2_cap_repair.py', 'apex_v8_r2_studio.py', 'apex_v8_r2_audit.py']]
audit['descriptor']=bound('docs/p08/golden/apex/v8/r2/descriptor.json')
audit['renders']=[bound(p.relative_to(ROOT).as_posix()) for p in EVIDENCE.glob('apex-*-final.png')]
(EVIDENCE/'geometry-observations.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')
print('V8 exact inputs bound; candidate unaccepted. LOD triangles: '+str([sum(m['triangles'] for m in audit['meshes'] if '_L%d_'%level in m['name']) for level in range(3)]))
