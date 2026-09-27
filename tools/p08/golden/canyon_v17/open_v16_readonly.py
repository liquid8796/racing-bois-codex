"""Open the immutable V16 input only in the verified new factory-startup session."""
import bpy, json

expected = {'Cube', 'Camera', 'Light'}
if bpy.data.filepath or {obj.name for obj in bpy.context.scene.objects} != expected:
    raise RuntimeError('Expected the new owned factory-startup scene; do not replace another scene.')
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend')
print('CANYON_V16_LOADED_READONLY ' + json.dumps({
    'filepath': bpy.data.filepath, 'objects': len(bpy.context.scene.objects),
    'scope': 'Loaded existing V16 bytes in an isolated session; source file was not saved or edited.'
}))
