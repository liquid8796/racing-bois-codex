import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Ash_V6'];rig=bpy.data.objects['RB_P06_Rider_Rig']
source=[root,rig]+[bpy.data.objects['AshV6_L'+str(i)+'_Skin'] for i in range(3)]+[bpy.data.objects[n] for n in ['Forward','Ground_L','Ground_R']]
names={o:o.name for o in source};before=set(bpy.data.objects);before_mesh=set(bpy.data.meshes);before_actions=set(bpy.data.actions);created=[]
expected={}
for o in source:
    if o.type=='MESH':o.data.calc_loop_triangles();expected[o.name]=len(o.data.loop_triangles)
rows=[];actions=[]
try:
    for o,name in names.items():o.name='PrivateRoundtripSource_'+name
    bpy.ops.import_scene.fbx(filepath=ROOT+'_local/p08-ash-v6-staging/RB_Golden_Ash_V6.fbx',use_anim=True,use_image_search=False)
    created=list(set(bpy.data.objects)-before)
    for o in created:
        if o.type!='MESH':continue
        m=o.data;m.calc_loop_triangles();bad=0;uvbad=0
        for tri in m.loop_triangles:
            a,b,c=[o.matrix_world@m.vertices[i].co for i in tri.vertices]
            if (b-a).cross(c-a).length_squared<=1e-16:bad+=1
            a,b,c=[m.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
            if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvbad+=1
        rows.append({'name':o.name,'vertices':len(m.vertices),'triangles':len(m.loop_triangles),'sourceTriangles':expected[o.name],'physicalFailures':bad,'uvFailures':uvbad})
    actions=[a.name for a in set(bpy.data.actions)-before_actions]
    assert len(rows)==3 and all(r['physicalFailures']==0 and r['uvFailures']==0 for r in rows),'Roundtrip geometry/UV failure'
    assert all(r['triangles']==r['sourceTriangles'] for r in rows),'Roundtrip triangle count changed'
    assert any(a.endswith('RB_MenuHero') for a in actions),'Missing actual exported menu action'
finally:
    for o in created:bpy.data.objects.remove(o,do_unlink=True)
    for m in set(bpy.data.meshes)-before_mesh:
        if m.users==0:bpy.data.meshes.remove(m)
    for a in set(bpy.data.actions)-before_actions:bpy.data.actions.remove(a)
    for o,name in names.items():o.name=name
print('ASH_V6_ROUNDTRIP '+json.dumps({'passed':True,'meshes':rows,'actualImportedActions':actions,'sourceSaved':False,'nativeUnityStillRequired':True}))
