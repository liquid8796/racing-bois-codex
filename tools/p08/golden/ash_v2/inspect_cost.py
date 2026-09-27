import bpy,json
scene=bpy.context.scene;collection=bpy.data.collections['AshV2_Editable_Source'];collection.hide_viewport=False
bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get();counts=[]
for obj in collection.objects:
    if obj.type!='MESH':continue
    mesh=obj.evaluated_get(depsgraph).to_mesh();mesh.calc_loop_triangles()
    counts.append({'name':obj.name,'triangles':len(mesh.loop_triangles)})
    obj.evaluated_get(depsgraph).to_mesh_clear()
def triangle_count(row):return row['triangles']
counts.sort(key=triangle_count,reverse=True)
collection.hide_viewport=True
print(json.dumps({'largest_sources':counts[:20],'total':sum(v['triangles'] for v in counts)}))
