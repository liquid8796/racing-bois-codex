"""Discard only owned post-audit temporary state by loading its frozen source."""
import bpy, json
expected = 'D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_04.blend'
if bpy.data.filepath.replace('\\', '/') != expected:
    raise RuntimeError('Another file is open; do not replace unrelated work.')
bpy.ops.wm.open_mainfile(filepath=expected)
print('CANYON_V17_RELOADED04 '+json.dumps({'file': bpy.data.filepath, 'dirty': bpy.data.is_dirty,
      'objects': len(bpy.data.objects), 'meshes': len(bpy.data.meshes), 'materials': len(bpy.data.materials),
      'images': len(bpy.data.images), 'sourceSaved': False,
      'scope': 'Reload exact owned frozen04; discard only temporary import audit state.'}))
