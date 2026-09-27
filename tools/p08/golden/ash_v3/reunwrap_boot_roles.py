"""Give boot/rubber roles actual packed UV islands and transfer to every LOD."""
import bpy,bmesh,math,json
from mathutils import Matrix
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();lod0=bpy.data.objects['AshV3_L0_Skin'];report=[]
for previous in list(bpy.data.objects):
    if previous.name.startswith(('AshV3_UVTransferSource_','AshV3_UVTransferTarget_')):bpy.data.objects.remove(previous,do_unlink=True)
def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
def subset(obj,role,name):
    copy=obj.copy();copy.data=obj.data.copy();scene.collection.objects.link(copy);copy.name=name;copy.shape_key_clear()
    for modifier in list(copy.modifiers):copy.modifiers.remove(modifier)
    marker=copy.data.attributes.new('AshOriginalLoop','INT','CORNER')
    for i,item in enumerate(marker.data):item.value=i
    bm=bmesh.new();bm.from_mesh(copy.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if role not in copy.data.materials[f.material_index].name],context='FACES')
    bm.to_mesh(copy.data);bm.free();return copy
for role in ['BootLeather','Rubber']:
    active(lod0);lod0.data.uv_layers.active_index=0
    unaffected={i:tuple(lod0.data.uv_layers.active.data[i].uv) for polygon in lod0.data.polygons if role not in lod0.data.materials[polygon.material_index].name for i in polygon.loop_indices}
    bpy.context.tool_settings.mesh_select_mode=(False,False,True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
    for polygon in lod0.data.polygons:polygon.select=role in lod0.data.materials[polygon.material_index].name
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.016,area_weight=.8,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
    assert all(tuple(lod0.data.uv_layers.active.data[i].uv)==uv for i,uv in unaffected.items()),'Unrelated material UV was changed'
    reference=subset(lod0,role,'AshV3_UVTransferSource_'+role);reference.hide_render=True
    for level in [1,2]:
        target=bpy.data.objects['AshV3_L'+str(level)+'_Skin'];temporary=subset(target,role,'AshV3_UVTransferTarget_'+role);active(temporary)
        modifier=temporary.modifiers.new('Preserve authored role UV across LODs','DATA_TRANSFER');modifier.object=reference;modifier.use_loop_data=True;modifier.data_types_loops={'UV'};modifier.loop_mapping='POLYINTERP_NEAREST';modifier.layers_uv_select_src='UV0';modifier.layers_uv_select_dst='UV0'
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        original=temporary.data.attributes['AshOriginalLoop'];uv=temporary.data.uv_layers.active
        for index,item in enumerate(original.data):target.data.uv_layers.active.data[item.value].uv=uv.data[index].uv
        report.append({'role':role,'level':level,'transferredLoops':len(original.data)})
        bpy.data.objects.remove(temporary,do_unlink=True)
    bpy.data.objects.remove(reference,do_unlink=True)
print('ASH_V3_PACKED_ROLE_UV '+json.dumps(report))
