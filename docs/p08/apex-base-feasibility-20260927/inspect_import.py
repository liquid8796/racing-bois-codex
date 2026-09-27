"""Two licensed reference GLBs; isolated inspection, never writes game Assets."""
import bpy
import bmesh
import json
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois'
WORK = ROOT + '/_local/p08-apex-base-inspection-20260927'
uids = ['95a107fee2ab41bdb6e21bac72741781', '47f87e3d70f644289e34cbff91255d0c']
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute, 'Auto-execution must already be disabled'
previous_path = bpy.data.filepath
before_scenes = list(bpy.data.scenes)
report = {'previousFile': previous_path, 'autoExecuteScripts': False, 'models': []}

for uid in uids:
    scene = bpy.data.scenes.new('Inspection_' + uid[:8])
    bpy.context.window.scene = scene
    previous_objects = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=WORK + '/inputs/' + uid + '.glb')
    objects = [obj for obj in bpy.data.objects if obj not in previous_objects]
    meshes = [obj for obj in objects if obj.type == 'MESH']
    pts = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    rows = []
    material_names = set()
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        boundary = sum(edge.is_boundary for edge in bm.edges)
        nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
        wire = sum(edge.is_wire for edge in bm.edges)
        zero_area = sum(face.calc_area() <= 1e-20 for face in bm.faces)
        # Disconnected components show separability without assuming semantic parts.
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
        bm.free()
        names = [slot.material.name if slot.material else None for slot in obj.material_slots]
        material_names.update(name for name in names if name)
        rows.append({'name': obj.name, 'vertices': len(mesh.vertices), 'triangles': len(mesh.loop_triangles),
                     'boundaryEdges': boundary, 'nonManifoldEdges': nonmanifold, 'wireEdges': wire,
                     'zeroAreaFacesLocalThreshold1e20': zero_area, 'uvLayers': [uv.name for uv in mesh.uv_layers],
                     'materials': names, 'connectedComponents': len(components),
                     'largestComponentVertexCounts': components[:12], 'modifiers': [m.type for m in obj.modifiers]})
    # Normalize the inspection display only, preserving each source GLB unchanged.
    longest = max(hi.x - lo.x, hi.y - lo.y)
    scale = 2.05 / longest
    display_root = bpy.data.objects.new('InspectionDisplayScale_' + uid[:8], None)
    scene.collection.objects.link(display_root)
    for obj in objects:
        if obj.parent is None:
            obj.parent = display_root
    display_root.scale = (scale, scale, scale)
    display_root.location = (-(lo.x + hi.x) * .5 * scale, -(lo.y + hi.y) * .5 * scale, -lo.z * scale)
    materials = []
    for name in sorted(material_names):
        mat = bpy.data.materials[name]
        textures = []
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    im = node.image
                    textures.append({'image': im.name if im else None, 'size': list(im.size) if im else None,
                                     'packed': bool(im and im.packed_file), 'hasData': bool(im and im.has_data)})
        materials.append({'name': name, 'useNodes': mat.use_nodes, 'textures': textures})
    report['models'].append({'uid': uid, 'scene': scene.name, 'sourceBounds': {'min': list(lo), 'max': list(hi)},
                             'inspectionScaleOnly': scale, 'displayLongestFootprintMetres': 2.05,
                             'objectCount': len(objects), 'meshObjects': rows, 'materials': materials,
                             'sourceObjectNames': [obj.name for obj in objects]})

# Delete only pre-existing in-memory scenes after import. Saved source files stay untouched.
for old_scene in before_scenes:
    bpy.data.scenes.remove(old_scene)
for obj in list(bpy.data.objects):
    if not obj.users_scene:
        bpy.data.objects.remove(obj)
bpy.context.scene['InspectionReport'] = json.dumps(report)
bpy.ops.wm.save_as_mainfile(filepath=WORK + '/licensed-base-inspection.blend')
print('INSPECTION_REPORT=' + json.dumps(report))
print(json.dumps({'models': [{'uid': m['uid'], 'objects': m['objectCount'], 'meshes': len(m['meshObjects']),
                             'triangles': sum(o['triangles'] for o in m['meshObjects']),
                             'boundaryEdges': sum(o['boundaryEdges'] for o in m['meshObjects']),
                             'nonManifoldEdges': sum(o['nonManifoldEdges'] for o in m['meshObjects']),
                             'bounds': m['sourceBounds']} for m in report['models']],
                  'saved': bpy.data.filepath, 'scriptsAutoExecute': bpy.context.preferences.filepaths.use_scripts_auto_execute}))
