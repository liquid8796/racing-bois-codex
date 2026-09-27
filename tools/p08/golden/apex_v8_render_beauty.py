import bpy
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
scene.cycles.device='CPU';scene.cycles.samples=14
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1100;scene.render.resolution_y=790;scene.render.resolution_percentage=100
camera.data.type='PERSP';camera.data.lens=68;camera.data.clip_end=10000
camera.location=(3.6,3.3,1.42)
camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/v8/apex-beauty-04.png'
bpy.ops.render.render(write_still=True)
print('APEX_V8_VIEW '+scene.render.filepath)
