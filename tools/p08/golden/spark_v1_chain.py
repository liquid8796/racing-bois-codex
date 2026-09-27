import bpy,bmesh,math,json
from mathutils import Vector
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

for obj in list(root.children_recursive):
    if obj.type=='MESH' and any(obj.name.startswith(p) for p in ['Drive chain','Rear drive sprocket','Countershaft drive sprocket','Countershaft connector']):
        bpy.data.objects.remove(obj,do_unlink=True)
lane=.075
rear=Vector((-.695,.315));front=Vector((-.195,.405))
rear_radius=.101;front_radius=.045
direction=front-rear;distance=direction.length;direction.normalize();perpendicular=Vector((-direction.y,direction.x))
ratio=(rear_radius-front_radius)/distance
upper=direction*ratio+perpendicular*math.sqrt(1-ratio*ratio)
lower=direction*ratio-perpendicular*math.sqrt(1-ratio*ratio)
a=rear+upper*rear_radius;b=front+upper*front_radius;c=front+lower*front_radius;d=rear+lower*rear_radius
theta_upper=math.atan2(upper.y,upper.x);theta_lower=math.atan2(lower.y,lower.x)
path=[]
for i in range(70):path.append(a*(1-i/70)+b*(i/70))
for i in range(55):
    angle=theta_upper+(theta_lower-theta_upper)*i/55;path.append(front+Vector((math.cos(angle),math.sin(angle)))*front_radius)
for i in range(70):path.append(c*(1-i/70)+d*(i/70))
for i in range(90):
    angle=theta_lower+(theta_upper-math.tau-theta_lower)*i/90;path.append(rear+Vector((math.cos(angle),math.sin(angle)))*rear_radius)
path.append(path[0])
lengths=[0]
for i in range(len(path)-1):lengths.append(lengths[-1]+(path[i+1]-path[i]).length)
total=lengths[-1];count=round(total/.0127);pitch=total/count
centers=[]
for i in range(count):
    distance=i*pitch;k=0
    while lengths[k+1]<distance:k+=1
    t=(distance-lengths[k])/(lengths[k+1]-lengths[k]);point=path[k]*(1-t)+path[k+1]*t
    centers.append(Vector((lane,point.x,point.y)))
for i,p in enumerate(centers):
    following=centers[(i+1)%count];axis=(following-p).normalized();across=Vector((0,-axis.z,axis.y))
    tube('Drive chain roller %03d'%i,[p-Vector((.0058,0,0)),p+Vector((.0058,0,0))],.0036,'Spark_SatinSteel',sides=10)
    tube('Drive chain pin %03d'%i,[p-Vector((.0085,0,0)),p+Vector((.0085,0,0))],.0020,'Spark_Machined',sides=8)
    center=(p+following)/2
    # Two closed obround plates, inboard of the same-flank silencers.
    for side in [-1,1]:
        outline=[]
        for sign in [-1,1]:
            for j in range(5):
                angle=math.pi*(j/4-.5)+(0 if sign==1 else math.pi)
                outline.append(center+axis*(sign*pitch*.50+math.cos(angle)*.0038)+across*math.sin(angle)*.0038)
        plate_offset=.0068 if i%2==0 else .0048
        vertices=[point+Vector((side*plate_offset+depth,0,0)) for depth in [-.0009,.0009] for point in outline]
        n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh_object('Drive chain link %03d side %d'%(i,side),vertices,faces,'Spark_SatinSteel')

def sprocket(name,center_y,center_z,radius,teeth,group):
    n=teeth*4;vertices=[];faces=[]
    for x,inside in [(lane-.003,False),(lane+.003,False),(lane+.003,True),(lane-.003,True)]:
        for j in range(n):
            angle=math.tau*j/n
            r=radius*.61 if inside else radius+(.0035 if j%4 in [1,2] else -.005)
            vertices.append((x,center_y+r*math.cos(angle),center_z+r*math.sin(angle)))
    for k in range(4):
        nk=(k+1)%4
        faces.extend((k*n+j,k*n+(j+1)%n,nk*n+(j+1)%n,nk*n+j) for j in range(n))
    mesh_object(name,vertices,faces,'Spark_SatinSteel',group)
    lathe(name+' hub',(lane,center_y,center_z),(1,0,0),[(-.007,.030),(.007,.030)],'Spark_Graphite',group,32)
    for i in range(5):
        angle=math.tau*i/5
        tube(name+' carrier '+str(i),[(lane,center_y+.025*math.cos(angle),center_z+.025*math.sin(angle)),
             (lane,center_y+radius*.72*math.cos(angle+.06),center_z+radius*.72*math.sin(angle+.06))],.007,'Spark_SatinSteel',group,sides=8)
sprocket('Rear drive sprocket',rear.x,rear.y,rear_radius,50,'Rear')
sprocket('Countershaft drive sprocket',front.x,front.y,front_radius,22,'Body')
tube('Countershaft connector',[(.066,front.x,front.y),(.177,front.x,front.y)],.012,'Spark_Machined',sides=20)
root['spark_chain_added']=1
root['chainSameVisibleFlankAsSilencers']=True
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_CHAIN='+json.dumps({'links':count,'actualPitchMetres':pitch,'chainCenterPlaneX':lane,'silencerCenterPlanesX':[.231,.243],'sameFlank':True,'intersectionCheckPending':True,'visualAccepted':False}))

