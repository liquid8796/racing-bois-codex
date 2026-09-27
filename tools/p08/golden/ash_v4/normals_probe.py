import bpy,json
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];mesh=obj.data
    rows.append({'lod':level,'hasCustomNormals':mesh.has_custom_normals,'smoothFaces':sum(p.use_smooth for p in mesh.polygons),
        'modifiers':[m.type for m in obj.modifiers],'attributes':[a.name for a in mesh.attributes]})
print('ASH_V4_NORMALS '+json.dumps(rows))
