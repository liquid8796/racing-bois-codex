"""Create bounded per-material UV bake targets while preserving source maps."""
import bpy,json
from mathutils import Matrix
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin']
    for key in obj.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update()
lod0=bpy.data.objects['AshV2_L0_Skin'];source_materials=list(lod0.data.materials);bounds=[]
for index,material in enumerate(source_materials):
    points=[lod0.data.uv_layers.active.data[i].uv.copy() for polygon in lod0.data.polygons if polygon.material_index==index for i in polygon.loop_indices]
    bounds.append((min(p.x for p in points),min(p.y for p in points),max(p.x for p in points),max(p.y for p in points)))
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];data=obj.data;uv=data.uv_layers.active
    preserved=data.uv_layers.new(name='UVSource')
    for i,entry in enumerate(uv.data):preserved.data[i].uv=entry.uv
    for polygon in data.polygons:
        low_u,low_v,high_u,high_v=bounds[polygon.material_index]
        span_u=max(high_u-low_u,.00001);span_v=max(high_v-low_v,.00001)
        for i in polygon.loop_indices:
            p=preserved.data[i].uv
            uv.data[i].uv=(.025+.95*(p.x-low_u)/span_u,.025+.95*(p.y-low_v)/span_v)
    data.uv_layers.active_index=0;data.uv_layers[0].active_render=True;data.uv_layers[0].name='UV0'
    attr=data.attributes.new('AshSurfaceMeters','FLOAT_VECTOR','POINT')
    for vertex in data.vertices:attr.data[vertex.index].vector=vertex.co
scratch=[];metadata=[]
for source in source_materials:
    mat=source.copy();mat.name='RB_Bake_'+source.name;mat['source_name']=source.name
    size=512
    if source.name in ['AshV2_Skin','AshV2_TailoredClothing']:size=2048
    elif source.name in ['AshV2_IvoryEnamel','AshV2_Hair','AshV2_Brows','AshV2_BootLeather','AshV2_CharcoalLeather']:size=1024
    mat['texture_size']=size;mat['uses_alpha']=source.name in ['AshV2_Hair','AshV2_Brows']
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    uv_node=nodes.new('ShaderNodeUVMap');uv_node.uv_map='UVSource'
    meters=nodes.new('ShaderNodeAttribute');meters.attribute_name='AshSurfaceMeters'
    for node in nodes:
        if node.bl_idname=='ShaderNodeTexImage':links.new(uv_node.outputs['UV'],node.inputs['Vector'])
        elif node.bl_idname=='ShaderNodeNormalMap':node.uv_map='UVSource'
        elif node.bl_idname in ['ShaderNodeTexNoise','ShaderNodeTexVoronoi'] and not node.inputs['Vector'].is_linked:
            links.new(meters.outputs['Vector'],node.inputs['Vector'])
            if node.bl_idname=='ShaderNodeTexVoronoi':node.inputs['Scale'].default_value=110
            elif node.inputs['Scale'].default_value>100:node.inputs['Scale'].default_value=2200 if source.name!='AshV2_AgedBrass' else 6500
    if source.name=='AshV2_Skin':
        p=nodes['Principled BSDF'];noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3500;noise.inputs['Detail'].default_value=2
        links.new(meters.outputs['Vector'],noise.inputs['Vector'])
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.00014
        links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
        rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.46;rough.inputs['To Max'].default_value=.62
        links.new(noise.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs[0],p.inputs['Roughness'])
    scratch.append(mat);metadata.append({'sourceName':source.name,'bakeMaterial':mat.name,'size':size,'alpha':bool(mat['uses_alpha'])})
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin']
    for i,mat in enumerate(scratch):obj.data.materials[i]=mat
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=8
bpy.context.scene.render.bake.use_selected_to_active=False;bpy.context.scene.render.bake.margin=12
bpy.ops.object.select_all(action='DESELECT');lod0.select_set(True);bpy.context.view_layer.objects.active=lod0
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_BAKE_PREP '+json.dumps({'materials':metadata,'uvBoundsBefore':bounds,'uvPadding':.025,'sourceUVPreserved':True}))
