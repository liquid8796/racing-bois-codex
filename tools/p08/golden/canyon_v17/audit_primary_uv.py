"""Read-only float32 primary-UV audit on every Canyon source LOD."""
import bpy, json, math
from array import array

if not bpy.data.filepath.replace('\\', '/').endswith('/Canyon/V16/RB_Golden_Canyon.blend'):
    raise RuntimeError('Expected frozen V16 in the owned Blender session.')
rows = []
triangles = 0
def by_name(item):
    return item.name
for obj in sorted(bpy.data.objects['RB_Golden_Canyon'].children_recursive, key=by_name):
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    if not mesh.uv_layers.active:
        raise RuntimeError('Missing primary UV: ' + obj.name)
    values = array('f', [0]) * (len(mesh.loops) * 2)
    mesh.uv_layers.active.data.foreach_get('uv', values)
    bad = []
    minimum = None
    for triangle in mesh.loop_triangles:
        ia, ib, ic = [index * 2 for index in triangle.loops]
        cross = ((values[ib]-values[ia])*(values[ic+1]-values[ia+1])
                 - (values[ib+1]-values[ia+1])*(values[ic]-values[ia]))
        magnitude = abs(cross)
        minimum = magnitude if minimum is None else min(minimum, magnitude)
        if not math.isfinite(cross) or magnitude <= 1e-14:
            bad.append({'triangle': triangle.index, 'polygon': triangle.polygon_index,
                        'loops': list(triangle.loops), 'vertices': list(triangle.vertices),
                        'uv': [[values[index*2], values[index*2+1]] for index in triangle.loops],
                        'localVertices': [list(mesh.vertices[index].co) for index in triangle.vertices],
                        'cross': cross})
    triangles += len(mesh.loop_triangles)
    rows.append({'object': obj.name, 'triangles': len(mesh.loop_triangles), 'minimumAbsoluteCross': minimum,
                 'collapsedCount': len(bad), 'collapsed': bad})
print('CANYON_V16_PRIMARY_UV_AUDIT '+json.dumps({'source': bpy.data.filepath, 'thresholdStrictlyGreaterThan': 1e-14,
      'floatStorage': 'Blender primary UV float32; cross computed in double precision like current Unity validator',
      'meshCount': len(rows), 'triangles': triangles, 'collapsedCount': sum(row['collapsedCount'] for row in rows),
      'rows': rows, 'sourceChanged': False}))
