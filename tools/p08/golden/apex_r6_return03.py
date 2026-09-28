"""Narrow the R6 study02 return after its actual quarter render showed an oversized box-like edge."""
import bpy
import bmesh
import json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\', '/').endswith('/R6/RB_Golden_Apex_r6_editable02.blend')
root = bpy.data.objects['RB_Golden_Apex_r6']
rows = []
for side in [-1, 1]:
    obj = bpy.data.objects['R6 recessed front cooling return ' + str(side)]
    mesh = obj.data; count = len(mesh.vertices) // 2; across = 5
    for vertex in mesh.vertices:
        layer = vertex.index // count; within = vertex.index % count
        j = within % across; t = j / (across - 1); base = within - j
        old_outer = abs(mesh.vertices[base].co.x)
        # Read the original outer point before this row is edited (j0 is first).
        if j == 0: row_outer = old_outer
        z = vertex.co.z
        outer = row_outer - .007
        width = .026 + .013 * max(0, min(1, (z - .25) / .28))
        vertex.co.x = side * (outer - width * t)
        vertex.co.y -= .014 * t
    bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    nonmanifold = sum(not edge.is_manifold for edge in bm.edges); assert nonmanifold == 0
    bm.to_mesh(mesh); bm.free(); mesh.update()
    uv = mesh.uv_layers.active
    for face in mesh.polygons:
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co; uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    rows.append({'name': obj.name, 'returnWidthMetres': [.026, .039], 'inboardRecessAddedMetres': .007, 'nonManifoldEdges': nonmanifold})
root['r6Change'] = 'Study03: fairing planes/graphite seam, narrower recessed front return; R5 belly/mechanics unchanged'
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable03.blend')
print('R6_STUDY03=' + json.dumps({'changed': rows, 'saved': bpy.data.filepath, 'visualAccepted': False}))
