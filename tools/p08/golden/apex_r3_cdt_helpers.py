def point_in_loop(point,loop):
    inside=False;x,y=point
    for i,a in enumerate(loop):
        b=loop[(i+1)%len(loop)]
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside

def edge_distance(point,a,b):
    delta=b-a;t=max(0,min(1,(point-a).dot(delta)/delta.length_squared));return (point-a-delta*t).length

def constrained_fairing_surface(outer,upper,lower,side):
    # CDT honours the boundary segments first; centroid filtering then removes
    # the exterior and the two holes. No Boolean ngons or self-touching loops.
    loops=[]
    for outline,steps in [(outer,5),(upper,5),(lower,4)]:
        loops.append([Vector((z,y)) for y,z in sample_poly(outline,steps)])
    vertices=[];edges=[]
    for loop in loops:
        base=len(vertices);vertices.extend(loop)
        edges.extend((base+i,base+(i+1)%len(loop)) for i in range(len(loop)))
    for iz in range(34):
        for iy in range(35):
            point=Vector((.017+iz*.024,.183+iy*.022))
            if not point_in_loop(point,loops[0]) or any(point_in_loop(point,loop) for loop in loops[1:]):continue
            if min(edge_distance(point,loop[i],loop[(i+1)%len(loop)]) for loop in loops for i in range(len(loop)))<.008:continue
            vertices.append(point)
    result=delaunay_2d_cdt(vertices,edges,[],0,.000001)
    points=result[0];faces=[]
    for face in result[2]:
        center=sum((points[i] for i in face),Vector((0,0)))/len(face)
        if not point_in_loop(center,loops[0]) or any(point_in_loop(center,loop) for loop in loops[1:]):continue
        # Single-precision boundary samples can yield numerical slivers whose
        # centres lie on the authored edge. They are not an interior region.
        if min(edge_distance(center,loop[i],loop[(i+1)%len(loop)]) for loop in loops for i in range(len(loop)))<.000008:continue
        aa,bb,cc=[points[i] for i in face]
        if abs((bb.x-aa.x)*(cc.y-aa.y)-(bb.y-aa.y)*(cc.x-aa.x))<1e-8:continue
        faces.append(face)
    used=sorted({i for face in faces for i in face});mapping={v:i for i,v in enumerate(used)}
    mapped=[]
    for i in used:
        z,y=points[i];mapped.append((side*fairing_x(y,z),y,z))
    mapped_faces=[[mapping[i] for i in face] for face in faces]
    incidence={}
    for face in mapped_faces:
        for i in range(len(face)):
            key=tuple(sorted((face[i],face[(i+1)%len(face)])));incidence[key]=incidence.get(key,0)+1
    boundary={}
    for edge,count in incidence.items():
        assert count<=2,'CDT edge has multiple faces'
        if count==1:
            for a,b in [edge,tuple(reversed(edge))]:boundary.setdefault(a,set()).add(b)
    assert all(len(neighbours)==2 for neighbours in boundary.values()),'CDT contains touching boundary cycles'
    visited=set();cycles=0
    for vertex in boundary:
        if vertex in visited:continue
        cycles+=1;todo=[vertex]
        while todo:
            vertex=todo.pop()
            if vertex in visited:continue
            visited.add(vertex);todo.extend(boundary[vertex]-visited)
    assert cycles==3,'Expected exactly outer boundary and two intake holes'
    return mapped,mapped_faces
