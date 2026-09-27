"""Retain the dense authoring mesh and select measured desktop runtime LODs."""
import bpy,json
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
high=bpy.data.objects['AshV2_L0_Skin'];middle=bpy.data.objects['AshV2_L1_Skin'];far=bpy.data.objects['AshV2_L2_Skin']
high.name='AshV2_HighResSource'
for collection in list(high.users_collection):collection.objects.unlink(high)
bpy.data.collections['AshV2_Editable_Source'].objects.link(high);high.hide_render=True
middle.name='AshV2_L0_Skin';middle.hide_render=False
far.name='AshV2_L1_Skin';far.hide_render=True
low=far.copy();low.data=far.data.copy();bpy.data.collections['AshV2_Runtime_LODs'].objects.link(low);low.name='AshV2_L2_Skin'
low.shape_key_clear()
for modifier in list(low.modifiers):low.modifiers.remove(modifier)
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
modifier=low.modifiers.new('Distant rider budget','DECIMATE');modifier.ratio=.30;modifier.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=modifier.name)
kd=KDTree(len(high.data.vertices))
for vertex in high.data.vertices:kd.insert(vertex.co,vertex.index)
kd.balance()
low.shape_key_add(name='Basis',from_mix=False)
for name in ['Happy','Focused']:
    source_key=high.data.shape_keys.key_blocks[name];key=low.shape_key_add(name=name,from_mix=False);key.value=0
    for vertex in low.data.vertices:
        delta=Vector();total=0
        for point,index,distance in kd.find_n(vertex.co,3):
            weight=1/max(distance,.00001)**2;total+=weight
            delta+=(source_key.data[index].co-high.data.vertices[index].co)*weight
        key.data[vertex.index].co+=delta/total
for vertex in low.data.vertices:
    values=[(g.group,g.weight) for g in vertex.groups if g.weight>.00001]
    def weight_value(pair):return pair[1]
    values.sort(key=weight_value,reverse=True);values=values[:4];total=sum(w for i,w in values)
    if total<=0:raise RuntimeError('Unweighted distant rider vertex')
    old=[g.group for g in vertex.groups]
    for index in old:low.vertex_groups[index].remove([vertex.index])
    for index,weight in values:low.vertex_groups[index].add([vertex.index],weight/total,'REPLACE')
modifier=low.modifiers.new('Anatomical skin deformation','ARMATURE');modifier.object=rig;low.hide_render=True
counts=[]
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];obj.data.calc_loop_triangles()
    counts.append({'level':level,'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles)})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_RUNTIME_BUDGET '+json.dumps({'lods':counts,'source_high_retained':True,'performanceMeasured':False}))
