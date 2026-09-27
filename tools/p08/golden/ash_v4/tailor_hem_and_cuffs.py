import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
rows=[]
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];mesh=obj.data
    assert not obj.get('v4_shortened_jacket',False),'Do not apply the tailoring delta twice'
    ids=set(v for p in mesh.polygons if mesh.materials[p.material_index].name=='AshV4_TailoredLeather_Source' for v in p.vertices)
    adjacent={i:set() for i in ids}
    for edge in mesh.edges:
        a,b=edge.vertices
        if a in ids and b in ids:adjacent[a].add(b);adjacent[b].add(a)
    todo=set(ids);shirt=set();pants=set()
    while todo:
        first=todo.pop();seen={first};queue=[first]
        while queue:
            for nxt in adjacent[queue.pop()]:
                if nxt in todo:todo.remove(nxt);seen.add(nxt);queue.append(nxt)
        if max(mesh.vertices[i].co.z for i in seen)>1.40:shirt.update(seen)
        else:pants.update(seen)
    before=min(mesh.vertices[i].co.z for i in shirt);maximum=0
    for index in shirt|pants:
        vertex=mesh.vertices[index];p=vertex.co.copy();delta=Vector()
        if index in shirt and p.z<1.15:delta.z=.079*smooth((1.15-p.z)/(1.15-before))
        if index in pants and .242<p.z<.71:
            side='L' if p.x>0 else 'R';bone=rig.data.bones['RB_P06_Rider_L0_'+('Shin_' if p.z<.54 else 'Thigh_')+side]
            axis=(bone.tail_local-bone.head_local).normalized();t=max(0,min(bone.length,(p-bone.head_local).dot(axis)))
            center=bone.head_local+axis*t;radial=p-center;angle=math.atan2(radial.y,radial.x)
            influence=math.exp(-((p.z-.305)/.042)**2)+.65*math.exp(-((p.z-.414)/.048)**2)+.55*math.exp(-((p.z-.637)/.045)**2)
            amount=.0027*math.sin(p.z*123+angle*1.4)*influence
            delta+=radial.normalized()*amount
        if delta.length:
            saved=[key.data[index].co.copy() for key in mesh.shape_keys.key_blocks]
            vertex.co=p+delta
            for key,co in zip(mesh.shape_keys.key_blocks,saved):key.data[index].co=co+delta
            maximum=max(maximum,delta.length)
    mesh.update()
    for vertex in mesh.vertices:mesh.attributes['AshV4_RestMeters'].data[vertex.index].vector=vertex.co
    obj['v4_shortened_jacket']=True
    rows.append({'lod':level,'jacketHemBefore':before,'jacketHemAfter':min(mesh.vertices[i].co.z for i in shirt),'maximumTailoringDelta':maximum,'pantsSeatAbove71cmUntouched':True})
collection=bpy.data.collections.get('AshV4_SewnDetails_Source')
if collection:
    for obj in list(collection.objects):
        assert obj.get('v4_detail',False),'Unexpected object in task-owned detail collection'
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(collection)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_HEM_TAILOR '+json.dumps({'lods':rows,'detailRegenerationRequired':True,'rigAndGameplayActionsEdited':False}))
