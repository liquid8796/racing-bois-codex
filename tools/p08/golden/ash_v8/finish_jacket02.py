import bpy,json
SOURCE='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket01.blend'
DESTINATION='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket02.blend'
if bpy.data.filepath.replace('\\','/')!=SOURCE or bpy.context.scene.get('ash_v8_jacket02_authored'):
    raise RuntimeError('Unmodified owned Jacket01 session required')
if bpy.context.preferences.filepaths.use_scripts_auto_execute:raise RuntimeError('Auto-execute must remain disabled')
changes=[];copies={}
for original_name in ['AshV4_TailoredLeather_Baked','AshV4_LeatherDetails_Baked','AshV2_OchreThread_Baked']:
    first=bpy.data.materials['AshV8_'+original_name+'_JacketStudy'];material=first.copy();material.name='AshV8_'+original_name+'_WornLeather02'
    nodes=material.node_tree.nodes;links=material.node_tree.links;shader=next(node for node in nodes if node.type=='BSDF_PRINCIPLED')
    shader.inputs['Coat Weight'].default_value=0
    shader.inputs['Specular IOR Level'].default_value=.28
    grain=original_name!='AshV2_OchreThread_Baked'
    if grain:
        for node in nodes:
            if node.type=='BUMP':node.inputs['Strength'].default_value=.33;node.inputs['Distance'].default_value=.0008
            if node.type=='TEX_NOISE':node.inputs['Scale'].default_value=480;node.inputs['Detail'].default_value=3
        coords=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.name='AshV8_WearVariation'
        noise.inputs['Scale'].default_value=26;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
        links.new(coords.outputs['Object'],noise.inputs['Vector'])
        color_link=next(link for link in links if link.to_socket==shader.inputs['Base Color']);source=color_link.from_socket;links.remove(color_link)
        ramp=nodes.new('ShaderNodeValToRGB');ramp.name='AshV8_SubtleWornBrownVariation'
        ramp.color_ramp.elements[0].position=.20;ramp.color_ramp.elements[0].color=(.66,.59,.51,1)
        ramp.color_ramp.elements[1].position=.80;ramp.color_ramp.elements[1].color=(1.14,1.06,.93,1)
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
        links.new(noise.outputs['Fac'],ramp.inputs['Fac']);links.new(source,mix.inputs[1]);links.new(ramp.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],shader.inputs['Base Color'])
        for link in list(links):
            if link.to_socket==shader.inputs['Roughness']:links.remove(link)
        rough=nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1
        rough.inputs['To Min'].default_value=.58;rough.inputs['To Max'].default_value=.72
        links.new(noise.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs['Result'],shader.inputs['Roughness'])
    else:
        for link in list(links):
            if link.to_socket==shader.inputs['Roughness']:links.remove(link)
        shader.inputs['Roughness'].default_value=.72
    copies[first.name]=material;changes.append(dict(fromMaterial=first.name,toMaterial=material.name,coat=0,specularIorLevel=.28,
        roughnessRange=[.58,.72] if grain else [.72,.72],microBumpDistanceMetres=.0008 if grain else 0))
for level in range(3):
    mesh=bpy.data.objects['AshV7_L'+str(level)+'_Skin'].data
    for index,material in enumerate(mesh.materials):
        if material.name in copies:mesh.materials[index]=copies[material.name]
bpy.context.scene['ash_v8_jacket02_authored']=True
bpy.ops.wm.save_as_mainfile(filepath=DESTINATION,compress=True)
print('ASH_V8_JACKET02 '+json.dumps(dict(source=SOURCE,candidate=DESTINATION,materials=changes,geometryChanged=False,rigOrActionsChanged=False,
    originalTexturesRewritten=False,proceduralFinishNeedsBakeBeforeRuntime=True,visualAccepted=False)))
