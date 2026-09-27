"""Fork V3 and tailor continuous clothing without replacing its rig/12 actions."""
import bpy,math,json
from mathutils import Matrix,Vector
ROOT='D:/Project/Unity/racing-bois/'
assert '/Ash/V3/' in bpy.data.filepath.replace('\\','/')
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
root=bpy.data.objects['RB_Golden_Ash_V3'];root.name='RB_Golden_Ash_V4'
rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):
    obj=bpy.data.objects['AshV3_L'+str(level)+'_Skin'];obj.name='AshV4_L'+str(level)+'_Skin'
    for key in obj.data.shape_keys.key_blocks:key.value=0
    obj.hide_render=level!=0;obj.hide_set(level!=0)
reference=bpy.data.collections['ApexR2_ContactReferenceOnly'];reference.hide_render=True
floor=bpy.data.objects['AshV2_ReviewFloor'];floor.location.z=.022
bpy.context.view_layer.update()
PREFIX='RB_P06_Rider_L0_'

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def stroke(x,z,a,b,width):
    p=Vector((x,z));a=Vector(a);b=Vector(b);edge=b-a;t=max(0,min(1,(p-a).dot(edge)/edge.length_squared))
    d=(p-a-edge*t).length
    return math.exp(-.5*(d/width)**2)*math.sin(math.pi*t)**.6
folds=[((.028,1.342),(.154,1.271),.010,.0040),((.048,1.253),(.184,1.213),.009,.0033),
    ((.095,1.170),(.197,1.196),.008,.0032),((.080,1.375),(.199,1.350),.007,.0026),
    ((.036,1.105),(.141,1.126),.007,.0022)]
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];mesh=obj.data
    ids=set(v for poly in mesh.polygons if mesh.materials[poly.material_index].name=='AshV2_TailoredClothing_Baked' for v in poly.vertices)
    maximum=0;changed=0
    for index in ids:
        vertex=mesh.vertices[index];p=vertex.co.copy();delta=Vector();x,y,z=p
        if 1.075<z<1.435 and abs(x)<.224:
            envelope=smooth((z-1.075)/.035)*smooth((1.435-z)/.045)
            waist=math.exp(-((z-1.14)/.14)**2)
            delta.x-=x*.07*waist*envelope
            delta.y-=(y+.018)*.055*waist*envelope
            if y<-.042:
                amount=0
                for a,b,width,height in folds:
                    az=a[1]+(.006 if x<0 else 0);bz=b[1]-(.004 if x<0 else 0)
                    amount+=height*stroke(abs(x),z,(a[0],az),(b[0],bz),width)
                    amount-=height*.28*stroke(abs(x),z,(a[0],az-.012),(b[0],bz-.012),width*.85)
                delta.y-=amount*envelope
            elif y>.012:
                amount=.0022*stroke(abs(x),z,(.040,1.350),(.186,1.269),.012)
                amount+=.0030*stroke(abs(x),z,(.072,1.200),(.191,1.232),.010)
                delta.y+=amount*envelope
        if abs(x)>.222 and z>1.135:
            side='L' if x>0 else 'R';best=None
            for role in ['UpperArm_','Forearm_']:
                bone=rig.data.bones[PREFIX+role+side];a=bone.head_local;axis=(bone.tail_local-a).normalized();length=bone.length
                t=max(0,min(length,(p-a).dot(axis)));center=a+axis*t;radial=p-center
                if best is None or radial.length<best[0]:best=(radial.length,role,radial,t,length)
            distance,role,radial,t,length=best
            if radial.length>.015:
                angle=math.atan2(radial.y,radial.x*(1 if x>0 else -1))
                joint_distance=length-t if role=='UpperArm_' else t
                influence=math.exp(-((joint_distance-.045)/.065)**2)*smooth((length-t)/.045)
                ridge=.0032*math.sin(t*91+1.6*angle+.65)*influence
                ridge+=.0018*math.sin(t*148-2.1*angle)*influence
                delta+=radial.normalized()*ridge
        if delta.length:
            old_keys=[key.data[index].co.copy() for key in mesh.shape_keys.key_blocks]
            vertex.co=p+delta
            for key,old in zip(mesh.shape_keys.key_blocks,old_keys):key.data[index].co=old+delta
            maximum=max(maximum,delta.length);changed+=1
    mesh.update()
    attr=mesh.attributes.get('AshV4_RestMeters') or mesh.attributes.new('AshV4_RestMeters','FLOAT_VECTOR','POINT')
    for vertex in mesh.vertices:attr.data[vertex.index].vector=vertex.co
    rows.append({'lod':level,'garmentVertices':len(ids),'sculptedVertices':changed,'maximumDeltaMetres':maximum})
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_TAILOR '+json.dumps({'lods':rows,'bones':len(rig.data.bones),'actions':[a.name for a in bpy.data.actions if a.name.startswith('RB_')],'rigAndGameplayActionsEdited':False,'v3Preserved':True,'visualAccepted':False}))
