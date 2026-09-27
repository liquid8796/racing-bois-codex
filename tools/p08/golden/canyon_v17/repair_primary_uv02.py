"""Repair only collapsed cap UVs; all geometry and material assignments stay exact."""
import bpy, json, math
from array import array
from mathutils import Vector

ROOT = 'D:/Project/Unity/racing-bois/'
if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V17/RB_Golden_Canyon_V17_01.blend'):
    raise RuntimeError('Expected separate V17 candidate01, never the frozen V16 file.')

def floats(collection, property_name, count):
    result = array('f', [0]) * count
    collection.foreach_get(property_name, result)
    return result

def integers(collection, property_name, count):
    result = array('i', [0]) * count
    collection.foreach_get(property_name, result)
    return result

def geometry_identity(obj):
    mesh = obj.data
    return (floats(mesh.vertices, 'co', len(mesh.vertices)*3),
            integers(mesh.loops, 'vertex_index', len(mesh.loops)),
            integers(mesh.polygons, 'loop_start', len(mesh.polygons)),
            integers(mesh.polygons, 'loop_total', len(mesh.polygons)),
            integers(mesh.polygons, 'material_index', len(mesh.polygons)),
            [list(row) for row in obj.matrix_world], [material.name for material in mesh.materials])

def collapsed(mesh):
    mesh.calc_loop_triangles()
    values = floats(mesh.uv_layers.active.data, 'uv', len(mesh.loops)*2)
    result = []
    minimum = None
    for triangle in mesh.loop_triangles:
        ia, ib, ic = [index*2 for index in triangle.loops]
        cross = ((values[ib]-values[ia])*(values[ic+1]-values[ia+1])
                 - (values[ib+1]-values[ia+1])*(values[ic]-values[ia]))
        magnitude = abs(cross)
        minimum = magnitude if minimum is None else min(minimum, magnitude)
        if not math.isfinite(cross) or magnitude <= 1e-14:
            result.append({'triangle': triangle.index, 'polygon': triangle.polygon_index,
                           'loops': list(triangle.loops), 'uv': [[values[index*2], values[index*2+1]] for index in triangle.loops],
                           'cross': cross})
    return result, minimum

rows = []
mesh_count = 0
total_triangles = 0
for obj in bpy.data.objects['RB_Golden_Canyon'].children_recursive:
    if obj.type != 'MESH':
        continue
    mesh_count += 1
    mesh = obj.data
    if mesh.users != 1:
        raise RuntimeError('Repair requires owned per-object mesh data: '+obj.name)
    before_geometry = geometry_identity(obj)
    bad, minimum_before = collapsed(mesh)
    total_triangles += len(mesh.loop_triangles)
    if bad and '_Guardrail_Beam_Tile' not in obj.name:
        raise RuntimeError('Unexpected non-guardrail collapsed UV: '+obj.name)
    changed = []
    for polygon_index in sorted(set(row['polygon'] for row in bad)):
        polygon = mesh.polygons[polygon_index]
        # V16 normalized source is triangulated. Requiring that here avoids
        # introducing a mapping that only works for one triangulation of an ngon.
        if polygon.loop_total != 3:
            raise RuntimeError('Unexpected cap polygon size: '+obj.name)
        loops = list(polygon.loop_indices)
        points = [obj.matrix_world @ mesh.vertices[mesh.loops[index].vertex_index].co for index in loops]
        edges = [points[1]-points[0], points[2]-points[1], points[0]-points[2]]
        # Compare lengths explicitly; no topology edits, quantization or epsilon
        # UV offsets are used to evade the validator.
        longest = 0
        for index in range(1, 3):
            if edges[index].length_squared > edges[longest].length_squared:
                longest = index
        axis_u = edges[longest].normalized()
        normal = (points[1]-points[0]).cross(points[2]-points[0]).normalized()
        if normal.length_squared < .99:
            raise RuntimeError('Collapsed physical cap triangle: '+obj.name)
        axis_v = normal.cross(axis_u).normalized()
        anchor = mesh.uv_layers.active.data[loops[0]].uv.copy()
        before_uv = [list(mesh.uv_layers.active.data[index].uv) for index in loops]
        # One UV repeat per physical metre on the formerly unwrapped solidify
        # cap; preserve the first original UV as its local material anchor.
        for index, point in zip(loops, points):
            relative = point-points[0]
            mesh.uv_layers.active.data[index].uv = (anchor.x+relative.dot(axis_u), anchor.y+relative.dot(axis_v))
        changed.append({'polygon': polygon_index, 'loops': loops, 'before': before_uv,
                        'after': [list(mesh.uv_layers.active.data[index].uv) for index in loops]})
    mesh.update()
    remaining, minimum_after = collapsed(mesh)
    if remaining:
        raise RuntimeError('Primary UV remains collapsed: '+obj.name)
    if before_geometry != geometry_identity(obj):
        raise RuntimeError('UV-only repair changed geometry/material identity: '+obj.name)
    rows.append({'object': obj.name, 'triangles': len(mesh.loop_triangles), 'collapsedBefore': len(bad),
                 'collapsedAfter': len(remaining), 'minimumAbsoluteCrossBefore': minimum_before,
                 'minimumAbsoluteCrossAfter': minimum_after, 'geometryAndMaterialsExactlyUnchanged': True,
                 'changedPolygons': changed})

destination = ROOT+'ArtSource/P08/Golden/Canyon/V17/RB_Golden_Canyon_V17_02.blend'
bpy.context.scene.render.filepath = ROOT+'docs/p08/golden/canyon/v17/candidate02-gameplay.png'
bpy.context.scene['v17_uv_repair'] = 'Guardrail cap projection only; exact vertex/topology/material equality, all primary UV cross > 1e-14.'
bpy.ops.wm.save_as_mainfile(filepath=destination, check_existing=False)
print('CANYON_V17_UV_REPAIR02 '+json.dumps({'source': destination, 'meshCount': mesh_count, 'triangles': total_triangles,
      'collapsedBefore': sum(row['collapsedBefore'] for row in rows), 'collapsedAfter': 0,
      'thresholdStrictlyGreaterThan': 1e-14, 'geometryAndMaterialsExactlyUnchanged': True,
      'floatStorage': 'float32 primary UV; double precision cross', 'mappingScaleRepeatsPerMetre': 1,
      'rows': rows, 'visualAccepted': False, 'exportedToAssets': False}))
