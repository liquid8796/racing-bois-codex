"""Actual local render of the frozen composition plus cap-UV candidate."""
import bpy, json

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_05.blend'):
    raise RuntimeError('Expected separate V17 candidate05 source.')
scene = bpy.context.scene
if scene.render.filepath != 'D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v17/candidate05-gameplay.png':
    raise RuntimeError('Unexpected candidate output path.')
bpy.ops.render.render(write_still=True)
print('CANYON_V17_RENDER05 '+json.dumps({'source': bpy.data.filepath, 'image': scene.render.filepath,
      'resolution': [scene.render.resolution_x, scene.render.resolution_y], 'visualAccepted': False,
      'scope': 'Actual local Blender render; not Unity/native acceptance or a production export.'}))
