import bpy
import bmesh
import json

report = []
for scene in bpy.data.scenes:
    if not scene.name.startswith('Inspection_'):
        continue
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    objects = [obj for obj in scene.objects if obj.type == 'MESH' and not obj.name.startswith('INSPECTION')]
    minimum = min((obj.matrix_world @ v.co).z for obj in objects for v in obj.data.vertices)
    root = next(obj for obj in scene.objects if obj.name.startswith('InspectionDisplayScale_'))
    root.location.z -= minimum
    bpy.context.view_layer.update()
    bm = bmesh.new()
    for obj in objects:
        before = len(bm.verts)
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in list(bm.verts)[before:]:
            v.co = obj.matrix_world @ v.co
    raw_vertices = len(bm.verts)
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
    sizes_by_root = {i: sizes[i] for i in range(len(parent)) if parent[i] == i}
    bad_roots = set()
    for edge in bm.edges:
        if not edge.is_manifold:
            bad_roots.add(find(edge.verts[0].index))
    report.append({'scene': scene.name, 'diagnosticOnlyAggregateWeldMetres': .000001,
                   'sourceMeshesUnmodified': True, 'rawVertices': raw_vertices, 'weldedVertices': len(bm.verts),
                   'boundaryEdges': sum(e.is_boundary for e in bm.edges),
                   'nonManifoldEdges': sum(not e.is_manifold for e in bm.edges),
                   'connectedComponents': len(sizes_by_root), 'closedComponents': len(sizes_by_root) - len(bad_roots),
                   'largestClosedComponentVertexCounts': sorted((size for index, size in sizes_by_root.items() if index not in bad_roots), reverse=True)[:20],
                   'zeroAreaFacesPhysicalThreshold1e20': sum(f.calc_area() <= 1e-20 for f in bm.faces),
                   'displayRootGroundAdjustmentMetres': -minimum})
    bm.free()
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/_local/p08-apex-base-inspection-20260927/licensed-base-inspection.blend')
print('AGGREGATE_REPORT=' + json.dumps(report))
