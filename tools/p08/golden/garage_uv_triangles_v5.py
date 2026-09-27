import bpy,json
rows=[]
for o in bpy.data.objects['RB_Golden_Garage'].children_recursive:
    if o.type!='MESH':continue
    mesh=o.data;mesh.calc_loop_triangles();minimum=1;bad=0;physical_bad=0;uv1_bad=0;uv1_min=1
    for triangle in mesh.loop_triangles:
        a,b,c=[mesh.uv_layers[0].data[i].uv for i in triangle.loops]
        ab=b-a;ac=c-a;cross=abs(ab.x*ac.y-ab.y*ac.x)
        minimum=min(minimum,cross);bad+=cross<=1e-14
        va,vb,vc=[o.matrix_world@mesh.vertices[i].co for i in triangle.vertices]
        physical_bad+=(vb-va).cross(vc-va).length_squared<=1e-16
        if mesh.uv_layers.get('LightmapUV'):
            a,b,c=[mesh.uv_layers['LightmapUV'].data[i].uv for i in triangle.loops]
            ab=b-a;ac=c-a;cross=abs(ab.x*ac.y-ab.y*ac.x)
            uv1_bad+=cross<=1e-14;uv1_min=min(uv1_min,cross)
    rows.append({'name':o.name,'triangles':len(mesh.loop_triangles),'primaryDegenerateTriangles':bad,'minimumPrimaryUvCross':minimum,
        'geometryDegenerateTriangles':physical_bad,'lightmapDegenerateTriangles':uv1_bad,'minimumLightmapUvCross':uv1_min})
print('GARAGE_V5_TRIANGLES '+json.dumps({'objects':rows,'primaryFailures':sum(r['primaryDegenerateTriangles'] for r in rows),
    'physicalFailures':sum(r['geometryDegenerateTriangles'] for r in rows),'lightmapFailures':sum(r['lightmapDegenerateTriangles'] for r in rows)}))
