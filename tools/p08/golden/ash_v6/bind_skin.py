"""Pack numeric PBR channels inside Blender and bind freshly decoded runtime maps."""
import bpy,json,math,array
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';FOLDER=ROOT+'ArtSource/P08/Golden/Ash/V6/Textures/';RAW=ROOT+'ArtSource/P08/Golden/Ash/V6/BakeIntermediate/'
source=[m for m in bpy.data.objects['AshV6_L0_Skin'].data.materials if m.get('ash_v6_source_role','')]
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6_Procedural.blend',compress=False)
rows=[];replacement={}
for material in source:
    role=material['ash_v6_source_role'];prefix='AshV6_'+role;material.use_fake_user=True
    rough=bpy.data.images.load(RAW+prefix+'_Roughness.png',check_existing=False);rough.colorspace_settings.name='Non-Color';rough.reload()
    ao=bpy.data.images.load(RAW+prefix+'_Occlusion.png',check_existing=False);ao.colorspace_settings.name='Non-Color';ao.reload()
    width,height=rough.size;count=width*height*4
    r=array.array('f',[0])*count;o=array.array('f',[0])*count;packed=array.array('f',[0])*count
    rough.pixels.foreach_get(r);ao.pixels.foreach_get(o)
    for i in range(0,count,4):packed[i]=0;packed[i+1]=o[i];packed[i+2]=0;packed[i+3]=1-r[i]
    mask=bpy.data.images.new(prefix+'_MetallicSmoothness',width=width,height=height,alpha=True,float_buffer=False)
    mask.colorspace_settings.name='Non-Color';mask.alpha_mode='CHANNEL_PACKED';mask.pixels.foreach_set(packed)
    mask.filepath_raw=FOLDER+prefix+'_MetallicSmoothness.png';mask.file_format='PNG';mask.save()
    mat=bpy.data.materials.new(prefix+'_Baked');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];loaded={};bindings=[]
    for channel in ['BaseColor','Normal','MetallicSmoothness','Occlusion']:
        path=FOLDER+prefix+'_'+channel+'.png';image=bpy.data.images.load(path,check_existing=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        if channel=='MetallicSmoothness':image.alpha_mode='CHANNEL_PACKED'
        image.reload();probe=tuple(image.pixels[:4]);assert image.has_data
        image.pack();assert image.packed_file is not None
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;loaded[channel]=tex
        bindings.append({'channel':channel,'path':path,'size':list(image.size),'reloadedAndPacked':True})
    links.new(loaded['BaseColor'].outputs['Color'],bs.inputs['Base Color'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1;links.new(loaded['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
    separate=nodes.new('ShaderNodeSeparateColor');links.new(loaded['MetallicSmoothness'].outputs['Color'],separate.inputs['Color']);links.new(separate.outputs['Red'],bs.inputs['Metallic'])
    invert=nodes.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1;links.new(loaded['MetallicSmoothness'].outputs['Alpha'],invert.inputs[1]);links.new(invert.outputs[0],bs.inputs['Roughness'])
    # Match the intended URP Lit surface. AO remains separate for native
    # ambient-only occlusion; it is not multiplied into the albedo here.
    bs.inputs['Coat Weight'].default_value=0;bs.inputs['Subsurface Weight'].default_value=0
    mat['texture_size']=int(material['texture_size']);mat['source_material']=material.name;mat['uses_alpha']=False
    replacement[material.name]=mat
    rows.append({'role':role,'sourceMaterial':material.name,'runtimeMaterial':mat.name,'bindings':bindings,'maskChannels':'R=0 dielectric,G=AO,B=0,A=1-roughness','normalConvention':'OpenGL tangent','alphaSurface':False})
for level in range(3):
    obj=bpy.data.objects['AshV6_L'+str(level)+'_Skin']
    for i,mat in enumerate(obj.data.materials):
        if mat.name in replacement:obj.data.materials[i]=replacement[mat.name]
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_RUNTIME_MAPS '+json.dumps({'roles':rows,'newMapCount':len(rows)*4,'assetsFolderWritten':False,'visualAcceptance':False}))
