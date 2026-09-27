"""Read-only gameplay-ray ownership, stepping through non-landform fog sheets."""
import bpy, json
from mathutils import Vector

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V16/RB_Golden_Canyon.blend'):
    raise RuntimeError('Expected immutable V16 source loaded in owned session.')
scene = bpy.context.scene
camera = scene.camera
frame = camera.data.view_frame(scene=scene)
x0, x1 = min(p.x for p in frame), max(p.x for p in frame)
y0, y1 = min(p.y for p in frame), max(p.y for p in frame)
depsgraph = bpy.context.evaluated_depsgraph_get()
rows = []
for u in [.45, .6, .75, .9]:
    for v in [.12, .22, .32, .42]:
        direction = (camera.matrix_world.to_quaternion() @ Vector((x0+(x1-x0)*u, y1-(y1-y0)*v, frame[0].z))).normalized()
        origin = camera.matrix_world.translation.copy()
        skipped = []
        final = None
        for step in range(12):
            hit, point, normal, face, obj, matrix = scene.ray_cast(depsgraph, origin, direction, distance=2500)
            if not hit:
                break
            if obj.name.startswith('Canyon_L'):
                final = {'object': obj.name, 'pointBlender': list(point)}
                break
            skipped.append(obj.name)
            origin = point + direction * .01
        rows.append({'uvTopLeft': [u, v], 'hit': final, 'nonLandformSheetsSkipped': skipped})
print('CANYON_V16_OCCLUDERS ' + json.dumps({'rays': rows, 'scope': 'Read-only actual mesh ray ownership; no source or visibility changes.'}))
