"""Remove only measured collinear Boolean boundary vertices; do not weaken triangle checks."""
import bpy,bmesh,json
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_refined03.blend')
obj=bpy.data.objects['V2 copper teardrop tank'];data=obj.data;repairs=[]
for iteration in range(8):
    data.calc_loop_triangles();remove=set();maximum=0
    for triangle in data.loop_triangles:
        ids=list(triangle.vertices);points=[data.vertices[i].co for i in ids];a,b,c=points
        if (b-a).cross(c-a).length_squared>1e-16:continue
        pairs=[(0,1,2),(1,2,0),(2,0,1)];chosen=pairs[0];longest=0
        for i,j,k in pairs:
            length=(points[j]-points[i]).length_squared
            if length>longest:longest=length;chosen=(i,j,k)
        i,j,k=chosen;axis=points[j]-points[i];t=(points[k]-points[i]).dot(axis)/longest
        distance=(points[k]-(points[i]+axis*t)).length
        assert 0<t<1 and distance<=.00001,'Degenerate is not a redundant straight-edge sample'
        remove.add(ids[k]);maximum=max(maximum,distance)
    if not remove:break
    bm=bmesh.new();bm.from_mesh(data);bm.verts.ensure_lookup_table()
    bmesh.ops.dissolve_verts(bm,verts=[bm.verts[i] for i in sorted(remove)],use_face_split=False,use_boundary_tear=False)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
    repairs.append({'iteration':iteration,'removedCollinearVertices':len(remove),'maximumDistanceFromSurvivingEdgeMetres':maximum})
else:raise RuntimeError('Tank boundary repair did not converge')
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_refined04.blend',compress=True)
print('SPARK_V2_TANK_TOPOLOGY='+json.dumps({'source':bpy.data.filepath,'repairs':repairs,'visualAccepted':False,'exported':False}))
