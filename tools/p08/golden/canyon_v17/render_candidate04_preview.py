"""Low-sample actual Blender composition preview; preserves frozen source settings."""
import bpy, json
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_04.blend'):
    raise RuntimeError('Expected separate V17 candidate04 source.')
scene = bpy.context.scene
old = (scene.render.resolution_percentage, scene.cycles.samples, scene.render.filepath)
try:
    scene.render.resolution_percentage = 50
    scene.cycles.samples = 12
    scene.render.filepath = 'D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v17/candidate04-preview.png'
    bpy.ops.render.render(write_still=True)
finally:
    scene.render.resolution_percentage, scene.cycles.samples, scene.render.filepath = old
print('CANYON_V17_PREVIEW04 '+json.dumps({'source': bpy.data.filepath, 'percentage': 50, 'samples': 12,
      'sourceSettingsRestored': True, 'sourceSaved': False, 'visualAccepted': False}))
