"""Independent read-only geometry/UV audit through Blender MCP."""
import bpy
import bmesh
import json

def signed_area(poly):
    return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))*.5 if len(poly)>=3 else 0
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def intersection_area(first,second):
    output=list(first);clip=list(second)
    if signed_area(clip)<0:clip.reverse()
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
    return abs(signed_area(output))

root=bpy.data.objects.get('RB_Club')
if root is None:raise RuntimeError('Expected RB_Club scene')
reports=[]
for level in range(3):
    obj=bpy.data.objects.get('RB_Club_L'+str(level));mesh=obj.data;mesh.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    manifold=sum(1 for edge in bm.edges if not edge.is_manifold)
    winding=sum(1 for edge in bm.edges if edge.is_manifold and not edge.is_contiguous)
    degenerate=sum(1 for face in bm.faces if face.calc_area()<=1e-12)
    loose=sum(1 for vertex in bm.verts if not vertex.link_faces)
    unseen=set(vertex.index for vertex in bm.verts);components=[];duplicates=0
    while unseen:
        pending=[bm.verts[next(iter(unseen))]];indices=set();faces=set()
        while pending:
            at=pending.pop()
            if at.index in indices:continue
            indices.add(at.index);unseen.discard(at.index);faces.update(at.link_faces)
            pending.extend(edge.other_vert(at) for edge in at.link_edges if edge.other_vert(at).index not in indices)
        volume=0;positions=set()
        for face in faces:
            first=face.verts[0].co
            for i in range(1,len(face.verts)-1):volume+=first.dot(face.verts[i].co.cross(face.verts[i+1].co))/6
        for index in indices:
            point=tuple(round(value,8) for value in bm.verts[index].co)
            if point in positions:duplicates+=1
            positions.add(point)
        components.append({'vertices':len(indices),'signed_volume':volume})
    bm.free()
    uv=mesh.uv_layers.active;triangles=[];bad_uv=0;zero_uv=0
    for triangle in mesh.loop_triangles:
        points=[tuple(uv.data[index].uv) for index in triangle.loops]
        if any(value<0 or value>1 for point in points for value in point):bad_uv+=1
        if abs(signed_area(points))<1e-12:zero_uv+=1
        bounds=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
        triangles.append((points,bounds))
    overlaps=0;max_overlap=0
    for i,first in enumerate(triangles):
        a=first[1]
        for second in triangles[i+1:]:
            b=second[1]
            if a[2]<=b[0]+1e-12 or b[2]<=a[0]+1e-12 or a[3]<=b[1]+1e-12 or b[3]<=a[1]+1e-12:continue
            area=intersection_area(first[0],second[0])
            if area>1e-9:overlaps+=1;max_overlap=max(max_overlap,area)
    positions=[(-v.co.x,v.co.z,-v.co.y) for v in mesh.vertices]
    minimum=[min(p[axis] for p in positions) for axis in range(3)]
    maximum=[max(p[axis] for p in positions) for axis in range(3)]
    report={'lod':level,'triangles':len(mesh.loop_triangles),'vertices':len(mesh.vertices),
            'nonmanifold_edges':manifold,'inconsistent_winding_edges':winding,'degenerate_faces':degenerate,
            'loose_vertices':loose,'duplicate_vertices_within_components':duplicates,'components':components,
            'uv_out_of_bounds':bad_uv,'uv_degenerate_triangles':zero_uv,'uv_positive_area_overlap_pairs':overlaps,
            'max_overlap_area':max_overlap,'unity_min':minimum,'unity_max':maximum}
    report['passed']=all(value==0 for value in [manifold,winding,degenerate,loose,duplicates,bad_uv,zero_uv,overlaps]) and all(part['signed_volume']>1e-12 for part in components)
    reports.append(report)
print(json.dumps({'passed':all(report['passed'] for report in reports),'mode':'read-only independent mesh and exact triangle UV intersection audit',
                  'blender_version':bpy.app.version_string,'root_identity':list(root.location)==[0,0,0] and list(root.scale)==[1,1,1],
                  'lods':reports,'uv_reuse':'Same atlas reused between LODs only; no intra-LOD surface overlap'}))
