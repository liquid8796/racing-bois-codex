"""Local-only FBX audit after actual candidate render review; no Assets writes."""
import bpy, json, math
from array import array

ROOT = 'D:/Project/Unity/racing-bois/'
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_05.blend'):
    raise RuntimeError('Expected separate, already rendered candidate05.')
root = bpy.data.objects['RB_Golden_Canyon']
owned = [root]+list(root.children_recursive)
source_meshes = [obj for obj in owned if obj.type == 'MESH']
expected = {}
for obj in source_meshes:
    obj.data.calc_loop_triangles()
    expected[obj.name] = len(obj.data.loop_triangles)
states = [(obj, obj.hide_get(), obj.select_get()) for obj in bpy.context.view_layer.objects]
active = bpy.context.view_layer.objects.active
fbx = ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.fbx'
try:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in owned:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'EMPTY','MESH'},
        axis_forward='-Z', axis_up='Y', use_mesh_modifiers=True, add_leaf_bones=False,
        bake_anim=False, path_mode='STRIP', use_custom_props=True)
finally:
    for obj, hidden, selected in states:
        obj.hide_set(hidden)
        obj.select_set(selected)
    bpy.context.view_layer.objects.active = active

names = {obj: obj.name for obj in owned}
before_objects = set(bpy.data.objects)
before_meshes = set(bpy.data.meshes)
before_materials = set(bpy.data.materials)
before_images = set(bpy.data.images)
created = []
rows = []
try:
    for obj, name in names.items():
        obj.name = 'SourceV17Audit05_'+name
    bpy.ops.import_scene.fbx(filepath=fbx, use_anim=False, use_image_search=False)
    created = list(set(bpy.data.objects)-before_objects)
    imported = [obj for obj in created if obj.type == 'MESH']
    if set(obj.name for obj in imported) != set(expected):
        raise RuntimeError('FBX renderer coverage differs from source.')
    for obj in imported:
        mesh = obj.data
        mesh.calc_loop_triangles()
        if len(mesh.loop_triangles) != expected[obj.name]:
            raise RuntimeError('FBX triangle count differs: '+obj.name)
        if not mesh.uv_layers.active:
            raise RuntimeError('FBX primary UV missing: '+obj.name)
        values = array('f', [0]) * (len(mesh.loops)*2)
        mesh.uv_layers.active.data.foreach_get('uv', values)
        transform = obj.matrix_world.to_3x3()
        bad_uv = []
        bad_physical = []
        minimum_uv = None
        minimum_physical = None
        for triangle in mesh.loop_triangles:
            ia, ib, ic = [index*2 for index in triangle.loops]
            cross = ((values[ib]-values[ia])*(values[ic+1]-values[ia+1])
                     - (values[ib+1]-values[ia+1])*(values[ic]-values[ia]))
            magnitude = abs(cross)
            minimum_uv = magnitude if minimum_uv is None else min(minimum_uv, magnitude)
            if not math.isfinite(cross) or magnitude <= 1e-14:
                bad_uv.append({'triangle': triangle.index, 'cross': cross,
                               'uv': [[values[index*2], values[index*2+1]] for index in triangle.loops]})
            a, b, c = [mesh.vertices[index].co for index in triangle.vertices]
            first = transform @ (b-a)
            second = transform @ (c-a)
            physical = first.cross(second).length_squared
            minimum_physical = physical if minimum_physical is None else min(minimum_physical, physical)
            if not math.isfinite(physical) or physical <= 1e-16:
                bad_physical.append({'triangle': triangle.index, 'crossSquaredMetres': physical})
        rows.append({'object': obj.name, 'sourceAndExportTriangles': len(mesh.loop_triangles),
                     'minimumAbsoluteUvCross': minimum_uv, 'minimumPhysicalCrossSquaredMetres': minimum_physical,
                     'collapsedUV': bad_uv, 'degeneratePhysicalTriangles': bad_physical})
finally:
    # Also clean a partially completed import, using the exact pre-import set.
    for obj in set(bpy.data.objects)-before_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in set(bpy.data.meshes)-before_meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for material in set(bpy.data.materials)-before_materials:
        if material.users == 0:
            bpy.data.materials.remove(material)
    for image in set(bpy.data.images)-before_images:
        if image.users == 0:
            bpy.data.images.remove(image)
    for obj, name in names.items():
        obj.name = name
    for obj, hidden, selected in states:
        obj.hide_set(hidden)
        obj.select_set(selected)
    bpy.context.view_layer.objects.active = active
    if (set(bpy.data.objects) != before_objects or set(bpy.data.meshes) != before_meshes
            or set(bpy.data.materials) != before_materials or set(bpy.data.images) != before_images):
        raise RuntimeError('Owned import cleanup left changed datablock membership.')

uv_failures = sum(len(row['collapsedUV']) for row in rows)
physical_failures = sum(len(row['degeneratePhysicalTriangles']) for row in rows)
passed = uv_failures == 0 and physical_failures == 0
print('CANYON_V17_ROUNDTRIP05 '+json.dumps({'source': bpy.data.filepath, 'fbx': fbx, 'passed': passed,
      'exactRendererCoverage': True, 'exactPerMeshTriangleCounts': True, 'meshCount': len(rows),
      'triangles': sum(row['sourceAndExportTriangles'] for row in rows), 'collapsedUvTriangles': uv_failures,
      'degeneratePhysicalTriangles': physical_failures, 'uvThresholdStrictlyGreaterThan': 1e-14,
      'physicalCrossSquaredThresholdStrictlyGreaterThan': 1e-16, 'rows': rows,
      'scope': 'Actual local Blender FBX export/reimport geometry and UV validation. No Unity import or visual acceptance.',
      'exactObjectMeshMaterialImageMembershipRestored': True,
      'exportedToAssets': False, 'visualAccepted': False}))
if not passed:
    raise RuntimeError('FBX roundtrip technical validation failed; preserve source and receipt.')
