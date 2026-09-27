"""Read anatomical contact landmarks without mutating frozen V2 artifacts."""
import bpy,json
from mathutils import Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];prefix='RB_P06_Rider_L0_'
report={'bones':{},'sourceObjects':{}}
for name in ['Hand_L','Foot_L','Thigh_L','Hip']+['Finger_'+digit+'_'+str(segment)+'_L' for digit in ['Thumb','Index','Middle','Ring','Pinky'] for segment in [1,2,3]]:
    b=rig.data.bones[prefix+name]
    report['bones'][name]={'head':list(b.head_local),'tail':list(b.tail_local),'matrix':[list(row) for row in b.matrix_local]}
for name in ['AshV2_ArticulatedGloves','AshV2_Shoes','AshV2_Clothes']:
    obj=bpy.data.objects.get(name)
    if not obj:continue
    samples=[]
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        if name.endswith('Shoes') and p.x>0 and -.18<p.y<-.08:samples.append(list(p))
        elif name.endswith('Gloves') and .35<p.x<.5:samples.append(list(p))
    report['sourceObjects'][name]={'count':len(obj.data.vertices),'bounds':[[min((obj.matrix_world@v.co)[a] for v in obj.data.vertices),max((obj.matrix_world@v.co)[a] for v in obj.data.vertices)] for a in range(3)],'samples':samples[::max(1,len(samples)//24)]}
print('ASH_V3_CONTACT_GEOMETRY '+json.dumps(report))
