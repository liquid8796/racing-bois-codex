import bpy
import math
import json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
assert bpy.data.objects.get('RB_Golden_Apex_r6') is not None
camera.data.type='ORTHO';camera.data.lens=68;camera.data.ortho_scale=2.5
camera.location=(5, 0, 1.01);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
back=bpy.data.objects.get('Apex V8 studio cyclorama')
if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r6/01-side.png'
bpy.ops.render.render(write_still=True)
print(json.dumps({'render':scene.render.filepath,'reference':'lockedApexv2','baselineView':'R5 matched side','visualAccepted':False}))
