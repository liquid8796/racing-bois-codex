import bpy,bmesh,math,json
root=bpy.data.objects['RB_Golden_Apex_r4'];rows=[];bounds_min=[1e9]*3;bounds_max=[-1e9]*3
for o in root.children_recursive:
    if o.type!='MESH':continue
    mesh=o.data;mesh.calc_loop_triangles();bad=0;least=1e9
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices];squared=(o.matrix_world.to_3x3()@(b-a)).cross(o.matrix_world.to_3x3()@(c-a)).length_squared
        least=min(least,squared);bad+=squared<=1e-16
    for v in mesh.vertices:
        p=o.matrix_world@v.co
        for i,c in enumerate((p.x,p.z,p.y)):bounds_min[i]=min(bounds_min[i],c);bounds_max[i]=max(bounds_max[i],c)
    bm=bmesh.new();bm.from_mesh(mesh);boundary=sum(e.is_boundary for e in bm.edges);volume=bm.calc_volume(signed=True);bm.free()
    rows.append({'name':o.name,'triangles':len(mesh.loop_triangles),'physicalDegenerateTriangles':bad,'minimumCrossSquared':least,'boundaryEdges':boundary,'signedVolume':volume,'materials':[m.name for m in mesh.materials]})
print('APEX_R4_EDITABLE_AUDIT '+json.dumps({'objects':rows,'boundsMin':bounds_min,'boundsMax':bounds_max,'triangleCount':sum(r['triangles'] for r in rows),'physicalFailures':sum(r['physicalDegenerateTriangles'] for r in rows),'visualAccepted':False}))
