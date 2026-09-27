import bpy,bmesh,json
ROOT='D:/Project/Unity/racing-bois/';root=bpy.data.objects['RB_Golden_Apex_r5'];rows=[];failures=0
for o in root.children_recursive:
    if o.type!='MESH':continue
    o.data.calc_loop_triangles();bad=0
    for tri in o.data.loop_triangles:
        a,b,c=[o.data.vertices[i].co for i in tri.vertices]
        bad+=(o.matrix_world.to_3x3()@(b-a)).cross(o.matrix_world.to_3x3()@(c-a)).length_squared<=1e-16
        uv=o.data.uv_layers.active
        assert uv is not None,'Missing UV layer '+o.name
        p=[uv.data[i].uv for i in tri.loops]
        assert abs((p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x))*.5>=1e-12,'Degenerate UV triangle '+o.name
    bm=bmesh.new();bm.from_mesh(o.data);topology=sum(not e.is_manifold for e in bm.edges);bm.free()
    failures+=bad+topology;rows.append({'name':o.name,'triangles':len(o.data.loop_triangles),'physicalFailures':bad,'nonManifoldEdges':topology})
assert failures==0,'Fix source before export'
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children_recursive:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-apex-r5-staging/RB_Golden_Apex_r5.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
print('APEX_R5_STAGED_EXPORT '+json.dumps({'objects':rows,'visualAccepted':False,'path':'_local/p08-apex-r5-staging/RB_Golden_Apex_r5.fbx','assetsWritten':False}))
