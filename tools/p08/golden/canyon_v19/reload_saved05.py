"""Reload the owned saved05 file before independent geometry verification."""
import bpy,json
source='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V19/RB_Golden_Canyon_V19_05.blend'
if bpy.data.filepath.replace('\\','/')!=source:
    raise RuntimeError('Unexpected open source; preserve it.')
bpy.ops.wm.open_mainfile(filepath=source)
print('CANYON_V19_RELOAD05 '+json.dumps({'loadedFromDisk':bpy.data.filepath,'sourceSaved':False}))
