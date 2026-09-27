import bpy,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';center=Vector((0,-.041,1.706));radii=Vector((.112,.124,.148));rows=[]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for level in range(3):
    obj=bpy.data.objects['AshV5_L'+str(level)+'_Skin'];m=obj.data
    assert not obj.get('v5_hair_shell_fit',False)
    ids=set(i for p in m.polygons if 'Hair' in m.materials[p.material_index].name or 'Forelock' in m.materials[p.material_index].name for i in p.vertices)
    changed=0;maximum=0
    for i in ids:
        p=m.vertices[i].co.copy();q=Vector(((p.x-center.x)/radii.x,(p.y-center.y)/radii.y,(p.z-center.z)/radii.z));length=q.length
        if length<1e-6:continue
        phi=math.atan2(q.x,-q.y);angle=abs(phi);theta=math.acos(max(-1,min(1,q.z/length)))
        edge=1.27+.86*smooth((angle-.58)/.65)-.22*smooth((angle-1.75)/(math.pi-1.75));target=p.copy()
        if theta<edge+.025 and length>.94:target=center+(p-center)*(.94/length)
        elif abs(p.x)>.080 and p.z>1.704 and p.y<-.12:target.x*=.88
        delta=target-p
        if delta.length:
            saved=[k.data[i].co.copy() for k in m.shape_keys.key_blocks];m.vertices[i].co=target
            for key,co in zip(m.shape_keys.key_blocks,saved):key.data[i].co=co+delta
            maximum=max(maximum,delta.length);changed+=1
    m.update();obj['v5_hair_shell_fit']=True;rows.append({'lod':level,'hairVerticesFitted':changed,'maximumDeltaMetres':maximum})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',compress=False)
print('ASH_V5_HAIR_SHELL_FIT '+json.dumps(rows))
