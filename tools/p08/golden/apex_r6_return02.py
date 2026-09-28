"""R6 study02: recessed closed front-edge returns on the fairings; no belly or mechanical edits."""
import bpy
import bmesh
import math
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = 'D:/Project/Unity/racing-bois/'
root = bpy.data.objects['RB_Golden_Apex_r6']
assert bpy.data.filepath.replace('\\', '/').endswith('/Apex/R6/RB_Golden_Apex_r6_editable01.blend')
assert bpy.data.objects.get('R6 recessed front cooling return 1') is None

def old_skin(z, y):
    width = .155 + .123 * math.exp(-((z - .71) / .285) ** 2 - ((y - .40) / .36) ** 2)
    width -= .055 * math.exp(-((z - .59) / .18) ** 2 - ((y - .095) / .19) ** 2)
    width -= .069 * max(0, min(1, (y - .54) / .25))
    width -= .031 * max(0, min(1, (.40 - z) / .20))
    return width

def new_skin(z, y):
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

trace = [( .474, .201), (.488, .38), (.503, .571), (.607, .682), (.765, .839)]
dense = []
for index in range(len(trace) - 1):
    a, b = Vector(trace[index]), Vector(trace[index + 1])
    for i in range(8): dense.append(a.lerp(b, i / 8))
dense.append(Vector(trace[-1]))
rows = []
for side in [-1, 1]:
    vertices = []; faces = []; across = 5; count = len(dense) * across
    for layer in range(2):
        for y, z in dense:
            outer = new_skin(z, y) - .008
            inner = max(.083, outer - .074)
            for j in range(across):
                t = j / (across - 1)
                # The graphite return folds inboard/forward below the untouched
                # white perimeter; the wheel/cowl opening remains physically open.
                vertices.append((side * (outer * (1 - t) + inner * t), y + .034 * t - layer * .0035, z))
    for layer in range(2):
        offset = count * layer
        for i in range(len(dense) - 1):
            for j in range(across - 1):
                a = offset + i * across + j
                face = (a, a + 1, a + across + 1, a + across)
                faces.append(face if layer == 0 else tuple(reversed(face)))
    boundary = list(range(across)) + [i * across + across - 1 for i in range(1, len(dense))]
    boundary += [(len(dense) - 1) * across + j for j in range(across - 2, -1, -1)]
    boundary += [i * across for i in range(len(dense) - 2, 0, -1)]
    for i, a in enumerate(boundary):
        b = boundary[(i + 1) % len(boundary)]; faces.append((a, b, b + count, a + count))
    name = 'R6 recessed front cooling return ' + str(side)
    mesh = bpy.data.meshes.new(name + ' mesh'); mesh.from_pydata(vertices, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj); obj.parent = root; obj['asset_group'] = 'Body'
    mesh.materials.append(bpy.data.materials['Apex_Graphite'])
    bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    nonmanifold = sum(not edge.is_manifold for edge in bm.edges); assert nonmanifold == 0
    bm.to_mesh(mesh); bm.free(); mesh.update()
    uv = mesh.uv_layers.new(name='UV0_SurfaceMetres')
    for face in mesh.polygons:
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co; uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    rows.append({'name': name, 'vertices': len(mesh.vertices), 'faces': len(mesh.polygons), 'nonManifoldEdges': nonmanifold})

bpy.context.view_layer.update()
def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True, epsilon=.000001)
belly_tree = tree(bpy.data.objects['R5 cleared compound belly shell'])
for row in rows:
    obj = bpy.data.objects[row['name']]; row['bellyTrianglePairs'] = len(tree(obj).overlap(belly_tree))
    assert row['bellyTrianglePairs'] == 0, 'New return intersects unchanged R5 belly'
root['r6Change'] = 'Study02: fairing planes, graphite seam and recessed closed front-edge returns; R5 belly/mechanics unchanged'
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable02.blend')
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces.active.region_3d.view_location = Vector((0, 0, .61))
        area.spaces.active.region_3d.view_distance = 3.0
        area.spaces.active.region_3d.view_rotation = bpy.context.scene.camera.rotation_euler.to_quaternion()
print('R6_STUDY02=' + json.dumps({'added': rows, 'saved': bpy.data.filepath, 'visualAccepted': False}))
