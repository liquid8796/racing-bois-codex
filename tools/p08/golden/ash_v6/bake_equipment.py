"""Bake source materials into three actual per-LOD PBR atlas sets."""
import bpy,json,array
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';RAW=ROOT+'ArtSource/P08/Golden/Ash/V6/BakeIntermediate/';OUT=ROOT+'ArtSource/P08/Golden/Ash/V6/Textures/'
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=8;scene.render.bake.normal_space='TANGENT'
rows=[]
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_Equipment'];size=int(obj['atlas_resolution']);prefix='AshV6_EquipmentL'+str(level)
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
 # Isolate the bake from camera-only reference objects and other LOD copies.
 hidden=[]
 for other in bpy.data.objects:
  if other.type=='MESH' and other!=obj:hidden.append((other,other.hide_render));other.hide_render=True
 obj.hide_render=False
 try:
  for channel in ['BaseColor','Normal','Roughness','Metallic','Occlusion']:
   image=bpy.data.images.new(prefix+'_'+channel,width=size,height=size,alpha=True,float_buffer=False);image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
   image.generated_color=(.5,.5,1,1) if channel=='Normal' else (0,0,0,1);image.filepath_raw=RAW+prefix+'_'+channel+'.png';image.file_format='PNG';restore=[];targets=[]
   for mat in obj.data.materials:
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;target=nodes.new('ShaderNodeTexImage');target.image=image
    for node in nodes:node.select=False
    target.select=True;nodes.active=target;targets.append((mat,target))
    if channel not in ['Normal','Occlusion']:
     output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');original=output.inputs['Surface'].links[0].from_socket;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');socket=bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]]
     emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
     if socket.is_linked:links.new(socket.links[0].from_socket,emission.inputs['Color'])
     else:
      value=socket.default_value;emission.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else tuple(value)
     links.new(emission.outputs[0],output.inputs['Surface']);restore.append((mat,output,original,emission))
   try:
    bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'AO' if channel=='Occlusion' else 'EMIT',use_clear=True);image.save()
   finally:
    for mat,output,original,emission in restore:mat.node_tree.links.new(original,output.inputs['Surface']);mat.node_tree.nodes.remove(emission)
    for mat,target in targets:mat.node_tree.nodes.remove(target)
   if channel in ['BaseColor','Normal','Occlusion']:
    image.filepath_raw=OUT+prefix+'_'+channel+'.png';image.save()
  values={}
  for channel in ['Roughness','Metallic','Occlusion']:
   img=bpy.data.images.load(RAW+prefix+'_'+channel+'.png',check_existing=False);img.colorspace_settings.name='Non-Color';img.reload();data=array.array('f',[0])*(size*size*4);img.pixels.foreach_get(data);values[channel]=data
  packed=array.array('f',[0])*(size*size*4)
  for i in range(0,len(packed),4):packed[i]=values['Metallic'][i];packed[i+1]=values['Occlusion'][i];packed[i+2]=0;packed[i+3]=1-values['Roughness'][i]
  mask=bpy.data.images.new(prefix+'_MetallicSmoothness',width=size,height=size,alpha=True,float_buffer=False);mask.colorspace_settings.name='Non-Color';mask.alpha_mode='CHANNEL_PACKED';mask.pixels.foreach_set(packed);mask.filepath_raw=OUT+prefix+'_MetallicSmoothness.png';mask.file_format='PNG';mask.save()
  mat=bpy.data.materials.new(prefix+'_Baked');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF'];texs={}
  for channel in ['BaseColor','Normal','MetallicSmoothness','Occlusion']:
   img=bpy.data.images.load(OUT+prefix+'_'+channel+'.png',check_existing=False);img.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
   if channel=='MetallicSmoothness':img.alpha_mode='CHANNEL_PACKED'
   img.reload();img.pack();tex=nodes.new('ShaderNodeTexImage');tex.image=img;texs[channel]=tex
  links.new(texs['BaseColor'].outputs['Color'],bs.inputs['Base Color']);normal=nodes.new('ShaderNodeNormalMap');links.new(texs['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
  split=nodes.new('ShaderNodeSeparateColor');links.new(texs['MetallicSmoothness'].outputs['Color'],split.inputs['Color']);links.new(split.outputs['Red'],bs.inputs['Metallic']);inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(texs['MetallicSmoothness'].outputs['Alpha'],inv.inputs[1]);links.new(inv.outputs[0],bs.inputs['Roughness'])
  obj.data.materials.clear();obj.data.materials.append(mat)
  for p in obj.data.polygons:p.material_index=0
  mod=obj.modifiers.new('Preserved Head rig','ARMATURE');mod.object=rig
  rows.append({'lod':level,'size':size,'material':mat.name,'newMaps':4,'mask':'R=Metallic,G=AO,B=0,A=1-Roughness','bakeChannels':5})
 finally:
  for other,visible in hidden:other.hide_render=visible
  obj.hide_render=level!=0;obj.hide_set(level!=0)
 bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_BAKED_EQUIPMENT '+json.dumps({'lods':rows,'newMaps':12,'actualBlenderBakes':True,'reloadedBeforePacking':True,'visualAccepted':False}))
