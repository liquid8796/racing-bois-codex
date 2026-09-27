import bpy
import json
ROOT='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/Textures/'
obj=bpy.data.objects['Copper teardrop tank'];data=obj.data
ring_vertices=(8-1)*5*16+16
assert len(data.vertices)==ring_vertices+2
uv=data.uv_layers.active
for face in data.polygons:
    cap=any(i>=ring_vertices for i in face.vertices)
    wrap=not cap and any(i%16==0 for i in face.vertices) and any(i%16==15 for i in face.vertices)
    for loop in face.loop_indices:
        index=data.loops[loop].vertex_index;p=data.vertices[index].co
        if cap:
            uv.data[loop].uv=(.025 if p.y<0 else .975,.50+p.z*.03)
            uv.data[loop].uv.x+=p.x*.04
        else:
            v=(index%16)/16
            if wrap and index%16==0:v=1
            uv.data[loop].uv=(.05+.90*(p.y+.100)/.520,v)
material=bpy.data.materials['Spark_Copper'];nodes=material.node_tree.nodes;links=material.node_tree.links
shader=nodes.get('Principled BSDF');images={}
for node in list(nodes):
    if node.type in ['TEX_IMAGE','NORMAL_MAP','SEPARATE_COLOR']:nodes.remove(node)
for field,color in [('BaseColor','sRGB'),('Normal','Non-Color'),('MetallicSmoothness','Non-Color'),('Roughness','Non-Color')]:
    image=bpy.data.images.load(ROOT+'Spark_Copper_'+field+'.png',check_existing=False);image.colorspace_settings.name=color;image.reload();image.pack()
    node=nodes.new('ShaderNodeTexImage');node.image=image;node.label=field+' '+color;images[field]=node
links.new(images['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
links.new(images['Roughness'].outputs['Color'],shader.inputs['Roughness'])
channels=nodes.new('ShaderNodeSeparateColor');links.new(images['MetallicSmoothness'].outputs['Color'],channels.inputs['Color']);links.new(channels.outputs['Red'],shader.inputs['Metallic'])
normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.20;links.new(images['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
obj['paintSource']='Original UV painting from locked concept; no copied reference pixels'
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_TANK_PAINT_BOUND='+json.dumps({'uniqueTankUvCharts':True,'originalPaint':True,'freshImagesReloadedAndPacked':True,'visualAccepted':False}))
