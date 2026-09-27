import bpy
import bmesh
import json
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend', load_ui=False, use_scripts=False)
rows = []
for name in ['R4 angular pressed fuel tank', 'R4 formed main fairing with through intake -1', 'R4 formed main fairing with through intake 1']:
    obj = bpy.data.objects[name]
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000020)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.000005)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    failures = sum(not edge.is_manifold for edge in bm.edges)
    assert failures == 0, name + ' lost closure during micro-vertex repair'
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    mesh.calc_loop_triangles()
    minimum = min((mesh.vertices[t.vertices[1]].co - mesh.vertices[t.vertices[0]].co).cross(mesh.vertices[t.vertices[2]].co - mesh.vertices[t.vertices[0]].co).length_squared for t in mesh.loop_triangles)
    assert minimum > 1e-16, name + ' still fails physical triangle gate'
    rows.append({'name': name, 'mergedVertices': before - len(mesh.vertices), 'nonManifoldEdges': failures, 'minimumCrossSquared': minimum})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_SOURCE_CLEANUP=' + json.dumps(rows))
