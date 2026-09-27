import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
scene.cycles.device='CPU';scene.cycles.samples=24;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=980;scene.render.resolution_percentage=100
camera.data.type='PERSP';camera.data.lens=68;camera.data.clip_end=10000
camera.location=(3.6,3.3,1.42);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
back=bpy.data.objects.get('Apex V8 studio cyclorama')
if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/beauty-10.png'
bpy.ops.render.render(write_still=True)
print('APEX_R3_RENDER '+json.dumps({'file':scene.render.filepath,'visualAccepted':False,'CPUThreads':4}))

