"""Restore closed thickness only to 36 measured collapsed LOD2 dial markings."""
import bpy
import bmesh
import json

obj = bpy.data.objects['Spark_L2_Body']
assert bpy.data.filepath.replace('\\', '/').endswith('/RB_Golden_Spark_v1_assembled.blend')
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
index_faces = {}
for face in bm.faces:
    key = tuple(sorted(v.index for v in face.verts))
    index_faces.setdefault(key, []).append(face)
groups = [faces for faces in index_faces.values() if len(faces) > 1]
assert len(groups) == 36, 'Unexpected duplicate scope'
uv = bm.loops.layers.uv.active
assert uv is not None
before = len(bm.faces)
rows = []
for faces in groups:
    assert len(faces) == 2 and len(faces[0].verts) == 3
    face = faces[0]
    vertices = list(face.verts)
    assert {f for v in vertices for f in v.link_faces} == set(faces), 'Not an isolated collapsed component'
    assert all(abs(v.co.x) < .1 and .42 < v.co.y < .47 and 1.02 < v.co.z < 1.061 for v in vertices)
    material = face.material_index
    assert obj.data.materials[material].name in {'Spark_Cream', 'Spark_RedLamp'}
    assert sum(f.calc_area() for f in faces) < .0001
    normal = face.normal.normalized()
    cap_uv = {loop.vert: loop[uv].uv.copy() for loop in face.loops}
    opposite = [bm.verts.new(v.co - normal * .0004) for v in vertices]
    bmesh.ops.delete(bm, geom=faces, context='FACES_ONLY')
    top = bm.faces.new(vertices)
    bottom = bm.faces.new(list(reversed(opposite)))
    for cap in (top, bottom):
        cap.material_index = material
        for loop in cap.loops:
            original = loop.vert if loop.vert in cap_uv else vertices[opposite.index(loop.vert)]
            loop[uv].uv = cap_uv[original]
    for i in range(3):
        j = (i + 1) % 3
        side = bm.faces.new([vertices[j], vertices[i], opposite[i], opposite[j]])
        side.material_index = material
        width = (vertices[j].co - vertices[i].co).length * 2
        coordinates = ((width, 0), (0, 0), (0, .0008), (width, .0008))
        for loop, coordinate in zip(side.loops, coordinates):
            loop[uv].uv = coordinate
    rows.append({'material': obj.data.materials[material].name, 'thicknessMetres': .0004})
bmesh.ops.triangulate(bm, faces=list(bm.faces))
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges)
after = len(bm.faces)
assert after - before == 36 * 6
bm.to_mesh(obj.data)
bm.free()
obj.data.update()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_export.blend')
print('SPARK_GAUGE_REPAIR=' + json.dumps({'components': rows, 'bodyTrianglesBefore': before,
      'bodyTrianglesAfter': after, 'lod0AndLod1Unchanged': True,
      'originalAssembledSourcePreserved': True, 'visualAccepted': False}))
