import bpy,json
rows=[]
for name in ['Canyon_L2_Talus','Canyon_L2_Reflectors_Tile03','Canyon_L1_Guardrail_Posts_Tile05']:
    obj=bpy.data.objects[name];mesh=obj.data;mesh.calc_loop_triangles();seen=set();duplicates=0
    for tri in mesh.loop_triangles:
        key=tuple(sorted(tri.vertices))
        if key in seen:duplicates+=1
        seen.add(key)
    copy=mesh.copy();changed=copy.validate(clean_customdata=False);copy.calc_loop_triangles()
    rows.append({'name':name,'sourceTriangles':len(mesh.loop_triangles),'duplicateTriangleVertexSets':duplicates,'modifiers':[m.type for m in obj.modifiers],'validationChanged':changed,'afterValidationTriangles':len(copy.loop_triangles)})
    bpy.data.meshes.remove(copy)
print('CANYON_EXPORT_COUNT_PROBE '+json.dumps(rows))
