import bpy
import json
from mathutils import Vector
scene=bpy.data.scenes['Inspection_95a107fe']
bpy.context.window.scene=scene
scene.camera.location=(3, -4, 1.7)
scene.camera.rotation_euler=(Vector((0,0,.55))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.view_layers[0].material_override=bpy.data.materials['INSPECTION neutral gray clay']
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/apex-base-feasibility-20260927/renders/95a107fe-clay-front-quarter.png'
try:
 bpy.ops.render.render(write_still=True)
finally:
 scene.view_layers[0].material_override=None
print(json.dumps({'scene':scene.name,'view':'clay front quarter','camera':list(scene.camera.location),'render':scene.render.filepath,'threads':scene.render.threads,'device':scene.cycles.device,'overrideRestored':scene.view_layers[0].material_override is None}))
