"""Import the staged FBX through Blender, audit actual exported float geometry, then remove only the probe objects."""
import bpy,json
source='D:/Project/Unity/racing-bois/_local/p08-canyon-v15-staging/RB_Golden_Canyon.fbx'
before=set(bpy.data.objects);meshes_before=set(bpy.data.meshes);materials_before=set(bpy.data.materials)
bpy.ops.import_scene.fbx(filepath=source,use_anim=False,use_image_search=False)
created=set(bpy.data.objects)-before
rows=[];total=0;bad_total=0;world_bad_total=0;minimum=float('inf');world_minimum=float('inf')
for obj in created:
    if obj.type!='MESH':continue
    mesh=obj.data;mesh.calc_loop_triangles();bad=0;world_bad=0;smallest=float('inf');world_smallest=float('inf')
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        squared=(b-a).cross(c-a).length_squared
        smallest=min(smallest,squared)
        if squared<=1e-16:bad+=1
        wa,wb,wc=[obj.matrix_world@p for p in (a,b,c)]
        world_squared=(wb-wa).cross(wc-wa).length_squared
        world_smallest=min(world_smallest,world_squared)
        if world_squared<=1e-16:world_bad+=1
    rows.append({'name':obj.name,'triangles':len(mesh.loop_triangles),'crossSquaredAtOrBelow1e16':bad,'minimumCrossSquared':smallest,'worldFailedTriangles':world_bad,'worldMinimumCrossSquared':world_smallest,'worldScale':list(obj.matrix_world.to_scale())})
    total+=len(mesh.loop_triangles);bad_total+=bad;world_bad_total+=world_bad;minimum=min(minimum,smallest);world_minimum=min(world_minimum,world_smallest)
for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
for mesh in set(bpy.data.meshes)-meshes_before:
    if mesh.users==0:bpy.data.meshes.remove(mesh)
for material in set(bpy.data.materials)-materials_before:
    if material.users==0:bpy.data.materials.remove(material)
print('CANYON_FBX_ROUNDTRIP '+json.dumps({'passed':bad_total==0 and world_bad_total==0,'gate':'crossSquared > 1e-16 in local and world metres','sceneMetresPerUnit':bpy.context.scene.unit_settings.scale_length,'triangles':total,'failedTriangles':bad_total,'worldFailedTriangles':world_bad_total,'minimumCrossSquared':minimum,'worldMinimumCrossSquared':world_minimum,'objects':rows,'scope':'Actual Blender FBX round-trip; native Unity import is still required.'}))
assert bad_total==0 and world_bad_total==0,'Exported geometry failed unchanged triangle gate'
