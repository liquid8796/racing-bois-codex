import bpy,json
obj=bpy.data.objects['AshV2_L0_Skin'];obj.data.calc_loop_triangles();groups={}
for tri in obj.data.loop_triangles:
    a,b,c=[obj.data.vertices[i].co for i in tri.vertices]
    if (b-a).cross(c-a).length<1e-12:
        name=obj.data.materials[tri.material_index].name
        if name not in groups:groups[name]={'count':0,'sample':[]}
        groups[name]['count']+=1
        if len(groups[name]['sample'])<2:groups[name]['sample'].append([list(a),list(b),list(c)])
print(json.dumps(groups))
