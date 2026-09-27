"""Read-only exact per-LOD source and frozen FBX bounds for the native envelope."""
import bpy, json, math

ROOT = 'D:/Project/Unity/racing-bois/'
if bpy.data.filepath.replace('\\', '/') != ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.blend':
    raise RuntimeError('Expected owned frozen05; do not modify another scene.')
root = bpy.data.objects['RB_Golden_Canyon']
owned = [root]+list(root.children_recursive)
states = [(obj, obj.hide_get(), obj.select_get()) for obj in bpy.context.view_layer.objects]
active = bpy.context.view_layer.objects.active

def measure(objects, model_root):
    levels = []
    for level in range(3):
        low = [float('inf')]*3
        high = [float('-inf')]*3
        low_owner = [None]*3
        high_owner = [None]*3
        rows = []
        for obj in objects:
            if obj.type != 'MESH' or '_L%d_' % level not in obj.name:
                continue
            transform = obj.matrix_world
            obj_low = [float('inf')]*3
            obj_high = [float('-inf')]*3
            for vertex in obj.data.vertices:
                transformed = transform @ vertex.co
                point = (transformed.x, transformed.z, transformed.y)
                for axis in range(3):
                    if not math.isfinite(point[axis]):
                        raise RuntimeError('Nonfinite physical vertex: '+obj.name)
                    obj_low[axis] = min(obj_low[axis], point[axis])
                    obj_high[axis] = max(obj_high[axis], point[axis])
                    if point[axis] < low[axis]:
                        low[axis] = point[axis]
                        low_owner[axis] = {'object': obj.name, 'vertex': vertex.index}
                    if point[axis] > high[axis]:
                        high[axis] = point[axis]
                        high_owner[axis] = {'object': obj.name, 'vertex': vertex.index}
            rows.append({'object': obj.name, 'vertices': len(obj.data.vertices), 'minimum': obj_low, 'maximum': obj_high})
        levels.append({'level': level, 'meshCount': len(rows), 'minimumUnity': low, 'maximumUnity': high,
                       'sizeUnity': [high[axis]-low[axis] for axis in range(3)],
                       'minimumOwners': low_owner, 'maximumOwners': high_owner, 'meshes': rows})
    return levels

source_bounds = measure(root.children_recursive, root)
names = {obj: obj.name for obj in owned}
before_objects = set(bpy.data.objects)
before_meshes = set(bpy.data.meshes)
before_materials = set(bpy.data.materials)
before_images = set(bpy.data.images)
fbx_bounds = None
try:
    for obj, name in names.items():
        obj.name = 'SourceBounds05_'+name
    bpy.ops.import_scene.fbx(filepath=ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_05.fbx',
                             use_anim=False, use_image_search=False)
    created = list(set(bpy.data.objects)-before_objects)
    imported_root = bpy.data.objects.get('RB_Golden_Canyon')
    if imported_root is None or imported_root not in created:
        raise RuntimeError('Expected imported FBX root absent.')
    imported_meshes = [obj for obj in created if obj.type == 'MESH']
    expected = set()
    for level in source_bounds:
        expected.update(row['object'] for row in level['meshes'])
    if set(obj.name for obj in imported_meshes) != expected:
        raise RuntimeError('FBX renderer coverage differs from source.')
    fbx_bounds = measure(imported_root.children_recursive, imported_root)
finally:
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
        raise RuntimeError('Bounds audit did not restore exact owned datablock membership.')

print('CANYON_V17_LOD_BOUNDS_R1 '+json.dumps({'source': bpy.data.filepath,
      'method': 'Actual transformed mesh vertices in world metre space, Unity axis x,z,y. No bound_box or renderer AABB approximation.',
      'sourceLods': source_bounds, 'fbxLods': fbx_bounds, 'nativeEnvelopeConsumesLevel': 0,
      'nativeContract': 'GoldenSampleBuilder.Validation.cs:94-106 accumulates CurrentGeometryBounds only for level0.',
      'sourceSaved': False, 'fbxExported': False, 'exactDatablockMembershipRestored': True,
      'visualAccepted': False}))
