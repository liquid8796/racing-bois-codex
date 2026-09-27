import bpy,json,math
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';assert '/Ash/V5/' in bpy.data.filepath.replace('\\','/')
rows=[]
for obj in bpy.data.collections['AshV5_Equipment'].objects:
    if obj.type!='MESH':continue
    mesh=obj.data;mesh.calc_loop_triangles();bad=0;uvbad=set()
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.vertices[i].co for i in tri.vertices]
        bad+=(b-a).cross(c-a).length_squared<=1e-16
        a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvbad.add(tri.polygon_index)
    for index in uvbad:
        face=mesh.polygons[index];normal=face.normal;tangent=normal.orthogonal().normalized();across=normal.cross(tangent).normalized()
        coords=[mesh.vertices[mesh.loops[i].vertex_index].co for i in face.loop_indices];x=[p.dot(tangent) for p in coords];y=[p.dot(across) for p in coords]
        dx=max(x)-min(x);dy=max(y)-min(y)
        assert min(dx,dy)>1e-8
        for i,u,v in zip(face.loop_indices,x,y):mesh.uv_layers[0].data[i].uv=(.04+.92*(u-min(x))/dx,.04+.92*(v-min(y))/dy)
    failures=0
    for tri in mesh.loop_triangles:
        a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a;failures+=abs(ab.x*ac.y-ab.y*ac.x)<=1e-14
    assert bad==0 and failures==0,'New equipment geometry/UV failure '+obj.name
    assert all(len(v.groups)==1 and abs(v.groups[0].weight-1)<.00001 and obj.vertex_groups[v.groups[0].group].name=='RB_P06_Rider_L0_Head' for v in mesh.vertices)
    rows.append({'name':obj.name,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'degenerateGeometry':bad,'repairedUvFaces':len(uvbad),'remainingUvFailures':failures,'bone':'Head'})
clearance=[]
for level in range(3):
    shell=bpy.data.objects['AshV5_L'+str(level)+'_HelmetShell'].data
    tree=BVHTree.FromPolygons([v.co for v in shell.vertices],[tuple(p.vertices) for p in shell.polygons],all_triangles=False)
    band=bpy.data.objects['AshV5_L'+str(level)+'_ShellFittedGoggleBand'].data;values=[]
    for v in band.vertices:
        p,n,index,d=tree.find_nearest(v.co);values.append((v.co-p).dot(n))
    clearance.append({'lod':level,'bandMinimumSignedClearanceMetres':min(values),'bandMaximumSignedClearanceMetres':max(values),'samples':len(values)})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',compress=False)
print('ASH_V5_CANDIDATE_AUDIT '+json.dumps({'newEquipmentObjects':rows,'strapShellClearance':clearance,'rigBones':len(bpy.data.objects['RB_P06_Rider_Rig'].data.bones),
    'actions':[a.name for a in bpy.data.actions if a.name.startswith('RB_')],'notMergedOrExported':True,'nativeVerified':False,'visualAccepted':False}))
