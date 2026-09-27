import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];m=obj.data;m.calc_loop_triangles();faces=set();uvfaces=set()
    for tri in m.loop_triangles:
        a,b,c=[m.vertices[i].co for i in tri.vertices]
        if (b-a).cross(c-a).length_squared<=1e-16:
            assert m.materials[tri.material_index].name=='AshV4_Forelock_Source','Unexpected non-hair geometry failure'
            faces.add(tri.polygon_index)
        a,b,c=[m.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
        if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvfaces.add(tri.polygon_index)
    maximum=0
    for face in faces:
        p=m.polygons[face];center=sum((m.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        for i in p.vertices:
            v=m.vertices[i];radial=v.co-center;delta=radial.normalized()*.000115-radial
            old=[key.data[i].co.copy() for key in m.shape_keys.key_blocks];v.co+=delta
            for key,co in zip(m.shape_keys.key_blocks,old):key.data[i].co=co+delta
            m.attributes['AshV4_RestMeters'].data[i].vector=v.co;maximum=max(maximum,delta.length)
    for index in uvfaces:
        p=m.polygons[index];t=p.normal.orthogonal().normalized();b=p.normal.cross(t).normalized()
        points=[m.vertices[m.loops[i].vertex_index].co for i in p.loop_indices]
        u=[v.dot(t) for v in points];v=[p.dot(b) for p in points];low_u=min(u);low_v=min(v);span_u=max(u)-low_u;span_v=max(v)-low_v
        assert min(span_u,span_v)>1e-8
        for i,a,c in zip(p.loop_indices,u,v):m.uv_layers[0].data[i].uv=(.04+.92*(a-low_u)/span_u,.04+.92*(c-low_v)/span_v)
    m.update();rows.append({'lod':level,'hairEndCapsRepaired':len(faces),'maximumTipRadiusDeltaMetres':maximum,'uvSidewallFacesRepaired':len(uvfaces),'constantMicroSurfaceTilingIntentional':True})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_MICRO_REPAIR '+json.dumps(rows))
