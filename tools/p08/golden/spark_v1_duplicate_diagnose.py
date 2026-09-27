"""Measure duplicate-index triangles and their connected components."""
import bpy
import bmesh
import json
obj = bpy.data.objects['Spark_L2_Body']
bm = bmesh.new()
bm.from_mesh(obj.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()
index_faces = {}
for face in bm.faces:
    key = tuple(sorted(v.index for v in face.verts))
    index_faces.setdefault(key, []).append(face)
groups = [faces for faces in index_faces.values() if len(faces) > 1]
seen = set()
components = []
for faces in groups:
    seed = faces[0].verts[0]
    if seed in seen:
        continue
    component = set()
    todo = [seed]
    while todo:
        v = todo.pop()
        if v in component:
            continue
        component.add(v)
        seen.add(v)
        for edge in v.link_edges:
            todo.append(edge.other_vert(v))
    attached = {f for v in component for f in v.link_faces}
    minimum = [min(v.co[i] for v in component) for i in range(3)]
    maximum = [max(v.co[i] for v in component) for i in range(3)]
    components.append({'vertices': len(component), 'faces': len(attached),
                       'surfaceArea': sum(f.calc_area() for f in attached),
                       'minimum': minimum, 'maximum': maximum,
                       'materials': sorted({obj.data.materials[f.material_index].name for f in attached})})
result = {'duplicateTriangleGroups': len(groups), 'extraIndexDuplicateTriangles': sum(len(g)-1 for g in groups),
          'components': components}
bm.free()
print('SPARK_DUPLICATE_DIAGNOSIS=' + json.dumps(result))
