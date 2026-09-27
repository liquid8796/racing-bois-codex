import bpy,json
rows=[]
for obj in bpy.data.collections['AshV5_Equipment'].objects:
    if obj.type!='MESH':continue
    mesh=obj.data;mesh.calc_loop_triangles();bad=[];uvbad=[];minimum=1
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices];cross=(b-a).cross(c-a).length_squared;minimum=min(minimum,cross)
        if cross<=1e-16:bad.append(tri.polygon_index)
        a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvbad.append(tri.polygon_index)
    if bad or uvbad:rows.append({'name':obj.name,'physicalBad':len(bad),'uvBad':len(uvbad),'minimum':minimum,'physicalFaces':sorted(set(bad))[:16],'uvFaces':sorted(set(uvbad))[:16]})
print('ASH_V5_GEOMETRY_PROBE '+json.dumps(rows))
