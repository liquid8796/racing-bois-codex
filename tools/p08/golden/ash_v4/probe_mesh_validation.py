import bpy,json
rows=[]
for level in range(3):
    original=bpy.data.objects['AshV4_L'+str(level)+'_Skin'].data;mesh=original.copy();mesh.calc_loop_triangles()
    before=(len(mesh.vertices),len(mesh.polygons),len(mesh.loop_triangles));changed=mesh.validate(verbose=False,clean_customdata=False);mesh.calc_loop_triangles()
    after=(len(mesh.vertices),len(mesh.polygons),len(mesh.loop_triangles));rows.append({'lod':level,'copyValidationChanged':changed,'before':before,'after':after})
    bpy.data.meshes.remove(mesh)
print('ASH_V4_MESH_VALIDATE_COPY '+json.dumps(rows))
