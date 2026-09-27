import bpy,math,json
root=bpy.data.objects['RB_Golden_MenuEnvironment'];rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    mesh=obj.data;mesh.calc_loop_triangles();bad=0;uvbad=0;minimum=1;uvminimum=1;upmin=1;upavg=0
    uv=mesh.uv_layers.active
    assert uv and len(uv.data)==len(mesh.loops),obj.name
    assert all(math.isfinite(c) for v in mesh.vertices for c in v.co),obj.name
    for tri in mesh.loop_triangles:
        a,b,c=[obj.matrix_world@mesh.vertices[index].co for index in tri.vertices]
        cross=(b-a).cross(c-a);area=cross.length_squared;minimum=min(minimum,area);bad+=area<=1e-16
        if area>0:up=cross.normalized().z;upmin=min(upmin,up);upavg+=up
        u,v,w=[tuple(uv.data[index].uv) for index in tri.loops]
        crossuv=abs((v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0]));uvminimum=min(uvminimum,crossuv);uvbad+=crossuv<=1e-14
    rows.append({'name':obj.name,'triangles':len(mesh.loop_triangles),'physicalFailures':bad,'uvFailures':uvbad,'minPhysicalCrossSquared':minimum,'minUvCross':uvminimum,'averageNormalUp':upavg/len(mesh.loop_triangles),'minimumNormalUp':upmin})
surface_rows=[r for r in rows if any(token in r['name'] for token in ['_Road_','_Shoulder_','_WhitePaint_','_YellowPaint_','_Pullout','_EdgeGravel','_NearValley','_FarValley'])]
print('MENU_GEOMETRY_AUDIT '+json.dumps({'objects':rows,'meshes':len(rows),'triangles':sum(r['triangles'] for r in rows),'physicalFailures':sum(r['physicalFailures'] for r in rows),'uvFailures':sum(r['uvFailures'] for r in rows),'surfaceFrontFaceFailures':sum(r['minimumNormalUp']<=0 for r in surface_rows),'visualAccepted':False}))
