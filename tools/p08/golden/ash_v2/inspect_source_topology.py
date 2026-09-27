import bpy,bmesh,json
rows=[]
for obj in bpy.data.collections['AshV2_Editable_Source'].objects:
    if obj.type!='MESH' or obj.name=='AshV2_HighResSource':continue
    if not any(m and m.name in ['AshV2_BootLeather','AshV2_TailoredClothing'] for m in obj.data.materials):continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(len(e.link_faces)>2 for e in bm.edges)
    bm.free();rows.append({'name':obj.name,'boundary':boundary,'shared':nonmanifold,'verts':len(obj.data.vertices)})
print(json.dumps(rows))
