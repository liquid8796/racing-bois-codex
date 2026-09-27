import bpy,bmesh,math,json
root=bpy.data.objects['RB_Golden_Garage'];rows=[];lo=[float('inf')]*3;hi=[-float('inf')]*3;totals=[0,0,0]
for o in root.children_recursive:
    if o.type!='MESH':continue
    mesh=o.data;mesh.calc_loop_triangles();bad=0;minimum=float('inf')
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        value=(o.matrix_world.to_3x3()@(b-a)).cross(o.matrix_world.to_3x3()@(c-a)).length_squared
        minimum=min(minimum,value);bad+=value<=1e-16
    bm=bmesh.new();bm.from_mesh(mesh);boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold for e in bm.edges);bm.free()
    uv=mesh.uv_layers.active
    invalid_uv=sum(not all(math.isfinite(c) for c in x.uv) for x in uv.data) if uv else -1
    nonfinite=0
    for v in mesh.vertices:
        p=o.matrix_world@v.co;xyz=(p.x,p.z,p.y);nonfinite+=not all(math.isfinite(c) for c in xyz)
        for i in range(3):lo[i]=min(lo[i],xyz[i]);hi[i]=max(hi[i],xyz[i])
    level=int(o.name.split('_L')[1][0]);totals[level]+=len(mesh.loop_triangles)
    rows.append({'name':o.name,'triangles':len(mesh.loop_triangles),'physicalDegenerates':bad,'minimumCrossSquared':minimum,'boundaryEdges':boundary,'nonManifoldEdges':nonmanifold,'invalidUvs':invalid_uv,'nonfinite':nonfinite,'materials':[m.name for m in mesh.materials]})
print('GARAGE_SOURCE_AUDIT '+json.dumps({'objects':rows,'boundsMin':lo,'boundsMax':hi,'boundsSize':[hi[i]-lo[i] for i in range(3)],'lodTriangles':totals,'geometryChecksPassed':all(r['physicalDegenerates']==r['invalidUvs']==r['nonfinite']==r['boundaryEdges']==r['nonManifoldEdges']==0 for r in rows),'visualAccepted':False}))
