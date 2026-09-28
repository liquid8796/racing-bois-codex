"""Read-only editable R6 geometry observations and exact unchanged-component comparison to R5."""
import bpy
import bmesh
import json
from mathutils.bvhtree import BVHTree

ROOT = 'D:/Project/Unity/racing-bois/'
SOURCE = ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable04.blend'
assert bpy.data.filepath.replace('\\', '/') == SOURCE
root = bpy.data.objects['RB_Golden_Apex_r6']
prefixes = ['R4 formed main fairing', 'R3 Recessed black intake return', 'R3 Intake plenum shadow',
            'R3 Recessed intake grille', 'R3 Fairing flush bolt', 'R3 Fairing bolt recess',
            'R3 Lower diagonal plenum', 'R3 Lower diagonal black cavity wall', 'R6 recessed front cooling return']

def signature(obj):
    return (tuple(tuple(row) for row in obj.matrix_world), tuple(tuple(v.co) for v in obj.data.vertices),
            tuple(tuple(p.vertices) for p in obj.data.polygons), tuple(m.name for m in obj.data.materials),
            tuple(tuple(tuple(value.uv) for value in layer.data) for layer in obj.data.uv_layers))

untouched = {obj.name: signature(obj) for obj in root.children_recursive if obj.type == 'MESH' and not any(obj.name.startswith(p) for p in prefixes)}
wheel_positions = [tuple(bpy.data.objects['RB_Golden_Apex_r6_Wheel_' + side].matrix_world.translation) for side in ['Front', 'Rear']]
rows = []; points = []; failures = []
for obj in root.children_recursive:
    if obj.type != 'MESH': continue
    data = obj.data; data.calc_loop_triangles(); points.extend(obj.matrix_world @ v.co for v in data.vertices)
    if not any(obj.name.startswith(p) for p in prefixes): continue
    bm = bmesh.new(); bm.from_mesh(data); nonmanifold = sum(not edge.is_manifold for edge in bm.edges); bm.free()
    uv = data.uv_layers.active; tiny = 0; bad_uv = 0; minimum = 1
    for triangle in data.loop_triangles:
        q = [obj.matrix_world @ data.vertices[index].co for index in triangle.vertices]
        cross = (q[1] - q[0]).cross(q[2] - q[0]).length_squared; minimum = min(minimum, cross)
        if cross <= 1e-16: tiny += 1
        p = [uv.data[index].uv for index in triangle.loops]
        if abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5 < 1e-12: bad_uv += 1
    row = {'name': obj.name, 'triangles': len(data.loop_triangles), 'nonManifoldEdges': nonmanifold,
           'unityDegenerateTriangles': tiny, 'zeroAreaUVTriangles': bad_uv, 'minimumCrossSq': minimum}
    rows.append(row)
    if nonmanifold or tiny or bad_uv: failures.append(row)

def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True, epsilon=.000001)

belly_tree = tree(bpy.data.objects['R5 cleared compound belly shell'])
pair_rows = []
for obj in root.children_recursive:
    if obj.type == 'MESH' and any(obj.name.startswith(p) for p in ['R4 formed main fairing', 'R3 Recessed black intake return', 'R3 Lower diagonal', 'R6 recessed front cooling return']):
        pair_rows.append({'component': obj.name, 'bellyTrianglePairs': len(tree(obj).overlap(belly_tree))})
bounds = {'min': [min(p[i] for p in points) for i in range(3)], 'max': [max(p[i] for p in points) for i in range(3)]}

# All editable geometry is already saved. Only our review-camera state is reset
# by these read-only source reloads; no prior-session unsaved work is replaced.
bpy.ops.wm.open_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R5/RB_Golden_Apex_r5_editable01.blend', load_ui=False, use_scripts=False)
bpy.context.view_layer.update()
changed_unowned = [name for name, data in untouched.items() if bpy.data.objects.get(name) is None or signature(bpy.data.objects[name]) != data]
original_wheels = [tuple(bpy.data.objects['RB_Golden_Apex_r5_Wheel_' + side].matrix_world.translation) for side in ['Front', 'Rear']]
bpy.ops.wm.open_mainfile(filepath=SOURCE, load_ui=False, use_scripts=False)
print('R6_AUDIT=' + json.dumps({'source': SOURCE, 'changedSystemMeshes': rows, 'structuralFailures': failures,
    'bellyPairs': pair_rows, 'untouchedMeshesCompared': len(untouched), 'changedUntouchedMeshes': changed_unowned,
    'wheelTransformsUnchanged': wheel_positions == original_wheels, 'boundsBlender': bounds,
    'visualAccepted': False, 'scope': 'Editable source only; no LOD assembly, FBX, Unity import or whole-bike intersection claim.'}))
