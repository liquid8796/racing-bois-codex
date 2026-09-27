import bpy,bmesh,math,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
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

def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(p.vertices) for p in obj.data.polygons],all_triangles=False,epsilon=0)

old_a=bpy.data.objects['Swept connected header 0'];old_b=bpy.data.objects['Swept connected header 1']
before_intersections=len(tree(old_a).overlap(tree(old_b)))
for obj in list(root.children_recursive):
    if obj.type=='MESH' and any(obj.name.startswith(p) for p in ['Swept connected header','Satin stacked silencer','Dark silencer outlet','Deep silencer throat','Silencer rear frame hanger','Silencer joining band','Silencer connected hanger','Collector perforated heat shield','Silencer perforated front guard','Heat-shield retaining screw']):
        bpy.data.objects.remove(obj,do_unlink=True)

routes=[ [(-.065,.239,.666),(-.060,.333,.645),(.080,.427,.580),(.170,.393,.430),(.182,.310,.245),
           (.180,.140,.206),(.180,-.100,.222),(.190,-.270,.285),(.231,-.437,.340)],
         [(.065,.239,.666),(.225,.334,.652),(.249,.407,.515),(.252,.390,.302),
           (.249,.190,.245),(.246,-.100,.250),(.243,-.437,.260)] ]
headers=[]
for i,route in enumerate(routes):headers.append(tube('Swept connected header '+str(i),route,.022,'Spark_SatinSteel',sides=20,curved=True))
bpy.context.view_layer.update()
after_intersections=len(tree(headers[0]).overlap(tree(headers[1])))
assert after_intersections==0,'Separated headers still intersect'

for index,(x,front_z,back_z) in enumerate([(.231,.340,.521),(.243,.260,.423)]):
    a=Vector((x,-.437,front_z));b=Vector((x,-.886,back_z));axis=(b-a).normalized();length=(b-a).length
    lathe('Satin stacked silencer '+str(index),a,axis,[(0,.024),(.025,.033),(.070,.041),(length-.025,.041),(length,.037),
          (length,.030),(length-.105,.030),(.064,.035),(.020,.027),(0,.018)],'Spark_SatinSteel',segments=48,closed=True)
    lathe('Dark silencer outlet '+str(index),b-axis*.013,axis,[(-.024,.041),(.012,.039),(.016,.035),(.016,.029),(-.024,.029)],'Spark_Graphite',segments=40,closed=True)
    tube('Deep silencer throat '+str(index),[b-axis*.140,b-axis*.113],.029,'Spark_Graphite',sides=24)
    for y_fraction in [.19,.76]:
        center=a+axis*(length*y_fraction)
        lathe('Silencer joining band '+str(index)+' '+str(y_fraction),center,axis,[(-.005,.042),(.005,.042),(.005,.040),(-.005,.040)],'Spark_SatinSteel',segments=48,closed=True)
    tube('Silencer connected hanger '+str(index),[(x,-.609,front_z+(back_z-front_z)*.383),(.200,-.567,.469),(.146,-.531,.515)],.008,'Spark_Machined',sides=12)

def circle(radius,count,center):
    return [Vector((center[0]+radius*math.cos(math.tau*i/count),center[1]+radius*math.sin(math.tau*i/count))) for i in range(count)]

def inside(point,polygon):
    result=False
    for i,a in enumerate(polygon):
        b=polygon[(i+1)%len(polygon)]
        if (a.y>point.y)!=(b.y>point.y) and point.x<(b.x-a.x)*(point.y-a.y)/(b.y-a.y)+a.x:result=not result
    return result

def curved_guard(name,centers,radius,half_width,hole_radius,holes):
    centers=[Vector(p) for p in catmull(centers,10)]
    lengths=[0]
    for i in range(len(centers)-1):lengths.append(lengths[-1]+(centers[i+1]-centers[i]).length)
    length=lengths[-1];corner=.009
    outline=[]
    for cx,cy,start in [(length-corner,half_width-corner,0),(corner,half_width-corner,math.pi/2),
                        (corner,-half_width+corner,math.pi),(length-corner,-half_width+corner,3*math.pi/2)]:
        for i in range(6):
            a=start+math.pi/2*i/5;outline.append(Vector((cx+corner*math.cos(a),cy+corner*math.sin(a))))
    loops=[outline]
    for side in [-1,1]:
        for i in range(holes):
            loops.append(circle(hole_radius,10,(.023+(length-.046)*i/(holes-1),side*half_width*.42)))
    coords=[];edges=[]
    for loop in loops:
        base=len(coords);coords.extend(loop);edges.extend((base+j,base+(j+1)%len(loop)) for j in range(len(loop)))
    for iu in range(1,max(2,int(length/.012))):
        for iv in range(1,8):
            q=Vector((length*iu/max(2,int(length/.012)),-half_width+2*half_width*iv/8))
            if inside(q,outline) and not any(inside(q,loop) for loop in loops[1:]):
                if all((q-point).length>.002 for point in coords):coords.append(q)
    output=delaunay_2d_cdt(coords,edges,[],0,.0000001);p=output[0];triangles=[]
    for face in output[2]:
        center=sum((p[i] for i in face),Vector((0,0)))/len(face)
        if inside(center,outline) and not any(inside(center,loop) for loop in loops[1:]):triangles.append(face)
    used=sorted({i for face in triangles for i in face});remap={old:new for new,old in enumerate(used)}
    points=[p[i] for i in used];triangles=[tuple(remap[i] for i in face) for face in triangles]
    incidence={}
    for face in triangles:
        for i in range(len(face)):
            edge=tuple(sorted((face[i],face[(i+1)%len(face)])));incidence[edge]=incidence.get(edge,0)+1
    boundary=[e for e,count in incidence.items() if count==1]
    vertices=[]
    for depth in [0,-.0018]:
        for u,v in points:
            k=0
            while k<len(lengths)-2 and lengths[k+1]<u:k+=1
            t=max(0,min(1,(u-lengths[k])/(lengths[k+1]-lengths[k])))
            center=centers[k]*(1-t)+centers[k+1]*t;axis=(centers[k+1]-centers[k]).normalized()
            across=axis.cross(Vector((1,0,0))).normalized();angle=v/radius
            vertices.append(center+(Vector((1,0,0))*math.cos(angle)+across*math.sin(angle))*(radius+depth))
    n=len(points);faces=triangles+[tuple(i+n for i in reversed(face)) for face in triangles]+[(a,b,b+n,a+n) for a,b in boundary]
    obj=mesh_object(name,vertices,faces,'Spark_SatinSteel')
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges),name+' open topology'
    for face in bm.faces:face.smooth=True
    for edge in bm.edges:edge.smooth=not(len(edge.link_faces)==2 and edge.calc_face_angle()>.28)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj

curved_guard('Collector perforated heat shield',[(.249,.168,.245),(.251,.311,.256),(.252,.386,.307),(.250,.402,.360)],.034,.034,.0045,7)
for index,(x,front_z,back_z) in enumerate([(.231,.340,.521),(.243,.260,.423)]):
    a=Vector((x,-.437,front_z));axis=(Vector((x,-.886,back_z))-a).normalized()
    curved_guard('Silencer perforated front guard '+str(index),[a-axis*.017,a+axis*.090,a+axis*.155],.045,.030,.0038,5)
    for fraction in [.005,.145]:
        center=a+axis*fraction+Vector((.046,0,0))
        lathe('Heat-shield retaining screw '+str(index)+' '+str(fraction),center,(1,0,0),[(0,.0038),(.0025,.0038)],'Spark_Machined',segments=6)
root['spark_exhaust_revision']=1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_EXHAUST='+json.dumps({'headerIntersectionsBefore':before_intersections,'headerIntersectionsAfter':after_intersections,
      'sameVisibleFlankSilencers':True,'perforatedCollectorGuardHoles':14,'perforatedCanGuardHolesEach':10,'visualAccepted':False}))

