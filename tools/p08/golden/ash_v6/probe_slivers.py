import bpy,json
o=bpy.data.objects['AshV6_L2_Equipment'];m=o.data;m.calc_loop_triangles();rows=[]
for tri in m.loop_triangles:
 a,b,c=[m.vertices[i].co for i in tri.vertices]
 if (b-a).cross(c-a).length_squared>1e-16:continue
 p=m.polygons[tri.polygon_index];points=[m.vertices[i].co for i in p.vertices]
 rows.append({'triangle':tri.index,'polygon':p.index,'points':[list(v) for v in points],'indices':list(p.vertices),'uv':[list(m.uv_layers[0].data[i].uv) for i in p.loop_indices],'quadAlternateCrossSquared':[(points[2]-points[1]).cross(points[3]-points[1]).length_squared,(points[3]-points[1]).cross(points[0]-points[1]).length_squared] if len(points)==4 else []})
print('ASH_V6_SLIVERS '+json.dumps(rows))
