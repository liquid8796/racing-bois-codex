import bpy
import json

ROOT = 'D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/Textures/'
names = ['Apex_Pearl', 'Apex_Graphite', 'Apex_Machined', 'Apex_Rubber', 'Apex_Titanium',
         'Apex_Glass', 'Apex_Lamp', 'Apex_Lens', 'Apex_RedLamp']
records = []
for name in names:
    material = bpy.data.materials[name]
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    shader.inputs['IOR'].default_value = 1.46
    textures = {}
    fields = [('BaseColor', 'sRGB'), ('Normal', 'Non-Color'), ('MetallicSmoothness', 'Non-Color'), ('Roughness', 'Non-Color')]
    if name in ['Apex_Lamp', 'Apex_RedLamp']:
        fields.append(('Emission', 'sRGB'))
    for field, color_space in fields:
        image = bpy.data.images.load(ROOT + name + '_' + field + '.png', check_existing=False)
        image.colorspace_settings.name = color_space
        image.reload()
        image.pack()
        node = nodes.new('ShaderNodeTexImage')
        node.image = image
        node.label = field + ' / ' + color_space
        textures[field] = node
    links.new(textures['BaseColor'].outputs['Color'], shader.inputs['Base Color'])
    links.new(textures['Roughness'].outputs['Color'], shader.inputs['Roughness'])
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(textures['MetallicSmoothness'].outputs['Color'], channels.inputs['Color'])
    links.new(channels.outputs['Red'], shader.inputs['Metallic'])
    normal = nodes.new('ShaderNodeNormalMap')
    normal.inputs['Strength'].default_value = .25
    links.new(textures['Normal'].outputs['Color'], normal.inputs['Color'])
    links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    if name == 'Apex_Pearl':
        shader.inputs['Coat Weight'].default_value = .28
        shader.inputs['Coat Roughness'].default_value = .16
    if name in ['Apex_Glass', 'Apex_Lens']:
        shader.inputs['Transmission Weight'].default_value = .95 if name == 'Apex_Glass' else 1
        shader.inputs['Specular IOR Level'].default_value = .5 if name == 'Apex_Glass' else .25
    if 'Emission' in textures:
        links.new(textures['Emission'].outputs['Color'], shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value = 2.0 if name == 'Apex_Lamp' else 1.5
    material['baseColorStorage'] = 'sRGB encoded from declared linear reflectance'
    material['scalarStorage'] = 'linear data'
    records.append({'name': name, 'loadedFreshAndReloaded': True, 'packed': True, 'maps': len(fields)})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_MATERIALS=' + json.dumps({'materials': records, 'visualAccepted': False, 'r2FilesChanged': False}))
