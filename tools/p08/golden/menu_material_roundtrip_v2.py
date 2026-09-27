import bpy,json
ROOT='D:/Project/Unity/racing-bois/';root=bpy.data.objects['RB_Golden_MenuEnvironment'];expected={}
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    mesh=obj.data;mesh.calc_loop_triangles()
    names=[slot.material.name if slot.material else None for slot in obj.material_slots]
    assert names and all(names),obj.name
    assert all(0<=p.material_index<len(names) for p in mesh.polygons),obj.name
    expected[obj.name]={'slots':names,'indices':[p.material_index for p in mesh.polygons],'triangles':len(mesh.loop_triangles)}
original_names={o:o.name for o in [root]+list(root.children_recursive)};before=set(bpy.data.objects);mesh_before=set(bpy.data.meshes);created=[];rows=[]
def same_name(actual,wanted):
    if actual==wanted:return True
    suffix=actual[len(wanted)+1:] if actual.startswith(wanted+'.') else ''
    return len(suffix)>=3 and suffix.isdigit()
try:
    for obj,name in original_names.items():obj.name='SourceV2_'+name
    bpy.ops.import_scene.fbx(filepath=ROOT+'_local/p08-menu-environment-v2-staging/RB_Golden_MenuEnvironment.fbx',use_anim=False,use_image_search=False)
    created=list(set(bpy.data.objects)-before);imported=[o for o in created if o.type=='MESH']
    assert {o.name for o in imported}==set(expected),'Renderer coverage changed'
    for obj in imported:
        mesh=obj.data;mesh.calc_loop_triangles();wanted=expected[obj.name]
        names=[slot.material.name if slot.material else None for slot in obj.material_slots]
        slot_bad=abs(len(names)-len(wanted['slots']))
        slot_bad+=sum(name is None or not same_name(name,target) for name,target in zip(names,wanted['slots']))
        indices=[p.material_index for p in mesh.polygons]
        index_bad=sum(a!=b for a,b in zip(indices,wanted['indices']))+abs(len(indices)-len(wanted['indices']))
        out_of_range=sum(not(0<=i<len(names)) for i in indices)
        physical_bad=uv_bad=0;uv=mesh.uv_layers.active
        assert uv is not None and len(uv.data)==len(mesh.loops),obj.name
        for tri in mesh.loop_triangles:
            a,b,c=[obj.matrix_world@mesh.vertices[i].co for i in tri.vertices]
            physical_bad+=(b-a).cross(c-a).length_squared<=1e-16
            u,v,w=[tuple(uv.data[i].uv) for i in tri.loops]
            uv_bad+=abs((v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0]))<=1e-14
        rows.append({'name':obj.name,'expectedSlots':wanted['slots'],'actualSlots':names,'slotFailures':slot_bad,'polygonIndexFailures':index_bad,
                     'outOfRangeIndices':out_of_range,'triangles':len(mesh.loop_triangles),'triangleCountMatches':len(mesh.loop_triangles)==wanted['triangles'],
                     'physicalFailures':physical_bad,'uvFailures':uv_bad})
finally:
    for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
    for mesh in set(bpy.data.meshes)-mesh_before:
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    for obj,name in original_names.items():obj.name=name
passed=all(r['slotFailures']==r['polygonIndexFailures']==r['outOfRangeIndices']==r['physicalFailures']==r['uvFailures']==0 and r['triangleCountMatches'] for r in rows)
print('MENU_V2_MATERIAL_ROUNDTRIP '+json.dumps({'passed':passed,'objects':rows,'meshes':len(rows),'triangles':sum(r['triangles'] for r in rows),
    'slotFailures':sum(r['slotFailures'] for r in rows),'polygonIndexFailures':sum(r['polygonIndexFailures'] for r in rows),'physicalFailures':sum(r['physicalFailures'] for r in rows),'uvFailures':sum(r['uvFailures'] for r in rows),'nativeUnityVerified':False}))
assert passed,'Full slot/polygon/geometry roundtrip failed'
