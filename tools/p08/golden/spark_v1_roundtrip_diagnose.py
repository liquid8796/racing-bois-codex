"""Observe raw versus evaluated counts before changing an export policy."""
import bpy
import json
root = bpy.data.objects['RB_Golden_Spark_v1']
rows = []
for obj in root.children_recursive:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    mesh.calc_loop_triangles()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    data.calc_loop_triangles()
    polygon_sides = {}
    for p in mesh.polygons:
        key = str(len(p.vertices))
        polygon_sides[key] = polygon_sides.get(key, 0) + 1
    rows.append({'name': obj.name, 'rawTriangles': len(mesh.loop_triangles),
                 'evaluatedTriangles': len(data.loop_triangles), 'polygons': len(mesh.polygons),
                 'polygonSides': polygon_sides,
                 'modifiers': [{'name': m.name, 'type': m.type, 'viewport': m.show_viewport, 'render': m.show_render} for m in obj.modifiers]})
    evaluated.to_mesh_clear()
print('SPARK_EVALUATED_DIAGNOSIS=' + json.dumps(rows))
