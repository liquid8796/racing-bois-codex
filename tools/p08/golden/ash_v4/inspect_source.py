import bpy,json
rig=bpy.data.objects['RB_P06_Rider_Rig'];mesh=bpy.data.objects['AshV3_L0_Skin']
rows=[]
for i,mat in enumerate(mesh.data.materials):
    faces=[p for p in mesh.data.polygons if p.material_index==i];ids=set(v for p in faces for v in p.vertices)
    points=[mesh.data.vertices[v].co for v in ids]
    rows.append({'index':i,'name':mat.name,'faces':len(faces),'vertices':len(ids),'min':[min(v[a] for v in points) for a in range(3)],'max':[max(v[a] for v in points) for a in range(3)]})
print('ASH_V4_INSPECT '+json.dumps({'source':bpy.data.filepath,'materials':rows,'uv':[u.name for u in mesh.data.uv_layers],
    'attributes':[a.name for a in mesh.data.attributes],'shapeKeys':[s.name for s in mesh.data.shape_keys.key_blocks],
    'sourceParts':[{'name':o.name,'verts':len(o.data.vertices),'materials':[m.name for m in o.data.materials],'hidden':o.hide_render} for o in bpy.data.collections['AshV2_Editable_Source'].objects if o.type=='MESH' and o.name in ['AshV2_Clothes','AshV2_Hair','AshV2_Body','AshV2_Brows']],
    'bones':[{'name':b.name,'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones if not 'Finger' in b.name],
    'actions':[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions],
    'helmetParts':[o.name for o in bpy.data.collections['AshV2_Editable_Source'].objects if any(v in o.name for v in ['Helmet','Goggle','Chin','StandCollar'])]}))
