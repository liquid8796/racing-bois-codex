import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V5/' in bpy.data.filepath.replace('\\','/')
rows=[]
for o in bpy.data.objects['RB_Golden_Garage'].children_recursive:
    if o.type!='MESH':continue
    mesh=o.data;mesh.calc_loop_triangles();uv=mesh.uv_layers[0];bad_faces=set();triangles={}
    for tri in mesh.loop_triangles:
        triangles.setdefault(tri.polygon_index,[]).append(tuple(tri.loops))
        a,b,c=[uv.data[i].uv for i in tri.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<=1e-14:bad_faces.add(tri.polygon_index)
    if not bad_faces:continue
    before_verts=[tuple(v.co) for v in mesh.vertices];before_normals=[tuple(n.vector) for n in mesh.corner_normals]
    lightmap=[tuple(d.uv) for d in mesh.uv_layers['LightmapUV'].data] if mesh.uv_layers.get('LightmapUV') else None
    smallest=1
    for index in bad_faces:
        poly=mesh.polygons[index];material=mesh.materials[poly.material_index].name
        tile=2.0 if material=='Garage_Floor' else 2.2 if material in ['Garage_Concrete','Garage_NearConcrete'] else 1.0
        vertices={i:o.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co for i in poly.loop_indices}
        normal=(o.matrix_world.to_3x3().inverted().transposed()@poly.normal).normalized()
        candidates=[normal,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)),Vector((1,.37,.61)).normalized()]
        best_min=-1;best=None
        for n in candidates:
            tangent=n.orthogonal().normalized();bitangent=n.cross(tangent).normalized()
            projection={i:(p.dot(tangent)/tile,p.dot(bitangent)/tile) for i,p in vertices.items()}
            minimum=1
            for tri in triangles[index]:
                a,b,c=[projection[i] for i in tri]
                minimum=min(minimum,abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])))
            if minimum>best_min:best_min=minimum;best=projection
        assert best_min>1e-14,'No valid rigid metric projection for '+o.name
        for i,p in best.items():uv.data[i].uv=p
        for tri in triangles[index]:
            a,b,c=[uv.data[i].uv for i in tri];cross=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
            assert cross>1e-14,'Float UV storage collapsed '+o.name
            smallest=min(smallest,cross)
    assert before_verts==[tuple(v.co) for v in mesh.vertices]
    assert before_normals==[tuple(n.vector) for n in mesh.corner_normals]
    if lightmap is not None:assert lightmap==[tuple(d.uv) for d in mesh.uv_layers['LightmapUV'].data]
    rows.append({'name':o.name,'additionalFacesReprojected':len(bad_faces),'minimumRepairedUvCross':smallest,'normalsVerticesLightmapExact':True})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V5/RB_Golden_Garage.blend')
print('GARAGE_V5_TRIANGLE_REPAIR '+json.dumps({'objects':rows,'additionalFaces':sum(r['additionalFacesReprojected'] for r in rows),'geometryModified':False}))
