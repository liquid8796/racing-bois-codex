import bpy,json
rows=[]
for level in range(3):
    mesh=bpy.data.objects['AshV4_L'+str(level)+'_Skin'].data
    ids=set(v for p in mesh.polygons if mesh.materials[p.material_index].name=='AshV4_TailoredLeather_Source' for v in p.vertices)
    adjacent={i:set() for i in ids}
    for edge in mesh.edges:
        a,b=edge.vertices
        if a in ids and b in ids:adjacent[a].add(b);adjacent[b].add(a)
    todo=set(ids);components=[]
    while todo:
        first=todo.pop();seen={first};queue=[first]
        while queue:
            current=queue.pop()
            for nxt in adjacent[current]:
                if nxt in todo:todo.remove(nxt);seen.add(nxt);queue.append(nxt)
        points=[mesh.vertices[i].co for i in seen]
        components.append({'vertices':len(seen),'min':[min(p[a] for p in points) for a in range(3)],'max':[max(p[a] for p in points) for a in range(3)]})
    rows.append({'lod':level,'components':components})
print('ASH_GARMENT_COMPONENTS '+json.dumps(rows))
