"""Read-only R4 component intersection diagnosis in the dedicated direct-MCP scene."""
import bpy
import bmesh
import json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = 'D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT + 'ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend', load_ui=False, use_scripts=False)
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
root = bpy.data.objects['RB_Golden_Apex_r4']
names = ['R4 formed main fairing', 'R4 compound stepped belly shell', 'R3 Lower diagonal', 'R3 Recessed black intake return']
objects = [obj for obj in root.children_recursive if obj.type == 'MESH' and any(obj.name.startswith(prefix) for prefix in names)]
rows = []
trees = {}
for obj in objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    trees[obj.name] = BVHTree.FromPolygons(vertices, triangles, all_triangles=True, epsilon=0.000001)
    bm = bmesh.new(); bm.from_mesh(mesh)
    rows.append({'name': obj.name, 'vertices': len(vertices), 'triangles': len(triangles),
                 'boundsMin': [min(v[i] for v in vertices) for i in range(3)],
                 'boundsMax': [max(v[i] for v in vertices) for i in range(3)],
                 'nonManifoldEdges': sum(not e.is_manifold for e in bm.edges),
                 'materials': [m.name for m in mesh.materials]})
    bm.free()
belly = bpy.data.objects['R4 compound stepped belly shell']
pairs = []
for obj in objects:
    if obj == belly:
        continue
    hits = trees[obj.name].overlap(trees[belly.name])
    triangle_centers = []
    for index in sorted(set(a for a, b in hits)):
        triangle = obj.data.loop_triangles[index]
        center = sum((obj.matrix_world @ obj.data.vertices[i].co for i in triangle.vertices), Vector()) / 3
        triangle_centers.append(list(center))
    pairs.append({'component': obj.name, 'other': belly.name, 'intersectingTrianglePairs': len(hits),
                  'intersectingComponentTriangleCenters': triangle_centers})
report = {'source': bpy.data.filepath, 'scope': 'Native editable R4 meshes only; no source mutation or acceptance.',
          'components': rows, 'bellyIntersections': pairs}
print('R4_COMPONENT_DIAGNOSIS=' + json.dumps(report))
