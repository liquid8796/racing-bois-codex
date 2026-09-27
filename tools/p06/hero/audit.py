"""Independent read-only topology, UV channels, weights and animation audit."""
import bpy,bmesh,json,math
def area(poly):return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))*.5)
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def overlap(first,second):
    output=list(first);clip=list(second)
    if cross(clip[0],clip[1],clip[2])<0:clip.reverse()
    for i in range(3):
        a,b=clip[i],clip[(i+1)%3];current=output;output=[]
        if not current:break
        previous=current[-1];dp=cross(a,b,previous)
        for point in current:
            dc=cross(a,b,point)
            if (dp>=-1e-12)!=(dc>=-1e-12) and abs(dp-dc)>1e-20:
                t=dp/(dp-dc);output.append((previous[0]+t*(point[0]-previous[0]),previous[1]+t*(point[1]-previous[1])))
            if dc>=-1e-12:output.append(point)
            previous=point;dp=dc
    return area(output) if len(output)>=3 else 0
def audit(root):
    reports=[]
    for obj in root.children_recursive:
        if obj.type!='MESH':continue
        mesh=obj.data;mesh.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
        report={'name':obj.name,'triangles':len(mesh.loop_triangles),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'winding':sum(e.is_manifold and not e.is_contiguous for e in bm.edges),'degenerate':sum(f.calc_area()<1e-12 for f in bm.faces),'loose':sum(not v.link_faces for v in bm.verts)}
        components={};unseen=set(v.index for v in bm.verts);cid=0;volumes=[]
        while unseen:
            pending=[bm.verts[next(iter(unseen))]];faces=set();indices=set()
            while pending:
                v=pending.pop()
                if v.index in indices:continue
                indices.add(v.index);unseen.discard(v.index);components[v.index]=cid;faces.update(v.link_faces);pending.extend(e.other_vert(v) for e in v.link_edges if e.other_vert(v).index not in indices)
            volume=0
            for f in faces:
                for k in range(1,len(f.verts)-1):volume+=f.verts[0].co.dot(f.verts[k].co.cross(f.verts[k+1].co))/6
            volumes.append(volume);cid+=1
        report['closedComponents']=cid;report['nonpositiveVolumes']=sum(v<=1e-13 for v in volumes);bm.free()
        uv=mesh.uv_layers.active;report['uvOutOfBounds']=0;report['uvZeroArea']=0;report['unintendedUvOverlap']=0;bins={}
        for triangle in mesh.loop_triangles:
            coords=[tuple(uv.data[i].uv) for i in triangle.loops]
            if any(v<0 or v>1 for p in coords for v in p):report['uvOutOfBounds']+=1
            if area(coords)<1e-12:report['uvZeroArea']+=1
            bounds=(min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords));bins.setdefault(components[triangle.vertices[0]],[]).append((coords,bounds))
        for triangles in bins.values():
            for i,first in enumerate(triangles):
                a=first[1]
                for second in triangles[i+1:]:
                    b=second[1]
                    if a[2]<=b[0]+1e-10 or b[2]<=a[0]+1e-10 or a[3]<=b[1]+1e-10 or b[3]<=a[1]+1e-10:continue
                    if overlap(first[0],second[0])>1e-9:report['unintendedUvOverlap']+=1
        if obj.vertex_groups:
            report['unweightedVertices']=sum(sum(g.weight for g in v.groups)<.999 for v in mesh.vertices)
            report['maxBoneInfluences']=max(len([g for g in v.groups if g.weight>1e-6]) for v in mesh.vertices)
        report['passed']=all(report[k]==0 for k in ['nonmanifold','winding','degenerate','loose','nonpositiveVolumes','uvOutOfBounds','uvZeroArea','unintendedUvOverlap']) and report.get('unweightedVertices',0)==0
        reports.append(report)
    return {'root':root.name,'passed':all(r['passed'] for r in reports),'meshes':reports,'uvPolicy':'Material atlas tile reuse between disconnected authored surface components and LODs is intentional. Exact positive triangle intersections are checked within each connected surface component.'}
print(json.dumps(audit(bpy.data.objects.get('RB_P06_Rider') or bpy.data.objects.get('RB_P06_Motorcycle'))))
