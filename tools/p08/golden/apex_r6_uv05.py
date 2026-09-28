"""Repair only collapsed finish-UV triangles in the edited R6 fairing system; preserve geometry positions."""
import bpy
import bmesh
import json

ROOT = 'D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\', '/').endswith('/R6/RB_Golden_Apex_r6_editable04.blend')
root = bpy.data.objects['RB_Golden_Apex_r6']
prefixes = ['R4 formed main fairing', 'R3 Recessed black intake return', 'R3 Intake plenum shadow',
            'R3 Recessed intake grille', 'R3 Fairing flush bolt', 'R3 Fairing bolt recess',
            'R3 Lower diagonal plenum', 'R3 Lower diagonal black cavity wall', 'R6 recessed front cooling return']
rows = []
for obj in root.children_recursive:
    if obj.type != 'MESH' or not any(obj.name.startswith(p) for p in prefixes): continue
    mesh = obj.data; uv = mesh.uv_layers.active; mesh.calc_loop_triangles()
    bad = 0
    for triangle in mesh.loop_triangles:
        p = [uv.data[index].uv for index in triangle.loops]
        if abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5 < 1e-12: bad += 1
    if bad == 0: continue
    positions = tuple(tuple(vertex.co) for vertex in mesh.vertices)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free(); mesh.update()
    assert tuple(tuple(vertex.co) for vertex in mesh.vertices) == positions, 'UV repair moved geometry'
    uv = mesh.uv_layers.active; fixed = 0
    for face in mesh.polygons:
        p = [uv.data[index].uv for index in face.loop_indices]
        area = abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5
        if area >= 1e-12: continue
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            position = obj.matrix_world @ mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (position[axes[0]] * 2, position[axes[1]] * 2)
        fixed += 1
    rows.append({'name': obj.name, 'collapsedUvBefore': bad, 'reprojectedFinishTriangles': fixed, 'vertexPositionsUnchanged': True})
root['r6Change'] = 'Study05: study04 geometry, collapsed fairing finish-UV triangles repaired; R5 belly/mechanics unchanged'
bpy.ops.wm.save_as_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/R6/RB_Golden_Apex_r6_editable05.blend')
print('R6_STUDY05=' + json.dumps({'repairs': rows, 'saved': bpy.data.filepath, 'visualAccepted': False}))
