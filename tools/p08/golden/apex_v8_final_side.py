import bpy,math
from mathutils import Vector
s=bpy.context.scene;c=s.camera
s.cycles.device='CPU';s.cycles.samples=16
s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=1200;s.render.resolution_y=860;s.render.resolution_percentage=100
c.data.type='ORTHO';c.data.lens=68;c.data.ortho_scale=2.52;c.data.clip_end=10000
c.location=(-4, 0, 0.73)
c.rotation_euler=(Vector((0, 0, 0.64))-c.location).to_track_quat('-Z','Y').to_euler()
back=bpy.data.objects.get('Apex V8 studio cyclorama')
if back:back.rotation_euler.z=math.atan2(c.location.x,-c.location.y)
s.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/v8/apex-side-final.png'
bpy.ops.render.render(write_still=True)
print('APEX_V8_FINAL_VIEW '+s.render.filepath)
