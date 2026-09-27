"""Assemble an isolated V8 candidate after visual review; no acceptance claim.

Execute only in the dedicated Apex Blender session after saving editable V8.
"""
import bpy, bmesh, json, math
from mathutils import Vector

ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Apex/V8/'
OUT=ROOT+'Assets/RacingBois/Art/P08/Golden/Apex/V8/'
NAME='RB_Golden_Apex_v8'
scene=bpy.context.scene
root=bpy.data.objects[NAME]
if any(o.name.startswith('Apex_L0_') for o in root.children_recursive):
    raise RuntimeError('V8 already assembled. Reopen the editable pre-export source before repeating finalization.')
def coord(p):return Vector((p[0],p[2],p[1]))
def empty(name,p):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj)
    obj.parent=root;obj.location=coord(p);return obj
for name,p in {
    'Forward':(0,0,1.1),'Semantic_Left':(-.5,0,0),'Semantic_Right':(.5,0,0),
    'Ground_Front':(0,0,.715),'Ground_Rear':(0,0,-.715),
    'Contact_Seat':(0,.824,-.37),'Contact_Grip_L':(-.294,.927,.389),'Contact_Grip_R':(.294,.927,.389),
    'Contact_Foot_L':(-.286,.342,-.249),'Contact_Foot_R':(.286,.342,-.249)
}.items():empty(name,p)
groups={name:[] for name in ['Body','Front','Rear']}
for obj in list(root.children_recursive):
    if obj.type=='MESH':
        group=obj.get('asset_group')
        if group not in groups:raise RuntimeError('Missing explicit editable component group: '+obj.name)
        groups[group].append(obj)
source_collection=bpy.data.collections.new('Apex_V8_Editable_Components')
scene.collection.children.link(source_collection)
source_collection.hide_render=True;source_collection.hide_viewport=True
for group,objects in groups.items():
    for obj in objects:
        editable=obj.copy();editable.data=obj.data.copy();editable.parent=None
        editable.matrix_world=obj.matrix_world.copy()
        source_collection.objects.link(editable);editable.name='Source_'+obj.name
def assemble(objects,name,parent,pivot):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    obj=bpy.context.object;obj.name=name
    scene.cursor.location=coord(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    transform=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=transform
    return obj
body=assemble(groups['Body'],'Apex_L0_Body',root,(0,0,0))
front=assemble(groups['Front'],'Apex_L0_Front',bpy.data.objects[NAME+'_Wheel_Front'],(0,.315,.715))
rear=assemble(groups['Rear'],'Apex_L0_Rear',bpy.data.objects[NAME+'_Wheel_Rear'],(0,.315,-.715))
for original in [body,front,rear]:
    for level,ratio in [(1,.44),(2,.14)]:
        duplicate=original.copy();duplicate.data=original.data.copy();scene.collection.objects.link(duplicate)
        duplicate.name=original.name.replace('_L0_','_L'+str(level)+'_')
        bpy.context.view_layer.objects.active=duplicate
        modifier=duplicate.modifiers.new('LOD preserved silhouette reduction','DECIMATE')
        modifier.ratio=ratio;modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name);duplicate.hide_render=True
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Final export triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # New solidify edges get proper planar charts if their UV was collapsed.
    # Deliberate shared finish charts are documented, not claimed unique.
    uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        p=[uv.data[i].uv.copy() for i in face.loop_indices]
        area=abs(sum(p[i].x*p[(i+1)%len(p)].y-p[(i+1)%len(p)].x*p[i].y for i in range(len(p))))*.5
        if area<1e-12:
            axis=0
            for candidate in [1,2]:
                if abs(face.normal[candidate])>abs(face.normal[axis]):axis=candidate
            axes=[i for i in range(3) if i!=axis]
            for loop in face.loop_indices:
                v=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv=(v[axes[0]]*2+.5,v[axes[1]]*2+.5)
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children_recursive:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=OUT+NAME+'.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+NAME+'.blend')
print('APEX_V8_EXPORTED_PENDING_VISUAL_ACCEPTANCE '+OUT+NAME+'.fbx')
