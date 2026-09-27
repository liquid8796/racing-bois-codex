"""Exact constant glass PBR data; no borrowed V2 map mutation or painted reflections."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/';FOLDER=ROOT+'ArtSource/P08/Golden/Ash/V7/Textures/';size=512
values={'BaseColor':(.26,.095,.016,1),'Normal':(.5,.5,1,1),'MetallicSmoothness':(0,1,0,.895),'Occlusion':(1,1,1,1)}
mat=bpy.data.materials.new('AshV7_AmberGlass_Baked');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];textures={};rows=[]
for channel,color in values.items():
 name='AshV7_AmberGlass_'+channel;image=bpy.data.images.new(name,width=size,height=size,alpha=True,float_buffer=False);image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';image.generated_color=color
 if channel=='MetallicSmoothness':image.alpha_mode='CHANNEL_PACKED'
 image.filepath_raw=FOLDER+name+'.png';image.file_format='PNG';image.save()
 decoded=bpy.data.images.load(image.filepath_raw,check_existing=False);decoded.colorspace_settings.name=image.colorspace_settings.name
 if channel=='MetallicSmoothness':decoded.alpha_mode='CHANNEL_PACKED'
 decoded.reload();decoded.pack();tex=nodes.new('ShaderNodeTexImage');tex.image=decoded;textures[channel]=tex;rows.append({'channel':channel,'path':image.filepath_raw,'size':size,'constantLinearValue':color,'freshlyReloadedAndPacked':True})
links.new(textures['BaseColor'].outputs['Color'],bs.inputs['Base Color']);normal=nodes.new('ShaderNodeNormalMap');links.new(textures['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal']);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.105;bs.inputs['IOR'].default_value=1.47;bs.inputs['Alpha'].default_value=.38
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Glass'];obj.data.materials.clear();obj.data.materials.append(mat)
 for p in obj.data.polygons:p.material_index=0
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_GLASS_MAPS '+json.dumps({'material':mat.name,'maps':rows,'transparent':True,'opacity':.38,'roughness':.105,'ior':1.47,'doubleSided':False,'usesScreenSpaceRefraction':False,'sourcePreviewUsesAlphaBlendedPrincipled':True,'paintedReflectionOrBackground':False,'visualAccepted':False}))
