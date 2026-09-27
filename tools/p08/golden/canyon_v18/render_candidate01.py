"""Actual render of the saved Far33-only experiment with the frozen05 camera/light."""
import bpy,json
if not bpy.data.filepath.replace('\\','/').endswith('/Canyon/V18/RB_Golden_Canyon_V18_01.blend'):
    raise RuntimeError('Expected separate V18 candidate01 source.')
scene=bpy.context.scene
if scene.render.filepath!='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v18/candidate01-gameplay.png':
    raise RuntimeError('Unexpected V18 render path.')
bpy.ops.render.render(write_still=True)
print('CANYON_V18_RENDER01 '+json.dumps({'source':bpy.data.filepath,'image':scene.render.filepath,
    'resolution':[scene.render.resolution_x,scene.render.resolution_y],'visualAccepted':False,
    'scope':'Actual Far33-only Blender render; frozen05 camera/lighting, no Assets export or Unity acceptance.'}))
