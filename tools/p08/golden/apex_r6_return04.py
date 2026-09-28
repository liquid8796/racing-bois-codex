"""Preserve study03; restore its return back layers to the intended 3.5mm offset without a second X inset."""
import bpy
import bmesh
import json

ROOT = 'D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\', '/').endswith('/R6/RB_Golden_Apex_r6_editable03.blend')
rows = []
for side in [-1, 1]:
    obj = bpy.data.objects['R6 recessed front cooling return ' + str(side)]
    mesh = obj.data; count = len(mesh.vertices) // 2
    for i in range(count):
        front = mesh.vertices[i].co; back = mesh.vertices[i + count].co
        back.x = front.x; back.y = front.y - .0035; back.z = front.z
    bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    nonmanifold = sum(not edge.is_manifold for edge in bm.edges); assert nonmanifold == 0
    bm.to_mesh(mesh); bm.free(); mesh.update()
    uv = mesh.uv_layers.active
    for face in mesh.polygons:
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co; uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    rows.append({'name': obj.name, 'backLayerForwardOffset': -.0035, 'matchingFrontBackX': all(mesh.vertices[i].co.x == mesh.vertices[i + count].co.x for i in range(count)), 'nonManifoldEdges': nonmanifold})
bpy.data.objects['RB_Golden_Apex_r6']['r6Change'] = 'Study04: narrow fairing cooling returns with corrected layer pairing; fairing planes/seam retained; R5 belly/mechanics unchanged'
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable04.blend')
print('R6_STUDY04=' + json.dumps({'changed': rows, 'saved': bpy.data.filepath, 'visualAccepted': False}))
