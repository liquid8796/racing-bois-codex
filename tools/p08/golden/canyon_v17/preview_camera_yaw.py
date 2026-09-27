"""Temporary camera-only composition diagnostic; preserves candidate04 source."""
import bpy, json, math
from mathutils import Vector
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_04.blend'):
    raise RuntimeError('Expected frozen candidate04.')
scene = bpy.context.scene
camera = scene.camera
original_rotation = camera.rotation_euler.copy()
original = (scene.render.resolution_percentage, scene.cycles.samples, scene.render.filepath)
try:
    yaw = math.radians(3)
    pitch = math.radians(1.5)
    direction = Vector((math.sin(yaw)*math.cos(pitch), math.cos(yaw)*math.cos(pitch), -math.sin(pitch)))
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_percentage = 50
    scene.cycles.samples = 12
    scene.render.filepath = 'D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v17/candidate04-yaw3-preview.png'
    bpy.ops.render.render(write_still=True)
finally:
    camera.rotation_euler = original_rotation
    scene.render.resolution_percentage, scene.cycles.samples, scene.render.filepath = original
print('CANYON_V17_YAW_PREVIEW '+json.dumps({'source': bpy.data.filepath, 'yawBlenderXYDegrees': 3,
      'downPitchDegrees': 1.5, 'percentage': 50, 'samples': 12, 'sourceCameraAndSettingsRestored': True,
      'sourceSaved': False, 'visualAccepted': False}))
