"""Camera-clip-only follow-up to frozen candidate04, with geometry unchanged."""
import bpy, json

ROOT = 'D:/Project/Unity/racing-bois/'
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_04.blend'):
    raise RuntimeError('Expected frozen candidate04 in the owned session.')
scene = bpy.context.scene
camera = scene.camera
before = {'clipStart': camera.data.clip_start, 'clipEnd': camera.data.clip_end,
          'position': list(camera.location), 'rotation': list(camera.rotation_euler),
          'lens': camera.data.lens, 'sensorWidth': camera.data.sensor_width}
if camera.data.clip_end != 1000:
    raise RuntimeError('Inherited camera clipping diagnosis no longer matches.')
camera.data.clip_end = 2500
scene.render.filepath = ROOT+'docs/p08/golden/canyon/v17/candidate05-gameplay.png'
scene['v17_scope'] = 'Unaccepted candidate05: only camera far clip1000→2500 from04; all geometry/materials/UV/lighting unchanged.'
destination = ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.blend'
bpy.ops.wm.save_as_mainfile(filepath=destination, check_existing=False)
print('CANYON_V17_CLIP05 '+json.dumps({'source': destination, 'beforeCamera': before,
      'afterClipStart': camera.data.clip_start, 'afterClipEnd': camera.data.clip_end,
      'geometryMaterialsUvLightingUnchanged': True, 'visualAccepted': False, 'exportedToAssets': False}))
