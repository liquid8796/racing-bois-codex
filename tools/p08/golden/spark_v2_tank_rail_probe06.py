import bpy,json
from mathutils.bvhtree import BVHTree
def tree(obj):return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices) for f in obj.data.polygons],all_triangles=False,epsilon=0)
tank=bpy.data.objects['V2 continuous tank surface06'];rail=bpy.data.objects['Upper black frame rail 1']
overlaps=tree(tank).overlap(tree(rail));polygons=sorted({pair[0] for pair in overlaps});rows=[]
for index in polygons:
    points=[tank.matrix_world@tank.data.vertices[i].co for i in tank.data.polygons[index].vertices]
    rows.append({'polygon':index,'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]})
print('SPARK_TANK_RAIL_CONTACTS='+json.dumps(rows))
