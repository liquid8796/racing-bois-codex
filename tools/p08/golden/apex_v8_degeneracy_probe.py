import bpy,json
rows=[]
collection=bpy.data.collections['Apex_V8_Editable_Components']
for obj in collection.objects:
    if obj.type!='MESH':continue
    data=obj.data;data.calc_loop_triangles()
    bad=[t for t in data.loop_triangles if t.area<1e-12]
    if bad:rows.append({'name':obj.name,'triangles':[{'verts':list(t.vertices),'points':[list(data.vertices[i].co) for i in t.vertices],'area':t.area} for t in bad]})
print('V8_ZERO_AREA_SOURCE '+json.dumps(rows))
