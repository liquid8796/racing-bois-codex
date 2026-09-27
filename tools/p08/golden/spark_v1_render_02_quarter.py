import bpy,json
from mathutils import Vector
s=bpy.context.scene;c=s.camera;c.location=(3.6, 3.4, 1.62);c.data.type='PERSP';c.data.lens=62;c.data.ortho_scale=2.5;c.rotation_euler=(Vector((0,0,.61))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/spark/v1/02-quarter.png'
bpy.ops.render.render(write_still=True)
print(json.dumps({'path':s.render.filepath,'visualAccepted':False,'stage':'refined silhouette, original tank paint, actual seat ribs and same-side chain; details pending'}))
