import bpy
import bmesh
import json

report = []
for scene in bpy.data.scenes:
    if not scene.name.startswith('Inspection_'):
        continue
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    rows = []
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        before = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
        bm.verts.ensure_lookup_table()
        parent = list(range(len(bm.verts)))
        sizes = [1] * len(parent)
        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index
        for edge in bm.edges:
            a, b = find(edge.verts[0].index), find(edge.verts[1].index)
            if a != b:
                if sizes[a] < sizes[b]:
                    a, b = b, a
                parent[b] = a
                sizes[a] += sizes[b]
        components = sorted((sizes[i] for i in range(len(parent)) if parent[i] == i), reverse=True)
        rows.append({'name': obj.name, 'rawVertices': before, 'weldedVertices': len(bm.verts),
                     'boundaryEdges': sum(e.is_boundary for e in bm.edges),
                     'nonManifoldEdges': sum(not e.is_manifold for e in bm.edges),
                     'connectedComponents': len(components), 'largestComponents': components[:10],
                     'zeroAreaFacesPhysicalThreshold1e20': sum(f.calc_area() <= 1e-20 for f in bm.faces)})
        bm.free()
    report.append({'scene': scene.name, 'diagnosticOnlyWeldMetres': 0.000001,
                   'sourceMeshesUnmodified': True, 'meshes': rows})
print('WELD_REPORT=' + json.dumps(report))
