"""Load finalized PBR maps fresh, pack them, and export only runtime actor data.

The fixed FILE-image reload occurs after offline packing has completed. This
never reloads unsaved generated bake pixels and does not reuse cached PNG data.
"""
import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/'
TEXTURES=ROOT+'Assets/RacingBois/Art/P08/Golden/Ash/V2/Textures/'
rig=bpy.data.objects['RB_P06_Rider_Rig'];root=bpy.data.objects['RB_Golden_Ash_V2'];scene=bpy.context.scene
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
lod0=bpy.data.objects['AshV2_L0_Skin'];scratch=list(lod0.data.materials);materials=[];bindings=[]
for source in scratch:
    original=source['source_name']
    unused=bpy.data.materials.get(original+'_Baked')
    if unused and unused.users==0:bpy.data.materials.remove(unused)
    mat=bpy.data.materials.new(original+'_Baked');mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes['Principled BSDF'];loaded={}
    for channel in ['BaseColor','Normal','MetallicSmoothness','Occlusion']:
        path=TEXTURES+original+'_'+channel+'.png'
        image=bpy.data.images.load(path,check_existing=False)
        image.name='Runtime_'+original+'_'+channel
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        image.reload()
        # FILE reload invalidates decoded pixels; force the lazy decoder before
        # asserting has_data and before any preview uses the image.
        pixel_probe=tuple(image.pixels[:4])
        if image.source!='FILE' or not image.has_data:raise RuntimeError('Final texture not loaded from file '+path)
        image.pack()
        if image.packed_file is None:raise RuntimeError('Final texture not packed '+path)
        node=nodes.new('ShaderNodeTexImage');node.image=image;loaded[channel]=node
        bindings.append({'material':mat.name,'channel':channel,'image':image.name,'path':path,'size':list(image.size),'reloadedFromFile':True,'packed':True})
    # AO is carried as a separate map for Unity's ambient-only occlusion path.
    links.new(loaded['BaseColor'].outputs['Color'],p.inputs['Base Color'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1
    links.new(loaded['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
    split=nodes.new('ShaderNodeSeparateColor');links.new(loaded['MetallicSmoothness'].outputs['Color'],split.inputs[0])
    links.new(split.outputs['Red'],p.inputs['Metallic'])
    invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1
    links.new(loaded['MetallicSmoothness'].outputs['Alpha'],invert.inputs[1]);links.new(invert.outputs[0],p.inputs['Roughness'])
    if bool(source['uses_alpha']):
        links.new(loaded['BaseColor'].outputs['Alpha'],p.inputs['Alpha'])
        mat.surface_render_method='DITHERED'
    if original=='AshV2_Skin':
        p.inputs['Subsurface Weight'].default_value=.045;p.inputs['Subsurface Scale'].default_value=.013;p.inputs['Subsurface Radius'].default_value=(1,.5,.25)
    if original in ['AshV2_AmberLens','AshV2_IvoryEnamel','AshV2_Eyes']:
        p.inputs['Coat Weight'].default_value=.55;p.inputs['Coat Roughness'].default_value=.22
    mat['source_material']=original;mat['texture_size']=int(source['texture_size']);mat['uses_alpha']=bool(source['uses_alpha'])
    materials.append(mat)
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin']
    for i,material in enumerate(materials):obj.data.materials[i]=material
    for key in obj.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
export_objects=[root,rig]+[bpy.data.objects['AshV2_L'+str(level)+'_Skin'] for level in range(3)]+[bpy.data.objects[name] for name in ['Forward','Ground_L','Ground_R']]
for obj in export_objects:obj.select_set(True)
bpy.context.view_layer.objects.active=root
path=ROOT+'Assets/RacingBois/Art/P08/Golden/Ash/V2/RB_Golden_Ash_V2.fbx'
bpy.ops.export_scene.fbx(filepath=path,use_selection=True,object_types={'MESH','ARMATURE','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
                        use_mesh_modifiers=False,add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,
                        bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='AUTO')
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend',compress=False)
print('ASH_FINAL_TEXTURE_BINDINGS '+json.dumps({'bindings':bindings,'fbx':path,'bakePropertiesFromRealGeometry':True,'conceptFidelityAccepted':False,'nativeAcceptance':False}))
