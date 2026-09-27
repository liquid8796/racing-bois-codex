import bpy,json
root=bpy.data.objects['RB_Golden_Garage'];rows=[]
for o in root.children_recursive:
    if o.type!='MESH':continue
    m=o.data;m.calc_loop_triangles()
    rows.append({'name':o.name,'vertices':len(m.vertices),'polygons':len(m.polygons),'triangles':len(m.loop_triangles),'loops':len(m.loops),'uvLayers':[u.name for u in m.uv_layers],'customNormals':m.has_custom_normals,'cornerNormals':len(m.corner_normals),'modifiers':[x.type for x in o.modifiers],'colorAttributes':[a.name for a in m.color_attributes]})
print('GARAGE_V7_BASELINE '+json.dumps({'source':bpy.data.filepath,'meshes':rows,'normalSetterAvailable':hasattr(bpy.types.Mesh,'normals_split_custom_set')}))
