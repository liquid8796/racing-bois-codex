import bpy,json,math
rows=[]
for level in range(3):
    o=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];m=o.data;m.calc_loop_triangles();bad={};uv_bad={};minimum=1
    for tri in m.loop_triangles:
        a,b,c=[m.vertices[i].co for i in tri.vertices];cross=(b-a).cross(c-a).length_squared;minimum=min(minimum,cross)
        role=m.materials[tri.material_index].name
        if cross<=1e-16:bad[role]=bad.get(role,0)+1
        a,b,c=[m.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uv_bad[role]=uv_bad.get(role,0)+1
    rows.append({'lod':level,'triangles':len(m.loop_triangles),'physicalBadByMaterial':bad,'uvBadByMaterial':uv_bad,'minimumPhysicalCrossSquared':minimum})
print('ASH_V4_GEOMETRY_AUDIT '+json.dumps(rows))
