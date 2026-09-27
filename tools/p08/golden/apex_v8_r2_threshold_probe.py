import bpy,json
root=bpy.data.objects['RB_Golden_Apex_v8_r2']
rows=[];count=0;bad=0;minimum=1.0
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    data=obj.data;data.calc_loop_triangles();small=[]
    for tri in data.loop_triangles:
        p=[obj.matrix_world@data.vertices[v].co for v in tri.vertices]
        cross_sq=(p[1]-p[0]).cross(p[2]-p[0]).length_squared
        minimum=min(minimum,cross_sq);count+=1
        if cross_sq<=1e-16:small.append(cross_sq);bad+=1
    if small:rows.append({'name':obj.name,'bad':len(small),'minCrossSq':min(small)})
print('V8_R2_UNITY_THRESHOLD '+json.dumps({'triangles':count,'badTriangles':bad,'minimumCrossSq':minimum,'threshold':1e-16,'components':rows}))
