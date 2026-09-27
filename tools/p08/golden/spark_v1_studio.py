import bpy
import json
from mathutils import Vector
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Spark neutral studio world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.35,.35,.35,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
scene.world = world
material = bpy.data.materials.new('Spark inspection floor only')
material.use_nodes = True
shader = material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.18,.17,.155,1)
shader.inputs['Roughness'].default_value = .78
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.004))
obj=bpy.context.object;obj.name='Spark inspection floor';obj.data.materials.append(material)
for name,pos,power,size in [('Key',(3.3,2.1,4.2),620,3.5),('Fill',(-3.0,.5,2.5),370,4.0),('Rear',(1.0,-3.5,3.3),520,3.0)]:
    data=bpy.data.lights.new('Spark studio '+name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new('Spark studio '+name,data);scene.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((0,0,.60))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Spark inspection camera');data.lens=62
camera=bpy.data.objects.new('Spark inspection camera',data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=(3.6,3.4,1.62);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print(json.dumps({'engine':'CYCLES','device':'CPU','threads':4,'baked':False,'exported':False}))
