"""Reimport the actual exported FBX in owned Blender and restore source state."""
import bpy
import json
import math
from mathutils.kdtree import KDTree

root = bpy.data.objects['RB_Golden_Spark_v1']
source = [root] + list(root.children_recursive)
source_names = {o: o.name for o in source}
source_material_names = {m: m.name for o in source if o.type == 'MESH' for m in o.data.materials}
expected = {}
for obj in source:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    kd = KDTree(len(mesh.vertices))
    for i, vertex in enumerate(mesh.vertices):
        kd.insert(obj.matrix_world @ vertex.co, i)
    kd.balance()
    expected[obj.name] = {'triangles': len(mesh.loop_triangles), 'parent': obj.parent.name,
                          'materials': [m.name for m in mesh.materials], 'tree': kd,
                          'points': [obj.matrix_world @ v.co for v in mesh.vertices]}
markers = {o.name: o.matrix_world.translation.copy() for o in source if o.type == 'EMPTY'}
before_objects = set(bpy.data.objects)
before_meshes = set(bpy.data.meshes)
before_materials = set(bpy.data.materials)
before_images = set(bpy.data.images)
rows = []
marker_rows = []
failures = []
try:
    for obj, name in source_names.items():
        obj.name = 'SparkSource_' + name
    for material, name in source_material_names.items():
        material.name = 'SparkSource_' + name
    bpy.ops.import_scene.fbx(filepath='D:/Project/Unity/racing-bois/_local/p08-spark-v1-staging/RB_Golden_Spark_v1.fbx',
                             use_anim=False, use_image_search=False)
    imported = list(set(bpy.data.objects) - before_objects)
    imported_meshes = [obj for obj in imported if obj.type == 'MESH']
    if {obj.name for obj in imported_meshes} != set(expected):
        failures.append('Renderer name coverage differs')
    for obj in imported_meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        reference = expected[obj.name]
        uv = mesh.uv_layers.active
        physical = invalid_uv = non_finite = 0
        minimum = float('inf')
        for tri in mesh.loop_triangles:
            q = [obj.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
            cross = (q[1]-q[0]).cross(q[2]-q[0]).length_squared
            minimum = min(minimum, cross)
            physical += cross <= 1e-16
            non_finite += sum(not math.isfinite(v) for p in q for v in p)
            if uv is None:
                invalid_uv += 1
            else:
                p = [uv.data[i].uv for i in tri.loops]
                invalid_uv += abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5 < 1e-12
        points = [obj.matrix_world @ v.co for v in mesh.vertices]
        kd = KDTree(len(points))
        for i, p in enumerate(points):
            kd.insert(p, i)
        kd.balance()
        max_delta = max([reference['tree'].find(p)[2] for p in points] + [kd.find(p)[2] for p in reference['points']])
        material_match = [m.name for m in mesh.materials] == reference['materials']
        triangle_match = len(mesh.loop_triangles) == reference['triangles']
        parent_match = obj.parent.name == reference['parent']
        if physical or invalid_uv or non_finite or max_delta > 1e-5 or not (material_match and triangle_match and parent_match):
            failures.append('Roundtrip mesh gate: ' + obj.name)
        rows.append({'name': obj.name, 'triangles': len(mesh.loop_triangles),
                     'exactTriangleCount': triangle_match, 'exactMaterialSlots': material_match,
                     'exactParent': parent_match, 'physicalFailures': physical, 'uvFailures': invalid_uv,
                     'nonFiniteValues': non_finite, 'minimumWorldCrossSquared': minimum,
                     'maximumBidirectionalVertexDistanceMetres': max_delta})
    imported_markers = {o.name: o for o in imported if o.type == 'EMPTY'}
    if set(imported_markers) != set(markers):
        failures.append('Marker coverage differs')
    for name, point in markers.items():
        actual = imported_markers[name].matrix_world.translation
        delta = (actual - point).length
        marker_rows.append({'name': name, 'positionBlender': list(actual), 'deltaMetres': delta})
        if delta > 1e-5:
            failures.append('Marker moved: ' + name)
finally:
    for obj in list(set(bpy.data.objects) - before_objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(set(bpy.data.meshes) - before_meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(set(bpy.data.materials) - before_materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for image in list(set(bpy.data.images) - before_images):
        if image.users == 0:
            bpy.data.images.remove(image)
    for obj, name in source_names.items():
        obj.name = name
    for material, name in source_material_names.items():
        material.name = name
print('SPARK_FBX_ROUNDTRIP=' + json.dumps({'schema': 1, 'passed': not failures, 'failures': failures,
      'objects': rows, 'markers': marker_rows, 'sourceSaved': False, 'visualAccepted': False,
      'scope': 'Blender FBX roundtrip only; Unity import, handedness and render remain separate gates.'}))
# The MCP addon drops captured stdout when code raises. Keep diagnostics in its
# successful transport response; the staged-payload builder must require passed.
