CHANNEL='Normal'
"""Bake one physical material property through Blender; CHANNEL is a header literal."""
import bpy,json
scene=bpy.context.scene;obj=bpy.data.objects['AshV2_L0_Skin']
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12;scene.render.bake.normal_space='TANGENT'
materials=list(obj.data.materials);restore=[];images=[]
for mat in materials:
    name=mat['source_name'];size=int(mat['texture_size']);nodes=mat.node_tree.nodes;links=mat.node_tree.links
    image=bpy.data.images.new(name+'_'+CHANNEL,width=size,height=size,alpha=True,float_buffer=False)
    image.colorspace_settings.name='sRGB' if CHANNEL=='BaseColor' else 'Non-Color'
    image.generated_color=(.5,.5,1,1) if CHANNEL=='Normal' else (0,0,0,1)
    image.filepath_raw='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/BakeIntermediate/'+name+'_'+CHANNEL+'.png';image.file_format='PNG'
    target=nodes.new('ShaderNodeTexImage');target.name='RB_BakeTarget_'+CHANNEL;target.image=image
    for node in nodes:node.select=False
    target.select=True;nodes.active=target;images.append(image)
    if CHANNEL!='Normal':
        output=nodes.get('Material Output');original=output.inputs['Surface'].links[0].from_socket
        shader=nodes.get('Principled BSDF');field={'BaseColor':'Base Color','Metallic':'Metallic','Roughness':'Roughness','Alpha':'Alpha'}[CHANNEL]
        socket=shader.inputs[field];emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
        if socket.is_linked:links.new(socket.links[0].from_socket,emission.inputs['Color'])
        else:
            value=socket.default_value
            emission.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else tuple(value)
        links.new(emission.outputs[0],output.inputs['Surface']);restore.append((mat,output,original,emission))
try:
    bpy.ops.object.bake(type='NORMAL' if CHANNEL=='Normal' else 'EMIT',use_clear=True)
    for image in images:image.save()
finally:
    for mat,output,original,emission in restore:
        mat.node_tree.links.new(original,output.inputs['Surface']);mat.node_tree.nodes.remove(emission)
print('ASH_BAKED_CHANNEL '+json.dumps({'channel':CHANNEL,'files':[image.filepath_raw for image in images],'source':'actual Blender bake from current runtime LOD0'}))
