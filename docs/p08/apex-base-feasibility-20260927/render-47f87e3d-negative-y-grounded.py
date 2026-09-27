import bpy
import json
from mathutils import Vector
scene=bpy.data.scenes['Inspection_47f87e3d']
bpy.context.window.scene=scene
scene.camera.location=(0, -4, 0.65)
scene.camera.rotation_euler=(Vector((0,0,.55))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/apex-base-feasibility-20260927/renders/47f87e3d-negative-y-grounded.png'
bpy.ops.render.render(write_still=True)
print(json.dumps({'scene':scene.name,'view':'negative-y','camera':list(scene.camera.location),'render':scene.render.filepath,'threads':scene.render.threads,'device':scene.cycles.device}))
