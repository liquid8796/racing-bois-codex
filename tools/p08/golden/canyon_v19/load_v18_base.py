"""Separate owned-file load so Blender settles operator context before authoring."""
import bpy,json
root='D:/Project/Unity/racing-bois/'
source=root+'ArtSource/P08/Golden/Canyon/V18/RB_Golden_Canyon_V18_02.blend'
if bpy.data.filepath.replace('\\','/') not in [source,root+'ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_01.blend']:
    raise RuntimeError('Unrelated Blender source is open; preserve it.')
bpy.ops.wm.open_mainfile(filepath=source)
print('CANYON_V19_BASE_LOADED '+json.dumps({'source':bpy.data.filepath,'sourceSaved':False}))
