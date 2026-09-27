"""Bounded V17 composition candidate from frozen V16; execute via direct safe MCP9877."""
import bpy, math, json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_02.blend'):
    raise RuntimeError('Expected frozen V17 candidate02 input; do not apply transforms twice or modify another scene.')
scene = bpy.context.scene
root = bpy.data.objects.get('RB_Golden_Canyon')
if root is None:
    raise RuntimeError('Canyon root absent.')
allowed = ['Bend_07', 'DistantGround'] + ['Opposite_%02d' % i for i in range(20, 33)] + ['Far_%02d' % i for i in range(33, 45)]
before = []
changes = []

def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])

for module in allowed:
    for level in range(3):
        name = 'Canyon_L%d_%s' % (level, module)
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH':
            raise RuntimeError('Missing exact source module: ' + name)
        obj.data.calc_loop_triangles()
        before.append({'name': name, 'bounds': bounds(obj), 'triangles': len(obj.data.loop_triangles),
                       'materials': [m.name for m in obj.data.materials]})

def update_mesh(obj, kind, parameters):
    if obj.data.users != 1:
        obj.data = obj.data.copy()
    world = obj.matrix_world.copy()
    inverse = world.inverted()
    for vertex in obj.data.vertices:
        p = world @ vertex.co
        if kind == 'affine':
            cx, cy, ox, oy, sx, sy, sz, bottom, low_z = parameters
            result = (cx+(p.x-ox)*sx, cy+(p.y-oy)*sy, bottom+(p.z-low_z)*sz)
        else:
            raise RuntimeError('Unknown bounded mesh transform.')
        vertex.co = inverse @ Vector(result)
    obj.data.update()

def reshape(module, cx, cy, width, depth, bottom, top):
    lo, hi = bounds(bpy.data.objects['Canyon_L0_' + module])
    ox, oy = (lo[0] + hi[0]) * .5, (lo[1] + hi[1]) * .5
    sx, sy, sz = width/(hi[0]-lo[0]), depth/(hi[1]-lo[1]), (top-bottom)/(hi[2]-lo[2])
    for level in range(3):
        obj = bpy.data.objects['Canyon_L%d_%s' % (level, module)]
        update_mesh(obj, 'affine', (cx, cy, ox, oy, sx, sy, sz, bottom, lo[2]))
    changes.append({'module': module, 'kind': 'shared-affine-all-LODs', 'targetCenterXY': [cx, cy],
                    'targetWidthDepth': [width, depth], 'targetBottomTop': [bottom, top], 'scale': [sx, sy, sz]})

# Keep candidate02 intact. A receding left chain and right bank frame an open basin.
lo, hi = bounds(bpy.data.objects['Canyon_L0_Bend_07'])
reshape('Bend_07', (lo[0]+hi[0])*.5, (lo[1]+hi[1])*.5,
        hi[0]-lo[0], hi[1]-lo[1], lo[2]-18, hi[2]-18)
for i in range(13):
    reshape('Opposite_%02d' % (20+i), 180+i*28+12*math.sin(i*.6), 200+i*85,
            75+8*math.sin(i*.8), 135, -100+4*math.sin(i*.9), -12+i*6+4*math.sin(i*.7))
for i in range(12):
    reshape('Far_%02d' % (33+i), -120+i*25, 260+i*105,
            95+i*3, 185, -100, 270-i*19+9*math.sin(i*.75))

scene.render.filepath = ROOT+'docs/p08/golden/canyon/v17/candidate03-gameplay.png'
scene['v17_scope'] = 'Unaccepted candidate03: receding escarpment and open right basin; cap UV repair retained.'
bpy.context.view_layer.update()
after = []
for row in before:
    obj = bpy.data.objects[row['name']]; obj.data.calc_loop_triangles()
    if len(obj.data.loop_triangles) != row['triangles'] or [m.name for m in obj.data.materials] != row['materials']:
        raise RuntimeError('Unexpected topology/material change: '+obj.name)
    after.append({'name': obj.name, 'bounds': bounds(obj), 'triangles': len(obj.data.loop_triangles)})
destination = ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_03.blend'
bpy.ops.wm.save_as_mainfile(filepath=destination, check_existing=False)
print('CANYON_V17_CANDIDATE03 '+json.dumps({'source': destination, 'before': before, 'after': after, 'changes': changes,
      'camera': {'position': list(scene.camera.location), 'rotation': list(scene.camera.rotation_euler),
      'lens': scene.camera.data.lens, 'sensorWidth': scene.camera.data.sensor_width, 'resolution': [1536, 717]},
      'unchangedFrom02': ['DistantGround', 'all materials', 'all UVs', 'camera and lighting', 'all other geometry'],
      'visualAccepted': False, 'exportedToAssets': False}))
