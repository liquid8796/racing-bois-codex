import bpy,bmesh,json
obj=bpy.data.objects['AshV2_L0_Skin'];bm=bmesh.new();bm.from_mesh(obj.data);groups={}
for edge in bm.edges:
    if edge.is_boundary or len(edge.link_faces)>2:
        names=sorted(set(obj.data.materials[f.material_index].name for f in edge.link_faces));key='|'.join(names)
        if key not in groups:groups[key]={'boundary':0,'shared_nonmanifold':0,'samples':[]}
        if edge.is_boundary:groups[key]['boundary']+=1
        else:groups[key]['shared_nonmanifold']+=1
        if len(groups[key]['samples'])<3:groups[key]['samples'].append([list(v.co) for v in edge.verts])
bm.free();print(json.dumps(groups))
