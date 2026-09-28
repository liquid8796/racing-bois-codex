"""R6 study01: sculpt only the R5 fairing system; preserve every prior file and mechanical part."""
import bpy
import bmesh
import math
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = 'D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\', '/').endswith('/Apex/R5/RB_Golden_Apex_r5_editable01.blend')
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
root = bpy.data.objects['RB_Golden_Apex_r5']
prefixes = ['R4 formed main fairing', 'R3 Recessed black intake return', 'R3 Intake plenum shadow',
            'R3 Recessed intake grille', 'R3 Fairing flush bolt', 'R3 Fairing bolt recess',
            'R3 Lower diagonal plenum', 'R3 Lower diagonal black cavity wall']
selected = [o for o in root.children_recursive if o.type == 'MESH' and any(o.name.startswith(p) for p in prefixes)]
unaffected = [o for o in root.children_recursive if o.type == 'MESH' and o not in selected]

def signature(obj):
    return (tuple(tuple(row) for row in obj.matrix_world), tuple(tuple(v.co) for v in obj.data.vertices),
            tuple(tuple(p.vertices) for p in obj.data.polygons), tuple(m.name for m in obj.data.materials),
            tuple(tuple(tuple(value.uv) for value in layer.data) for layer in obj.data.uv_layers))

before = {o.name: signature(o) for o in unaffected}

def old_skin(z, y):
    width = .155 + .123 * math.exp(-((z - .71) / .285) ** 2 - ((y - .40) / .36) ** 2)
    width -= .055 * math.exp(-((z - .59) / .18) ** 2 - ((y - .095) / .19) ** 2)
    width -= .069 * max(0, min(1, (y - .54) / .25))
    width -= .031 * max(0, min(1, (.40 - z) / .20))
    return width

def new_skin(z, y):
    # A broad lower plane turns at the raised shoulder instead of reading as a
    # uniformly smooth hanging sheet. Ends still meet the untouched cowl.
    h = z - .10 * (y - .30)
    profile = [(.18, .172), (.32, .203), (.58, .260), (.74, .294), (.82, .258), (.92, .169)]
    width = profile[0][1]
    for a, b in zip(profile, profile[1:]):
        if a[0] <= h <= b[0]:
            width = a[1] + (b[1] - a[1]) * (h - a[0]) / (b[0] - a[0])
            break
        if h > b[0]: width = b[1]
    width -= .070 * math.exp(-((y - .055) / .15) ** 2 - ((z - .62) / .24) ** 2)
    width -= .070 * max(0, min(1, (y - .54) / .25))
    edge = max(0, min(1, (.918 - z) / .065)) * max(0, min(1, (.765 - y) / .11))
    return old_skin(z, y) + max(0, width - old_skin(z, y)) * edge

rows = []
for obj in selected:
    world = obj.matrix_world.copy(); inverse = world.inverted()
    if obj.name.startswith('R4 formed main fairing'):
        # Explicit crease/seam topology avoids a material edge wandering across
        # the existing triangles. Retain both sides of each closed shell.
        bm = bmesh.new(); bm.from_mesh(obj.data)
        for normal, height in [(Vector((0, -.10, 1)), .71), (Vector((0, -.10, 1)), .55), (Vector((0, .30, 1)), .43)]:
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=.000001,
                plane_co=inverse @ Vector((0, 0, height)), plane_no=world.to_3x3().transposed() @ normal,
                clear_outer=False, clear_inner=False)
        bm.to_mesh(obj.data); bm.free()
    largest = 0
    for vertex in obj.data.vertices:
        point = world @ vertex.co; side = 1 if point.x > 0 else -1
        delta = new_skin(point.z, point.y) - old_skin(point.z, point.y)
        point.x += side * delta; vertex.co = inverse @ point; largest = max(largest, delta)
    obj.data.update()
    if obj.name.startswith('R4 formed main fairing'):
        graphite = next(i for i, material in enumerate(obj.data.materials) if material.name == 'Apex_Graphite')
        bm = bmesh.new(); bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000001)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.000001)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        for face in bm.faces:
            center = world @ face.calc_center_median()
            if center.z + .30 * center.y < .43: face.material_index = graphite
        for edge in bm.edges:
            points = [world @ vertex.co for vertex in edge.verts]
            at_shoulder = all(abs(point.z - .10 * point.y - .71) < .000004 for point in points)
            at_lower = all(abs(point.z - .10 * point.y - .55) < .000004 for point in points)
            if at_shoulder or at_lower: edge.smooth = False
        nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
        assert nonmanifold == 0, obj.name + ' shell closure failed'
        bm.to_mesh(obj.data); bm.free(); obj.data.update()
        obj.data.normals_split_custom_set([(0, 0, 0)] * len(obj.data.loops))
    rows.append({'name': obj.name, 'maximumOutwardChangeMetres': largest, 'vertices': len(obj.data.vertices)})

for obj in unaffected: assert signature(obj) == before[obj.name], 'Unowned component changed: ' + obj.name
root.name = 'RB_Golden_Apex_r6'
for obj in root.children:
    if obj.name == 'RB_Golden_Apex_r5_Wheel_Front': obj.name = 'RB_Golden_Apex_r6_Wheel_Front'
    elif obj.name == 'RB_Golden_Apex_r5_Wheel_Rear': obj.name = 'RB_Golden_Apex_r6_Wheel_Rear'
root['referenceConceptSha256'] = 'f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819'
root['visualAccepted'] = False
root['r6Change'] = 'Study01: fairing shoulder/lower-plane volume and graphite seam only; R5 belly/mechanics unchanged'
bpy.context.view_layer.update()

def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True, epsilon=.000001)

belly = bpy.data.objects['R5 cleared compound belly shell']; belly_tree = tree(belly)
pairs = [{'component': obj.name, 'trianglePairs': len(tree(obj).overlap(belly_tree))} for obj in selected
         if obj.name.startswith('R4 formed main fairing') or obj.name.startswith('R3 Lower diagonal') or obj.name.startswith('R3 Recessed black intake return')]
assert all(row['trianglePairs'] == 0 for row in pairs), 'R5 repaired belly clearance regressed'
scene = bpy.context.scene; scene.cycles.device = 'CPU'; scene.render.threads_mode = 'FIXED'; scene.render.threads = 4; scene.cycles.samples = 24
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable01.blend')
print('R6_STUDY01=' + json.dumps({'changed': rows, 'unaffectedMeshComponentsExact': len(unaffected), 'bellyIntersections': pairs, 'saved': bpy.data.filepath, 'visualAccepted': False}))
