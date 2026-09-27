"""Bind this exact new authoring revision for isolated Unity inspection."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Assets/RacingBois/Art/P08/Golden/Apex'
EVIDENCE=ROOT/'docs/p08/golden/apex'

def file_input(path):
    path=ROOT/path
    return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

audit_receipt=json.loads((EVIDENCE/'source-audit-mcp.json').read_text(encoding='utf8'))
texts=[item['text'] for item in audit_receipt['result']['content'] if item['type']=='text']
audit=json.loads(next(text for text in texts if 'APEX_GEOMETRY_AUDIT ' in text).split('APEX_GEOMETRY_AUDIT ',1)[1].strip())
source_materials=sorted({name for mesh in audit['meshes'] for name in mesh['materials']})
materials=[]
for name in source_materials:
    logical=name.split('.')[0]
    prefix='Assets/RacingBois/Art/P08/Golden/Apex/'+logical
    size=2048 if logical=='Apex_Pearl' else 512 if logical in ('Apex_Glass','Apex_Lamp','Apex_RedLamp') else 1024
    item={'sourceName':name,'baseColor':file_input(prefix+'_BaseColor.png'),'normal':file_input(prefix+'_Normal.png'),'metallicSmoothness':file_input(prefix+'_MetallicSmoothness.png'),'maxSize':size,'normalScale':.38,'transparent':logical=='Apex_Glass','opacity':.68 if logical=='Apex_Glass' else 1}
    if logical in ('Apex_Lamp','Apex_RedLamp'):
        item['emission']=file_input(prefix+'_Emission.png')
        item['emissionIntensity']=.8 if logical=='Apex_Lamp' else 1.5
    materials.append(item)

asset={'id':'RB_Golden_Apex','kind':'bike',
       'concept':file_input('ArtSource/Concepts/P08/Golden/apex-v2.png'),
       'conceptReview':file_input('ArtSource/Concepts/P08/Golden/apex-v2-review.md'),
       'source':file_input('ArtSource/P08/Golden/Apex/RB_Golden_Apex.blend'),
       'fbx':file_input('Assets/RacingBois/Art/P08/Golden/Apex/RB_Golden_Apex.fbx'),
       'modelRotationEuler':{'x':0,'y':0,'z':0},
       'minimumSize':{'x':.85,'y':1.17,'z':2.03},'maximumSize':{'x':.91,'y':1.24,'z':2.11},
       'materials':materials,
       'lods':[{'height':height,'rendererPaths':[f'Apex_L{level}_Body',f'RB_Golden_Apex_Wheel_Front/Apex_L{level}_Front',f'RB_Golden_Apex_Wheel_Rear/Apex_L{level}_Rear']} for level,height in enumerate([.30,.115,.018])],
       'forwardMarker':'Forward','groundMarkers':['Ground_Front','Ground_Rear'],
       'wheelPivots':['RB_Golden_Apex_Wheel_Front','RB_Golden_Apex_Wheel_Rear'],
       'colliders':[{'type':'box','center':{'x':0,'y':.51,'z':0},'size':{'x':.45,'y':1.02,'z':1.95}}],
       'isStatic':False}
descriptor={'schema':1,'assets':[asset]}
(EVIDENCE/'descriptor.json').write_text(json.dumps(descriptor,indent=2)+'\n',encoding='utf8')
audit['exactInputs']=[asset['concept'],asset['conceptReview'],asset['source'],asset['fbx'],file_input('tools/p08/golden/apex_model.py'),file_input('tools/p08/golden/apex_textures.py')]
audit['descriptor']=file_input('docs/p08/golden/apex/descriptor.json')
(EVIDENCE/'geometry-observations.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf8')
print('APEX_DESCRIPTOR_WRITTEN',len(source_materials),'material bindings; visual acceptance pending')
