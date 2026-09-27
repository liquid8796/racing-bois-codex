"""Real V16 Blender comparison render; changes only transient render settings."""
import bpy, json

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V16/RB_Golden_Canyon.blend'):
    raise RuntimeError('Expected immutable V16 source in the owned session.')
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 1536
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.filepath = 'D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v17/v16-comparison-original-camera.png'
bpy.ops.render.render(write_still=True)
print('CANYON_V16_COMPARISON ' + json.dumps({'image': scene.render.filepath, 'sourceNotSaved': bpy.data.filepath,
      'cameraPositionBlender': list(scene.camera.location), 'cameraRotationBlender': list(scene.camera.rotation_euler),
      'lens': scene.camera.data.lens, 'resolution': [1536, 768], 'samples': 24,
      'scope': 'Actual local Blender V16 render at its original camera; no source save or acceptance.'}))
