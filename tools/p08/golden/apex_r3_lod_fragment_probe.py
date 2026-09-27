import bpy,bmesh,json
o=bpy.data.objects['Apex_L2_Body'];bm=bmesh.new();bm.from_mesh(o.data);seen=set();rows=[]
for seed in bm.verts:
    if seed in seen:continue
    component=set();todo=[seed]
    while todo:
        v=todo.pop()
        if v in component:continue
        component.add(v);seen.add(v)
        for edge in v.link_edges:todo.append(edge.other_vert(v))
    edges={e for v in component for e in v.link_edges};faces={f for v in component for f in v.link_faces}
    if not any(not e.is_manifold for e in edges):continue
    first=next(iter(component));end=first
    for v in component:
        if (v.co-first.co).length_squared>(end.co-first.co).length_squared:end=v
    start=end
    for v in component:
        if (v.co-end.co).length_squared>(start.co-end.co).length_squared:start=v
    axis=(end.co-start.co).normalized();thickness=max((v.co-start.co).cross(axis).length for v in component);area=sum(f.calc_area() for f in faces)
    if len(faces)>6 or thickness>=.009 or area>=.003:rows.append({'vertices':len(component),'faces':len(faces),'radius':thickness,'area':area,'boundsMin':[min(v.co[i] for v in component) for i in range(3)],'boundsMax':[max(v.co[i] for v in component) for i in range(3)],'materials':list({o.data.materials[f.material_index].name for f in faces})})
bm.free();print('APEX_R3_NONTRIVIAL_LOD_FRAGMENTS '+json.dumps(rows))
