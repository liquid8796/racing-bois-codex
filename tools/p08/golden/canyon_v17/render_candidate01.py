"""Render the frozen V17 local source without exporting production content."""
import bpy, json

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_01.blend'):
    raise RuntimeError('Expected the separate V17 candidate01 source.')
scene = bpy.context.scene
if scene.render.filepath != 'D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v17/candidate01-gameplay.png':
    raise RuntimeError('Unexpected candidate output path.')
bpy.ops.render.render(write_still=True)
print('CANYON_V17_RENDER01 '+json.dumps({'source': bpy.data.filepath, 'image': scene.render.filepath,
      'resolution': [scene.render.resolution_x, scene.render.resolution_y], 'visualAccepted': False,
      'scope': 'Actual local Blender render; not Unity/native acceptance or a production export.'}))
