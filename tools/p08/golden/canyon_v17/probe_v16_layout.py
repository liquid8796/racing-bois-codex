"""Read-only module bounds and visible-mass ray probes in the owned V16 scene."""
import bpy, json
from mathutils import Vector

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V16/RB_Golden_Canyon.blend'):
    raise RuntimeError('Expected frozen V16 inspection source.')
scene = bpy.context.scene
camera = scene.camera
root = bpy.data.objects.get('RB_Golden_Canyon')
if root is None or camera is None:
    raise RuntimeError('Missing Canyon root or camera.')
rows = []
for obj in root.children_recursive:
    if obj.type != 'MESH' or '_L0_' not in obj.name:
        continue
    if not any(token in obj.name for token in ['Opposite_', 'Far_', 'LowerLedge_', 'Bend_', 'DistantGround']):
        continue
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    rows.append({'name': obj.name, 'locationBlender': list(obj.location),
                 'boundsMinBlender': [min(p[i] for p in points) for i in range(3)],
                 'boundsMaxBlender': [max(p[i] for p in points) for i in range(3)],
                 'scale': list(obj.scale), 'rotation': list(obj.rotation_euler),
                 'hideRender': obj.hide_render, 'vertices': len(obj.data.vertices)})
corners = camera.data.view_frame(scene=scene)
x0, x1 = min(v.x for v in corners), max(v.x for v in corners)
y0, y1 = min(v.y for v in corners), max(v.y for v in corners)
z = corners[0].z
depsgraph = bpy.context.evaluated_depsgraph_get()
rays = []
for u in [.45, .6, .75, .9]:
    for v in [.2, .35, .5, .65]:
        direction = camera.matrix_world.to_quaternion() @ Vector((x0 + (x1-x0)*u, y1 - (y1-y0)*v, z)).normalized()
        hit, point, normal, face, obj, matrix = scene.ray_cast(depsgraph, camera.matrix_world.translation, direction, distance=2500)
        rays.append({'uvTopLeft': [u, v], 'object': obj.name if hit else None, 'pointBlender': list(point) if hit else None})
print('CANYON_V16_LAYOUT ' + json.dumps({'filepath': bpy.data.filepath, 'camera': {'name': camera.name,
      'location': list(camera.location), 'rotation': list(camera.rotation_euler), 'lens': camera.data.lens,
      'sensorWidth': camera.data.sensor_width, 'resolution': [scene.render.resolution_x, scene.render.resolution_y]},
      'modules': rows, 'rays': rays, 'scope': 'Read-only bounds/raycast evidence, not visual acceptance.'}))
