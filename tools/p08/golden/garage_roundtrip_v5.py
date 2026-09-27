import bpy,bmesh,json
root=bpy.data.objects['RB_Golden_Garage']
source_objects=[obj for obj in root.children_recursive if obj.type=='MESH']
expected={}
for obj in source_objects:
    obj.data.calc_loop_triangles();expected[obj.name]=len(obj.data.loop_triangles)
original_names={obj:obj.name for obj in [root]+list(root.children_recursive)}
before=set(bpy.data.objects);meshes_before=set(bpy.data.meshes)
created=[];rows=[];failures=0;uvFailures=0;lightmapFailures=0;minimum=float('inf');total=0
try:
    for obj,name in original_names.items():obj.name='GarageSourceV5_'+name
    bpy.ops.import_scene.fbx(filepath='D:/Project/Unity/racing-bois/_local/p08-garage-v5-staging/RB_Golden_Garage.fbx',use_anim=False,use_image_search=False)
    created=list(set(bpy.data.objects)-before)
    imported=[obj for obj in created if obj.type=='MESH']
    assert {obj.name for obj in imported}==set(expected),'Export renderer coverage changed'
    for obj in imported:
        mesh=obj.data;mesh.calc_loop_triangles();assert len(mesh.loop_triangles)==expected[obj.name],'Triangle count changed '+obj.name
        smallest=float('inf');bad=0;badUv=0;badLightmap=0
        assert mesh.uv_layers[0].name=='UV0_MetricTile'
        if '_L0_' in obj.name:assert len(mesh.uv_layers)==2 and mesh.uv_layers[1].name=='LightmapUV'
        else:assert len(mesh.uv_layers)==1
        for tri in mesh.loop_triangles:
            a,b,c=[obj.matrix_world@mesh.vertices[i].co for i in tri.vertices]
            cross=(b-a).cross(c-a).length_squared;smallest=min(smallest,cross)
            if cross<=1e-16:bad+=1
            for layerIndex,layer in enumerate(mesh.uv_layers):
                a,b,c=[layer.data[i].uv for i in tri.loops];ab=b-a;ac=c-a
                if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:
                    if layerIndex==0:badUv+=1
                    else:badLightmap+=1
        rows.append({'name':obj.name,'sourceAndExportTriangles':len(mesh.loop_triangles),'physicalAreaFailures':bad,'primaryUvFailures':badUv,'lightmapUvFailures':badLightmap,'minimumWorldCrossSquared':smallest})
        total+=len(mesh.loop_triangles);failures+=bad;uvFailures+=badUv;lightmapFailures+=badLightmap;minimum=min(minimum,smallest)
finally:
    for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
    for mesh in set(bpy.data.meshes)-meshes_before:
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    for obj,name in original_names.items():obj.name=name
print('GARAGE_V5_ROUNDTRIP '+json.dumps({'passed':failures==0 and uvFailures==0 and lightmapFailures==0,'exactRendererCoverage':True,'exactPerMeshTriangleCounts':True,'triangles':total,'physicalAreaFailures':failures,'primaryUvFailures':uvFailures,'lightmapUvFailures':lightmapFailures,'minimumWorldCrossSquared':minimum,'objects':rows}))
assert failures==0 and uvFailures==0 and lightmapFailures==0,'Physical/UV gate failed'



