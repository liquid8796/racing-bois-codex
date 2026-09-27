"""Direct pinned MCP source audit and isolated FBX export; no Unity writes."""
import bpy
import bmesh
import json
import math

SOURCE = 'D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_export.blend'
DESTINATION = 'D:/Project/Unity/racing-bois/_local/p08-spark-v1-staging/RB_Golden_Spark_v1.fbx'
assert bpy.data.filepath.replace('\\', '/') == SOURCE, 'Wrong source scene'
root = bpy.data.objects['RB_Golden_Spark_v1']
def named(item):
    return item.name

meshes = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=named)
expected = {'Spark_L%d_%s' % (level, group) for level in range(3) for group in ('Body', 'Front', 'Rear')}
assert {o.name for o in meshes} == expected, 'Unexpected renderer coverage'
rows = []
points = []
failures = []
for obj in meshes:
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active
    physical = invalid_uv = invalid_values = 0
    min_cross = min_uv = float('inf')
    material_counts = {}
    for triangle in mesh.loop_triangles:
        world = [obj.matrix_world @ mesh.vertices[i].co for i in triangle.vertices]
        cross = (world[1] - world[0]).cross(world[2] - world[0]).length_squared
        min_cross = min(min_cross, cross)
        physical += cross <= 1e-16
        invalid_values += sum(not math.isfinite(value) for point in world for value in point)
        if uv is None:
            invalid_uv += 1
        else:
            p = [uv.data[i].uv for i in triangle.loops]
            area = abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x)) * .5
            min_uv = min(min_uv, area)
            invalid_uv += area < 1e-12
            invalid_values += sum(not math.isfinite(value) for point in p for value in point)
        material = mesh.materials[triangle.material_index]
        if material is None:
            failures.append('Missing material slot: ' + obj.name)
        else:
            material_counts[material.name] = material_counts.get(material.name, 0) + 1
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    non_manifold = sum(not e.is_manifold for e in bm.edges)
    loose_vertices = sum(not v.link_faces for v in bm.verts)
    face_keys = [tuple(sorted(v.index for v in face.verts)) for face in bm.faces]
    duplicate_faces = len(face_keys) - len(set(face_keys))
    bm.free()
    if physical or invalid_uv or invalid_values or non_manifold or loose_vertices or duplicate_faces:
        failures.append('Source mesh gate: ' + obj.name)
    if '_L0_' in obj.name:
        points.extend(obj.matrix_world @ v.co for v in mesh.vertices)
    rows.append({'name': obj.name, 'parent': obj.parent.name, 'triangles': len(mesh.loop_triangles),
                 'vertices': len(mesh.vertices), 'physicalFailures': physical, 'uvFailures': invalid_uv,
                 'nonFiniteValues': invalid_values, 'nonManifoldEdges': non_manifold,
                 'looseVertices': loose_vertices, 'minimumWorldCrossSquared': min_cross,
                 'duplicateIndexFaces': duplicate_faces,
                 'minimumUvArea': min_uv, 'uvLayers': [layer.name for layer in mesh.uv_layers],
                 'materialTriangleCounts': material_counts, 'localPosition': list(obj.location),
                 'localScale': list(obj.scale)})
minimum = [min(p[i] for p in points) for i in range(3)]
maximum = [max(p[i] for p in points) for i in range(3)]
materials = []
for mat in sorted({m for o in meshes for m in o.data.materials}, key=named):
    shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        failures.append('Missing Principled shader: ' + mat.name)
        continue
    images = [{'path': n.image.filepath, 'size': list(n.image.size), 'packed': n.image.packed_file is not None,
               'colorSpace': n.image.colorspace_settings.name, 'alphaMode': n.image.alpha_mode}
              for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    if not images or any(not all(image['size']) for image in images):
        failures.append('Missing texture data: ' + mat.name)
    materials.append({'name': mat.name, 'images': images,
                      'shaderVectorScalingNodes': [n.type for n in mat.node_tree.nodes if n.type in ('MAPPING', 'VECT_MATH')],
                      'coatWeight': shader.inputs['Coat Weight'].default_value,
                      'transmissionWeight': shader.inputs['Transmission Weight'].default_value,
                      'ior': shader.inputs['IOR'].default_value,
                      'alpha': shader.inputs['Alpha'].default_value,
                      'emissionStrength': shader.inputs['Emission Strength'].default_value})
markers = {o.name: list(o.matrix_world.translation) for o in root.children_recursive if o.type == 'EMPTY'}
result = {'schema': 1, 'passed': not failures, 'failures': failures, 'source': SOURCE,
          'objects': rows, 'materials': materials, 'markersBlender': markers,
          'boundsBlender': {'minimum': minimum, 'maximum': maximum},
          'intendedUnitySize': [maximum[0]-minimum[0], maximum[2]-minimum[2], maximum[1]-minimum[1]],
          'lodTriangles': [sum(r['triangles'] for r in rows if '_L%d_' % i in r['name']) for i in range(3)],
          'uvPolicy': 'Authored repeating finish coordinates; Copper tank atlas retained. Overlap is intentional, not a unique-lightmap unwrap.',
          'visualAccepted': False, 'unityImportVerified': False}
print('SPARK_SOURCE_AUDIT=' + json.dumps(result))
assert not failures, 'Keep failure receipt and repair before export'
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
for obj in root.children_recursive:
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=DESTINATION, use_selection=True, object_types={'MESH', 'EMPTY'},
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_space_transform=False,
                         add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
print('SPARK_EXPORT=' + json.dumps({'path': DESTINATION, 'sourceSaved': False, 'assetsWritten': False,
                                   'selectedObjects': len(root.children_recursive) + 1, 'visualAccepted': False}))
