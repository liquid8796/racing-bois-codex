"""Bounded V17 composition candidate from frozen V16; execute via direct safe MCP9877."""
import bpy, bmesh, math, json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V16/RB_Golden_Canyon.blend'):
    raise RuntimeError('Expected V16 input; do not apply transforms twice or modify another scene.')
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
        elif kind == 'valley':
            result = valley(p.x, p.y, p.z)
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

# Actual V16 rays identify Bend_07 as the near-right visual obstruction.
# Lower only this one bank module; road, rail and the other bend modules are untouched.
lo, hi = bounds(bpy.data.objects['Canyon_L0_Bend_07'])
reshape('Bend_07', (lo[0]+hi[0])*.5, (lo[1]+hi[1])*.5,
        hi[0]-lo[0], hi[1]-lo[1], lo[2]-15, hi[2]-15)

# A connected, receding opposing bank replaces the alternating isolated islands.
for i in range(13):
    reshape('Opposite_%02d' % (20+i), 90+i*16, 315+i*24+10*math.sin(i*.55),
            63+5*math.sin(i*.8), 78, -64+2*math.sin(i*.9), 9+6*math.sin(i*.63))

# Broad overlapping far escarpments form a continuous skyline. This pass changes
# placement/proportions only; existing scan topology, UVs and materials remain.
for i in range(12):
    reshape('Far_%02d' % (33+i), -360+i*80, 720+i*14+25*math.sin(i*.5),
            155, 125, -58, 104-i*2.4+8*math.sin(i*.7))

def smooth(a, b, x):
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)

def road_center(distance):
    return -18*(1-math.cos(max(0, min(80, distance))*math.pi/160))

def valley(x, forward, old_height):
    channel = 40 + .12*(forward-200) + 10*math.sin(forward/120)
    cross = abs(x-channel)
    floor = -71 + 2.3*math.sin(forward*.024) + 1.4*math.sin(x*.071+forward*.01)
    height = floor + 22*smooth(32, 70, cross) + 21*smooth(80, 120, cross) + 18*smooth(140, 205, cross)
    height += max(0, forward-800)*.035
    # Keep the existing near roadside edge connected to its authored shoulder.
    lateral = x-road_center(forward)
    if forward < 145 and lateral < 48:
        near = -.62*max(0, lateral-4)
        blend = smooth(18, 48, lateral) * (1-smooth(105, 145, forward)) + smooth(105, 145, forward)
        height = near*(1-blend) + height*blend
    # The unobserved left side remains the V16 ground; this is a right-valley pass.
    weight = smooth(0, 8, lateral) * smooth(22, 42, forward)
    return (x, forward, old_height*(1-weight)+height*weight)

for level in range(3):
    update_mesh(bpy.data.objects['Canyon_L%d_DistantGround' % level], 'valley', ())
changes.append({'module': 'DistantGround', 'kind': 'continuous-right-valley-heightfield-all-LODs',
                'nearShoulderConnection': True, 'leftSidePreserved': True})

# Corresponding-view proposal: same eye position and yaw, less downward pitch,
# and the top gameplay-panel aspect. The original V16 camera render is retained.
camera = scene.camera
source_camera = {'position': list(camera.location), 'rotation': list(camera.rotation_euler), 'lens': camera.data.lens,
                 'sensorWidth': camera.data.sensor_width, 'resolution': [scene.render.resolution_x, scene.render.resolution_y]}
camera.location = (1.7, 3, 1.55)
target = Vector((-2, 32, 1.55-math.tan(math.radians(1.5))*math.hypot(3.7, 29)))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 28
camera.data.sensor_width = 36
camera.data.sensor_fit = 'HORIZONTAL'
scene.render.resolution_x = 1536
scene.render.resolution_y = 717
scene.render.resolution_percentage = 100
scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
scene.render.filepath = ROOT+'docs/p08/golden/canyon/v17/candidate01-gameplay.png'
for obj in root.children_recursive:
    if '_L1_' in obj.name or '_L2_' in obj.name:
        obj.hide_render = True; obj.hide_set(True)
    elif '_L0_' in obj.name:
        obj.hide_render = False; obj.hide_set(False)
scene['v17_scope'] = 'Unaccepted right-valley composition candidate only; no production export.'
scene['locked_concept_sha256'] = '83273dae6721d9f2c6f5d6bf4a6f39146322d8efeabc5cec0cb332e5a1cfa610'
scene['v16_source_sha256'] = 'c7681657df4666b13d22a15adbfaa17b42fd7413b8d4294a3cada4eb485cc01c'
bpy.context.view_layer.update()
after = []
for row in before:
    obj = bpy.data.objects[row['name']]; obj.data.calc_loop_triangles()
    if len(obj.data.loop_triangles) != row['triangles'] or [m.name for m in obj.data.materials] != row['materials']:
        raise RuntimeError('Unexpected topology/material change: '+obj.name)
    after.append({'name': obj.name, 'bounds': bounds(obj), 'triangles': len(obj.data.loop_triangles)})
destination = ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_01.blend'
bpy.ops.wm.save_as_mainfile(filepath=destination, check_existing=False)
print('CANYON_V17_CANDIDATE01 '+json.dumps({'source': destination, 'before': before, 'after': after, 'changes': changes,
      'sourceCamera': source_camera, 'candidateCamera': {'position': list(camera.location), 'rotation': list(camera.rotation_euler),
      'targetBlender': list(target), 'lens': camera.data.lens, 'sensorWidth': camera.data.sensor_width, 'resolution': [1536, 717]},
      'changedModules': len(allowed), 'changedMeshObjects': len(after), 'visualAccepted': False, 'exportedToAssets': False}))
