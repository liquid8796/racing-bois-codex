import bpy,json
obj=bpy.data.objects['R3 Curved main fairing with through intake 1'];mesh=obj.data;mesh.calc_loop_triangles();rows=[]
for tri in mesh.loop_triangles:
    a,b,c=[mesh.vertices[i].co for i in tri.vertices]
    if (b-a).cross(c-a).length_squared<=1e-16:
        rows.append({'indices':list(tri.vertices),'polygon':tri.polygon_index,'polygonVertices':list(mesh.polygons[tri.polygon_index].vertices),'positions':[list(p) for p in [a,b,c]],'edgeLengths':[(a-b).length,(b-c).length,(c-a).length]})
print('R3_BOOLEAN_DEGENERACY '+json.dumps(rows))
