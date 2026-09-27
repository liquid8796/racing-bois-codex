import bpy,json
from mathutils import Vector
s=bpy.context.scene;c=s.camera;c.location=(5, 0, 0.61);c.data.type='ORTHO';c.data.lens=88;c.data.ortho_scale=2.38;c.rotation_euler=(Vector((0,0,.61))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1536;s.render.resolution_y=1024;s.render.resolution_percentage=100
s.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/spark/v1/03-side.png'
bpy.ops.render.render(write_still=True)
print(json.dumps({'path':s.render.filepath,'visualAccepted':False,'stage':'complete mechanism and finish candidate; no export yet'}))
