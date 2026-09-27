import bpy,bmesh,math,json
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
scene=bpy.context.scene
root=bpy.data.objects['RB_Golden_Spark_v1']
def mesh_object(name, vertices, faces, material, group='Body', smooth=True):
    vertices = [Vector(v) for v in vertices]
    final_faces = []
    for face in faces:
        if len(face) <= 4:
            final_faces.append(face)
        else:
            index = len(vertices)
            vertices.append(sum((vertices[i] for i in face), Vector()) / len(face))
            final_faces.extend((index, face[i], face[(i + 1) % len(face)]) for i in range(len(face)))
    data = bpy.data.meshes.new(name + ' mesh')
    data.from_pydata(vertices, [], final_faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.parent = root
    obj['asset_group'] = group
    data.materials.append(bpy.data.materials[material])
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    uv = data.uv_layers.new(name='UV0_SurfaceMetres')
    for face in data.polygons:
        face.use_smooth = smooth
        axis = 0 if abs(face.normal.x) >= max(abs(face.normal.y), abs(face.normal.z)) else 1 if abs(face.normal.y) >= abs(face.normal.z) else 2
        axes = [i for i in range(3) if i != axis]
        for loop in face.loop_indices:
            p = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (p[axes[0]] * 2, p[axes[1]] * 2)
    return obj

def catmull(points, steps=5):
    result = []
    for i in range(len(points) - 1):
        a, b, c, d = [Vector(points[k]) for k in [max(0, i - 1), i, i + 1, min(len(points) - 1, i + 2)]]
        for j in range(steps):
            t = j / steps
            result.append(.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t))
    result.append(Vector(points[-1]))
    return result

def tube(name, points, radius, material, group='Body', sides=14, curved=False):
    points = catmull(points, 5) if curved else [Vector(p) for p in points]
    vertices = []
    faces = []
    for i, point in enumerate(points):
        axis = (points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]).normalized()
        helper = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
        u = axis.cross(helper).normalized()
        v = axis.cross(u).normalized()
        for j in range(sides):
            angle = math.tau * j / sides
            vertices.append(point + radius * (u * math.cos(angle) + v * math.sin(angle)))
        if i:
            faces.extend(((i - 1) * sides + j, (i - 1) * sides + (j + 1) % sides, i * sides + (j + 1) % sides, i * sides + j) for j in range(sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + j for j in range(sides))])
    return mesh_object(name, vertices, faces, material, group)

def lathe(name, center, axis, profile, material, group='Body', segments=40, closed=False):
    center, axis = Vector(center), Vector(axis).normalized()
    helper = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
    u = axis.cross(helper).normalized()
    v = axis.cross(u).normalized()
    vertices = []
    faces = []
    for k, (distance, radius) in enumerate(profile):
        for j in range(segments):
            angle = math.tau * j / segments
            vertices.append(center + axis * distance + radius * (u * math.cos(angle) + v * math.sin(angle)))
        if k:
            faces.extend(((k - 1) * segments + j, (k - 1) * segments + (j + 1) % segments, k * segments + (j + 1) % segments, k * segments + j) for j in range(segments))
    if closed:
        k = len(profile) - 1
        faces.extend((k * segments + j, k * segments + (j + 1) % segments, (j + 1) % segments, j) for j in range(segments))
    else:
        faces.extend([tuple(reversed(range(segments))), tuple((len(profile) - 1) * segments + j for j in range(segments))])
    return mesh_object(name, vertices, faces, material, group)

def box(name, center, size, material, bevel=.004, group='Body'):
    center = Vector(center)
    x, y, z = [v / 2 for v in size]
    vertices = [center + Vector((a * x, b * y, c * z)) for a, b, c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    obj = mesh_object(name, vertices, faces, material, group, False)
    if bevel:
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new('Manufactured edge radius', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj

def torus(name, center, major, minor, material, group='Body', segments=80, sides=8):
    center = Vector(center)
    vertices = []
    faces = []
    for i in range(segments):
        a = math.tau * i / segments
        radial = Vector((0, math.sin(a), math.cos(a)))
        for j in range(sides):
            b = math.tau * j / sides
            vertices.append(center + radial * (major + minor * math.cos(b)) + Vector((minor * math.sin(b), 0, 0)))
            faces.append((i*sides+j, ((i+1)%segments)*sides+j, ((i+1)%segments)*sides+(j+1)%sides, i*sides+(j+1)%sides))
    return mesh_object(name, vertices, faces, material, group)

def loft(name, sections, profile, material, smooth=True):
    rings = catmull(sections, 5)
    vertices = []
    faces = []
    n = len(profile)
    for k, (y, bottom, top, width) in enumerate(rings):
        vertices.extend((x*width, y, bottom+z*(top-bottom)) for x, z in profile)
        if k:
            faces.extend(((k-1)*n+j, (k-1)*n+(j+1)%n, k*n+(j+1)%n, k*n+j) for j in range(n))
    faces.extend([tuple(reversed(range(n))), tuple((len(rings)-1)*n+j for j in range(n))])
    return mesh_object(name, vertices, faces, material, smooth=smooth)

assert not root.get('spark_mechanical_detail')
for obj in list(root.children_recursive):
    if obj.type=='MESH' and (obj.name in ['Front tyre silhouette','Rear tyre silhouette','Front brake annulus','Rear brake annulus'] or obj.name.startswith('Front disc carrier')):
        bpy.data.objects.remove(obj,do_unlink=True)

def inside(p,polygon):
    result=False
    for i,a in enumerate(polygon):
        b=polygon[(i+1)%len(polygon)]
        if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:result=not result
    return result

def circle(radius,count,center=(0,0),phase=0):
    return [Vector((center[0]+radius*math.cos(math.tau*i/count+phase),center[1]+radius*math.sin(math.tau*i/count+phase))) for i in range(count)]

disc_reports=[]
for label,y,x,rout,rin,holes in [('Front',.695,.080,.178,.122,36),('Rear',-.695,.105,.121,.081,28)]:
    loops=[circle(rout,96),circle(rin,80)]
    for row,rr in enumerate([rin+(rout-rin)*.32,rin+(rout-rin)*.73]):
        for i in range(holes):
            angle=math.tau*(i+row*.5)/holes
            loops.append(circle(.0031 if label=='Front' else .0025,8,(rr*math.cos(angle),rr*math.sin(angle))))
    coords=[];edges=[]
    for loop in loops:
        base=len(coords);coords.extend(loop);edges.extend((base+i,base+(i+1)%len(loop)) for i in range(len(loop)))
    cdt=delaunay_2d_cdt(coords,edges,[],0,.0000001)
    points=cdt[0];triangles=[]
    for triangle in cdt[2]:
        center=sum((points[i] for i in triangle),Vector((0,0)))/len(triangle)
        if inside(center,loops[0]) and not any(inside(center,loop) for loop in loops[1:]):triangles.append(triangle)
    used=sorted({i for face in triangles for i in face});remap={old:new for new,old in enumerate(used)}
    points=[points[i] for i in used];triangles=[tuple(remap[i] for i in face) for face in triangles]
    incidence={}
    for face in triangles:
        for i in range(len(face)):
            key=tuple(sorted((face[i],face[(i+1)%len(face)])));incidence[key]=incidence.get(key,0)+1
    boundary=[edge for edge,count in incidence.items() if count==1]
    assert all(count<=2 for count in incidence.values())
    neighbours={}
    for a,b in boundary:neighbours.setdefault(a,set()).add(b);neighbours.setdefault(b,set()).add(a)
    assert all(len(v)==2 for v in neighbours.values()),label+' drilling boundary is not closed'
    seen=set();cycles=0
    for seed in neighbours:
        if seed in seen:continue
        cycles+=1;todo=[seed]
        while todo:
            i=todo.pop()
            if i in seen:continue
            seen.add(i);todo.extend(neighbours[i]-seen)
    assert cycles==len(loops),label+' missing drill boundary'
    n=len(points);vertices=[(xx,y+p.x,.315+p.y) for xx in [x-.0022,x+.0022] for p in points]
    faces=list(triangles)+[tuple(n+i for i in reversed(face)) for face in triangles]
    faces.extend((a,b,b+n,a+n) for a,b in boundary)
    obj=mesh_object(label+' genuinely perforated brake rotor',vertices,faces,'Spark_Machined',label,False)
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges);bm.free()
    disc_reports.append({'wheel':label,'throughHoles':holes*2,'closedBoundaryLoopsBeforeExtrusion':cycles,'radiusMetres':rout})
    if label=='Front':
        for i in range(8):
            a=math.tau*i/8
            tube('Front broad floating disc carrier '+str(i),[(x,y+.042*math.sin(a),.315+.042*math.cos(a)),
                 (x,y+.127*math.sin(a+.11),.315+.127*math.cos(a+.11))],.008,'Spark_Graphite','Front',sides=8)
            lathe('Front rotor floating pin '+str(i),(x,y+.131*math.sin(a+.11),.315+.131*math.cos(a+.11)),(1,0,0),[(-.005,.006),(.005,.006)],'Spark_SatinSteel','Front',12)

profile=[(-.5,.230),(-.51,.252),(-.49,.273),(-.44,.290),(-.35,.302),(-.25,.309),(-.14,.313),(-.06,.3147),(0,.315),
         (.06,.3147),(.14,.313),(.25,.309),(.35,.302),(.44,.290),(.49,.273),(.51,.252),(.5,.230)]
samples=[(0,1),(.024,.85),(.050,0),(.13,0),(.32,0),(.50,0),(.68,0),(.87,0),(.950,0),(.976,.85)]
for label,y,width in [('Front',.695,.125),('Rear',-.695,.160)]:
    vertices=[];faces=[];n=len(profile);rings=24*len(samples)
    for segment in range(24):
        for sample_index,(sample,depth) in enumerate(samples):
            a=math.tau*(segment+sample)/24;i=segment*len(samples)+sample_index
            for j,(x,radius) in enumerate(profile):
                angle=a+.43*abs(x)+(math.pi/24 if x<0 else 0)
                weight=min(1,max(0,(abs(x)-.018)/.066),max(0,(.47-abs(x))/.10))
                r=radius-.0032*depth*weight
                vertices.append((x*width,y+r*math.sin(angle),.315+r*math.cos(angle)))
                ni,nj=(i+1)%rings,(j+1)%n;faces.append((i*n+j,ni*n+j,ni*n+nj,i*n+nj))
    mesh_object(label+' road tyre with recessed channels',vertices,faces,'Spark_Rubber',label)

# Front caliper straddles the rotor with two separate pad planes. The bridge
# sits beyond the outer swept radius; caliper belongs to the fixed body.
box('Front brake caliper casting',(.125,.552,.409),(.048,.068,.127),'Spark_Graphite',.016)
for x in [.073,.087]:
    box('Front brake pad '+str(x),(x,.558,.399),(.005,.032,.063),'Spark_Graphite',.003)
box('Front caliper bridge',(.100,.536,.449),(.071,.037,.037),'Spark_Graphite',.010)
for z in [.382,.430]:
    lathe('Front caliper piston cap '+str(z),(.151,.552,z),(1,0,0),[(0,.019),(.004,.019)],'Spark_Graphite',segments=24)
    tube('Front caliper mount '+str(z),[(.128,.565,z),(.104,.639,z)],.009,'Spark_Graphite',sides=12)
    lathe('Front caliper mount screw '+str(z),(.150,.565,z),(1,0,0),[(0,.005),(.005,.005)],'Spark_Machined',segments=6)
box('Rear brake caliper casting',(.138,-.605,.258),(.045,.064,.071),'Spark_Graphite',.012)
tube('Rear brake caliper support',[(.120,-.582,.280),(.116,-.605,.332)],.011,'Spark_Graphite',sides=12)
for side in [-1,1]:
    # Inboard pins and bracket bodies close the previously visible shock/frame gap.
    tube('Shock upper inboard pin '+str(side),[(side*.129,-.449,.738),(side*.196,-.449,.738)],.009,'Spark_Machined',sides=14)
    box('Shock lower swingarm clevis '+str(side),(side*.144,-.610,.337),(.050,.050,.047),'Spark_Graphite',.007)
    tube('Shock lower inboard pin '+str(side),[(side*.116,-.610,.354),(side*.197,-.610,.354)],.009,'Spark_Machined',sides=14)
    box('Fork amber reflector '+str(side),(side*.127,.589,.557),(.012,.028,.079),'Spark_Amber',.008)
    for z in [.373,.428]:
        lathe('Fork caliper boss bolt '+str(side)+' '+str(z),(side*.132,.663-(z-.315)*.46,z),(side,0,0),[(0,.006),(.007,.006)],'Spark_Machined',segments=6)
tube('Front brake hydraulic line',[ (.221,.457,1.014),(.156,.488,.882),(.147,.502,.704),(.153,.540,.499),(.133,.553,.450)],.0034,'Spark_Rubber',sides=8,curved=True)
root['spark_mechanical_detail']=1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_MECHANISMS='+json.dumps({'rotors':disc_reports,'tyreGrooveDepthMetres':.0032,'visualAccepted':False,'licensedGeometryImported':False}))

