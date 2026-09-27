import bpy,bmesh,json
rows=[]
root=bpy.data.objects['RB_Golden_Apex_r3']
for o in root.children_recursive:
    if o.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(o.data);bad=[e for e in bm.edges if not e.is_manifold]
    if bad:rows.append({'name':o.name,'boundary':sum(e.is_boundary for e in bad),'wire':sum(e.is_wire for e in bad),'multipleFaces':sum(len(e.link_faces)>2 for e in bad),'examples':[{'vertices':[list(v.co) for v in e.verts],'faces':len(e.link_faces)} for e in bad[:10]]})
    bm.free()
print('APEX_R3_TOPOLOGY '+json.dumps(rows))
