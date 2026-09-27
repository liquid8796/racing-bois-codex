"""Replace only R4's intersecting belly with a closed, inboard R5 return shell."""
import bpy
import bmesh
import math
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = 'D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend', load_ui=False, use_scripts=False)
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
root = bpy.data.objects['RB_Golden_Apex_r4']
root.name = 'RB_Golden_Apex_r5'
for obj in root.children:
    if obj.name.endswith('_Wheel_Front'): obj.name = 'RB_Golden_Apex_r5_Wheel_Front'
    elif obj.name.endswith('_Wheel_Rear'): obj.name = 'RB_Golden_Apex_r5_Wheel_Rear'
root['referenceConceptSha256'] = 'f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819'
root['visualAccepted'] = False
root['r5Change'] = 'Belly return shell clearance only; all other R4 geometry/materials retained'

def formed_skin(z, y):
    width = .155 + .123 * math.exp(-((z - .71) / .285) ** 2 - ((y - .40) / .36) ** 2)
    width -= .055 * math.exp(-((z - .59) / .18) ** 2 - ((y - .095) / .19) ** 2)
    width -= .069 * max(0, min(1, (y - .54) / .25))
    width -= .031 * max(0, min(1, (.40 - z) / .20))
    return width

profile = [(0, 1), (.62, .99), (.92, .84), (1, .69), (.97, .47), (.84, .33), (.72, .13), (.45, 0),
           (0, 0), (-.45, 0), (-.72, .13), (-.84, .33), (-.97, .47), (-1, .69), (-.92, .84), (-.62, .99)]
sections = [(-.354, .235, .367, .133), (-.257, .216, .408, .178), (-.084, .199, .435, .205),
            (.160, .193, .452, .213), (.338, .194, .432, .189), (.474, .203, .289, .135)]
dense = [sections[0]]
for a, b in zip(sections, sections[1:]):
    count = math.ceil((b[0] - a[0]) / .012)
    dense.extend(tuple(a[j] + (b[j] - a[j]) * i / count for j in range(4)) for i in range(1, count + 1))
vertices = []; faces = []; n = len(profile)
for k, (y, bottom, top, width) in enumerate(dense):
    for x, z in profile:
        z = bottom + z * (top - bottom)
        magnitude = abs(x * width)
        # The outer white skin is unchanged. A continuous inner return clears
        # its true 5 mm wall and the recessed lower diagonal vent body.
        clearance = formed_skin(z, y) - .021
        vent_clearance = .101 + max(0, .375 - z) * 3
        limit = min(clearance, vent_clearance)
        t = max(0, min(1, (y + .08) / .13)); t = t * t * (3 - 2 * t)
        magnitude += (min(magnitude, limit) - magnitude) * t
        vertices.append((math.copysign(magnitude, x) if x else 0, y, z))
    if k:
        faces.extend(((k-1)*n+j, (k-1)*n+(j+1)%n, k*n+(j+1)%n, k*n+j) for j in range(n))
faces.append(tuple(reversed(range(n))))
faces.append(tuple((len(dense)-1)*n+j for j in range(n)))
mesh = bpy.data.meshes.new('R5 inboard belly return mesh')
mesh.from_pydata(vertices, [], faces); mesh.update()
belly = bpy.data.objects.new('R5 cleared compound belly shell', mesh)
bpy.context.scene.collection.objects.link(belly); belly.parent = root; belly['asset_group'] = 'Body'
mesh.materials.append(bpy.data.materials['Apex_Graphite'])
bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
mesh = belly.data
bm = bmesh.new(); bm.from_mesh(mesh)
bm.normal_update()
corners = [edge for edge in bm.edges if edge.is_manifold and edge.calc_face_angle() > .35]
bmesh.ops.bevel(bm, geom=corners, offset=.001, segments=2, affect='EDGES', clamp_overlap=True)
for face in bm.faces: face.smooth = True
for edge in bm.edges:
    direction = (edge.verts[1].co - edge.verts[0].co).normalized()
    edge.smooth = not (len(edge.link_faces) == 2 and abs(direction.y) > .55 and edge.calc_face_angle() > .35)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
uv = mesh.uv_layers.new(name='UV0_SurfaceMetres')
for face in mesh.polygons:
    axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
    axes = [i for i in range(3) if i != axis]
    for loop in face.loop_indices:
        p = mesh.vertices[mesh.loops[loop].vertex_index].co; uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
old = bpy.data.objects['R4 compound stepped belly shell']; bpy.data.objects.remove(old, do_unlink=True)

def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons([obj.matrix_world @ v.co for v in obj.data.vertices],
                               [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True, epsilon=.000001)
bpy.context.view_layer.update()
belly_tree = tree(belly)
others = [o for o in root.children_recursive if o.type == 'MESH' and any(o.name.startswith(p) for p in
          ['R4 formed main fairing', 'R3 Lower diagonal', 'R3 Recessed black intake return'])]
intersections = [{'component': o.name, 'trianglePairs': len(tree(o).overlap(belly_tree))} for o in others]
bm = bmesh.new(); bm.from_mesh(mesh); nonmanifold = sum(not e.is_manifold for e in bm.edges); bm.free()
scene = bpy.context.scene; scene.cycles.device = 'CPU'; scene.render.threads_mode = 'FIXED'; scene.render.threads = 4; scene.cycles.samples = 24
scene.render.resolution_x = 1280; scene.render.resolution_y = 900; scene.render.resolution_percentage = 100
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R5/RB_Golden_Apex_r5_editable01.blend')
print('R5_SEAM=' + json.dumps({'bellyTriangles': len(mesh.loop_triangles), 'nonManifoldEdges': nonmanifold,
      'intersections': intersections, 'saved': bpy.data.filepath, 'visualAccepted': False}))
