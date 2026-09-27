"""Bake a continuous boot/sole boundary and remove unrelated shoe normal detail.

The locked Ash concept specifies dark leather boots, not the laces embedded
in the borrowed anatomical shoe normal. V2 maps remain immutable.
"""
import bpy,bmesh,json
from mathutils import Matrix
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
source=bpy.data.objects['AshV3_L0_Skin'];copy=source.copy();copy.data=source.data.copy();scene.collection.objects.link(copy);copy.name='AshV3_BootBakeOnly';copy.shape_key_clear()
for modifier in list(copy.modifiers):copy.modifiers.remove(modifier)
roles=['BootLeather','Rubber'];source_names=[prefix+role+'_Baked' for role in roles for prefix in ['AshV2_','AshV3_']]
bm=bmesh.new();bm.from_mesh(copy.data)
bmesh.ops.delete(bm,geom=[face for face in bm.faces if copy.data.materials[face.material_index].name not in source_names],context='FACES')
bm.to_mesh(copy.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');copy.hide_set(False);copy.select_set(True);bpy.context.view_layer.objects.active=copy;bpy.ops.object.material_slot_remove_unused()
materials=[];old_materials=[]
for original in list(copy.data.materials):
    mat=bpy.data.materials.new(original.name.replace('AshV2_','AshV3_')+'_BakeSource');mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');shader.inputs['Roughness'].default_value=.76 if 'Rubber' in original.name else .65
    geometry=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geometry.outputs['Position'],sep.inputs[0])
    ramp=nodes.new('ShaderNodeMapRange');ramp.clamp=True;ramp.inputs['From Min'].default_value=.041;ramp.inputs['From Max'].default_value=.043
    links.new(sep.outputs['Z'],ramp.inputs['Value'])
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=140;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
    links.new(geometry.outputs['Position'],noise.inputs['Vector'])
    leather=nodes.new('ShaderNodeMixRGB');leather.blend_type='MIX';leather.inputs[1].default_value=(.040,.019,.008,1);leather.inputs[2].default_value=(.080,.039,.017,1);links.new(noise.outputs['Fac'],leather.inputs[0])
    factor=ramp.outputs[0]
    if 'Rubber' in original.name:
        # The same role also covers helmet seals and zipper tapes. Their
        # authored black rubber stays black; only the boot seam is recolored.
        boot=nodes.new('ShaderNodeMath');boot.operation='LESS_THAN';boot.inputs[1].default_value=.30;links.new(sep.outputs['Z'],boot.inputs[0])
        product=nodes.new('ShaderNodeMath');product.operation='MULTIPLY';links.new(factor,product.inputs[0]);links.new(boot.outputs[0],product.inputs[1]);factor=product.outputs[0]
    border=nodes.new('ShaderNodeMixRGB');border.inputs[1].default_value=(.009,.008,.007,1);links.new(leather.outputs[0],border.inputs[2]);links.new(factor,border.inputs[0]);links.new(border.outputs[0],shader.inputs['Base Color'])
    grain=nodes.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=2200;grain.inputs['Detail'].default_value=2;links.new(geometry.outputs['Position'],grain.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=0;bump.inputs['Distance'].default_value=.00002;links.new(grain.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    materials.append(mat);old_materials.append(original)
for index,material in enumerate(materials):copy.data.materials[index]=material
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12;scene.render.bake.normal_space='TANGENT'
visibility={obj:obj.hide_render for obj in bpy.data.objects if obj.type=='MESH'}
for obj in visibility:obj.hide_render=obj!=copy
paths=[]
for channel in ['BaseColor','Normal','Metallic','Roughness','Occlusion']:
    targets=[];restore=[]
    for material,original in zip(materials,old_materials):
        role=original.name[len('AshV2_'):-len('_Baked')];size=1024 if role=='BootLeather' else 512
        image=bpy.data.images.new('AshV3_'+role+'_'+channel,width=size,height=size,alpha=True)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.generated_color=(.5,.5,1,1) if channel=='Normal' else (0,0,0,1)
        directory='Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures/' if channel not in ['Metallic','Roughness'] else 'ArtSource/P08/Golden/Ash/V3/BakeIntermediate/'
        image.filepath_raw='D:/Project/Unity/racing-bois/'+directory+'AshV3_'+role+'_'+channel+'.png';image.file_format='PNG'
        nodes=material.node_tree.nodes;links=material.node_tree.links;target=nodes.new('ShaderNodeTexImage');target.image=image
        for node in nodes:node.select=False
        target.select=True;nodes.active=target;targets.append(image)
        if channel not in ['Normal','Occlusion']:
            shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');previous=output.inputs['Surface'].links[0].from_socket
            emission=nodes.new('ShaderNodeEmission');field=shader.inputs[{'BaseColor':'Base Color','Metallic':'Metallic','Roughness':'Roughness'}[channel]]
            if field.is_linked:links.new(field.links[0].from_socket,emission.inputs['Color'])
            else:
                value=field.default_value;emission.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else tuple(value)
            links.new(emission.outputs[0],output.inputs['Surface']);restore.append((material,output,previous,emission))
    bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'AO' if channel=='Occlusion' else 'EMIT',use_clear=True)
    for image in targets:image.save();paths.append(image.filepath_raw)
    for material,output,previous,emission in restore:material.node_tree.links.new(previous,output.inputs['Surface']);material.node_tree.nodes.remove(emission)
for obj,value in visibility.items():obj.hide_render=value
bpy.data.objects.remove(copy,do_unlink=True)
for original in old_materials:
    role=original.name[len('AshV2_'):-len('_Baked')];material=original if original.name.startswith('AshV3_') else original.copy();material.name=original.name.replace('AshV2_','AshV3_')
    for node in material.node_tree.nodes:
        if node.type!='TEX_IMAGE' or not node.image:continue
        channel='BaseColor' if '_BaseColor' in node.image.name else 'Normal' if '_Normal' in node.image.name else None
        if not channel:continue
        path='D:/Project/Unity/racing-bois/Assets/RacingBois/Art/P08/Golden/Ash/V3/Textures/AshV3_'+role+'_'+channel+'.png'
        image=bpy.data.images.load(path,check_existing=False);image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.reload();first=tuple(image.pixels[:4]);assert image.has_data;image.pack();node.image=image
    for level in range(3):
        obj=bpy.data.objects['AshV3_L'+str(level)+'_Skin']
        for index,slot in enumerate(obj.data.materials):
            if slot==original:obj.data.materials[index]=material
print('ASH_V3_BOOT_BAKE '+json.dumps({'files':paths,'v2MapsUnchanged':True,'bakedFromActualRuntimeUv':True,'productionAccepted':False}))
