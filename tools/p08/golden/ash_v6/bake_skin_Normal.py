CHANNEL='Normal'
"""CHANNEL header selects one real shader-property bake. Writes only ArtSource/V6."""
import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];obj=bpy.data.objects['AshV6_L0_Skin']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):
    value=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];value.hide_render=level!=0
    for key in value.data.shape_keys.key_blocks:key.value=0
bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True
for level in range(3):bpy.data.objects['AshV6_L'+str(level)+'_Equipment'].hide_render=True
floor=bpy.data.objects['AshV2_ReviewFloor'];old_floor=floor.hide_render;floor.hide_render=True
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
obj.data.uv_layers.active_index=0;obj.data.uv_layers[0].active_render=True
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12;scene.render.bake.normal_space='TANGENT'
images=[];restore=[];targets=[]
for mat in obj.data.materials:
    role=mat.get('ash_v6_source_role','');size=int(mat.get('texture_size',512)) if role else 8
    name='AshV6_'+role+'_'+CHANNEL if role else 'AshV6_Dummy_'+mat.name+'_'+CHANNEL
    image=bpy.data.images.new(name,width=size,height=size,alpha=True,float_buffer=False);image.colorspace_settings.name='sRGB' if CHANNEL=='BaseColor' else 'Non-Color'
    image.generated_color=(.5,.5,1,1) if CHANNEL=='Normal' else (0,0,0,1)
    if role:
        image.filepath_raw=ROOT+'ArtSource/P08/Golden/Ash/V6/BakeIntermediate/'+name+'.png';image.file_format='PNG';images.append(image)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;target=nodes.new('ShaderNodeTexImage');target.image=image;target.name='AshV6_BakeTarget_'+CHANNEL
    for node in nodes:node.select=False
    target.select=True;nodes.active=target;targets.append((mat,target,image,role))
    if CHANNEL not in ['Normal','Occlusion']:
        output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');original=output.inputs['Surface'].links[0].from_socket
        bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');field={'BaseColor':'Base Color','Roughness':'Roughness'}[CHANNEL]
        socket=bs.inputs[field];emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
        if socket.is_linked:links.new(socket.links[0].from_socket,emission.inputs['Color'])
        else:
            value=socket.default_value;emission.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else tuple(value)
        links.new(emission.outputs[0],output.inputs['Surface']);restore.append((mat,output,original,emission))
try:
    bpy.ops.object.bake(type='NORMAL' if CHANNEL=='Normal' else 'AO' if CHANNEL=='Occlusion' else 'EMIT',use_clear=True)
    for image in images:image.save()
finally:
    for mat,output,original,emission in restore:mat.node_tree.links.new(original,output.inputs['Surface']);mat.node_tree.nodes.remove(emission)
    for mat,target,image,role in targets:
        mat.node_tree.nodes.remove(target)
        if not role and image.users==0:bpy.data.images.remove(image)
    floor.hide_render=old_floor
print('ASH_V6_BAKE '+json.dumps({'channel':CHANNEL,'actualBlenderBake':True,'files':[i.filepath_raw for i in images],'reusedLegacyMapsUntouched':True}))
