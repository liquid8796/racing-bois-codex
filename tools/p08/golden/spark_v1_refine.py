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

assert not root.get('spark_silhouette_refine')
for obj in list(root.children_recursive):
    if obj.type=='MESH' and (obj.name in ['Copper teardrop tank','Long ribbed brown saddle base','Fitted black seat pan','Rear plate bracket'] or obj.name.startswith('Saddle edge piping')):
        bpy.data.objects.remove(obj,do_unlink=True)

# A flatter tank flank holds the cream inset; the tapered front clears the
# more raked fork and steering head without moving the gameplay origin.
tank_sections=[(-.100,.778,.824,.028),(-.051,.776,.870,.076),(.020,.778,.932,.139),
               (.125,.779,.981,.183),(.245,.785,.978,.185),(.335,.795,.949,.155),(.401,.813,.899,.090),(.420,.832,.865,.035)]
half=[(0,1),(.38,.994),(.69,.942),(.91,.803),(1,.58),(1,.33),(.95,.100),(.71,.025),(0,.025)]
profile=half+[(-x,z) for x,z in reversed(half[1:-1])]
tank=loft('Copper teardrop tank',tank_sections,profile,'Spark_Copper')
hit,point,normal,index=tank.ray_cast(Vector((0,.239,2)),Vector((0,0,-1)))
assert hit
for name in ['Tank filler rubber gasket','Flush silver fuel cap']:
    bpy.data.objects[name].location.z+=point.z-.989

seat_sections=[(-.963,.794,.852,.051),(-.905,.782,.875,.120),(-.761,.772,.862,.143),
               (-.644,.761,.836,.145),(-.508,.752,.807,.137),(-.345,.751,.800,.126),(-.182,.758,.812,.108),(-.094,.775,.826,.058)]
profile=[(0,1),(.45,.99),(.77,.93),(.94,.77),(1,.40),(.91,.10),(.52,0),(0,0),(-.52,0),(-.91,.10),(-1,.40),(-.94,.77),(-.77,.93),(-.45,.99)]
rings=catmull(seat_sections,32);vertices=[];faces=[];n=len(profile)
for k,(y,bottom,top,width) in enumerate(rings):
    for x,z in profile:
        groove=math.exp(-(math.sin(math.pi*(y+.95)/.030)/.28)**2)
        height=bottom+z*(top-bottom)-.0028*groove*max(0,min(1,(z-.45)/.4))
        vertices.append((x*width,y,height))
    if k:faces.extend(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j) for j in range(n))
faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+j for j in range(n))])
seat=mesh_object('Long ribbed brown saddle base',vertices,faces,'Spark_Leather')
loft('Fitted black seat pan',[(y,bottom-.012,bottom+.004,width*.96) for y,bottom,top,width in seat_sections],profile,'Spark_Graphite')
for side in [-1,1]:
    tube('Saddle edge piping '+str(side),[(side*width*.94,y,bottom+.015) for y,bottom,top,width in seat_sections],.0020,'Spark_Leather',sides=8,curved=True)

# Strap samples the real newly authored saddle, then wraps down at both edges.
vertices=[];faces=[]
for row,y in enumerate([-.702,-.698,-.669,-.665]):
    for col in range(25):
        x=-.148+col*.296/24
        hit,point,normal,index=seat.ray_cast(Vector((x,y,2)),Vector((0,0,-1)))
        height=point.z+.0028 if hit else .781
        vertices.append((x,y,height))
        if row and col:
            i=row*25+col;faces.append((i-26,i-25,i,i-1))
strap=mesh_object('Passenger leather strap',vertices,faces,'Spark_Leather')
bpy.context.view_layer.objects.active=strap;mod=strap.modifiers.new('Strap physical leather thickness','SOLIDIFY');mod.thickness=.0025;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)

fork_prefixes=['Lower black fork casting','Polished sliding fork tube','Fork upper dust collar','Fork lower axle eye','Upper fork sleeve','Upper triple clamp','Lower triple clamp']
for obj in root.children_recursive:
    if obj.type=='MESH' and any(obj.name.startswith(p) for p in fork_prefixes):
        for vertex in obj.data.vertices:
            vertex.co.y-=.070*max(0,min(1,(vertex.co.z-.315)/.656))
        obj.data.update()
for side in [-1,1]:
    tube('Connected handlebar riser '+str(side),[(side*.071,.436,.950),(side*.071,.440,.993)],.014,'Spark_Graphite',sides=16)
    tube('Riser clamp screw '+str(side),[(side*.071,.419,.989),(side*.071,.421,1.003)],.005,'Spark_Machined',sides=6)

# Replace the narrow round spoke algorithm with broad-faced cast blades.
for obj in list(root.children_recursive):
    if obj.type=='MESH' and 'tapered cast spoke' in obj.name:
        bpy.data.objects.remove(obj,do_unlink=True)
for label,y in [('Front',.695),('Rear',-.695)]:
    for j in range(10):
        a=math.tau*j/10;vertices=[];faces=[]
        for k,(radius,angle,width,depth) in enumerate([(.038,a,.016,.007),(.090,a+.013,.012,.006),(.175,a+.039,.009,.0045),(.224,a+.055,.011,.0045)]):
            center=Vector((0,y+radius*math.sin(angle),.315+radius*math.cos(angle)));tangent=Vector((0,math.cos(angle),-math.sin(angle)))
            vertices.extend(center+Vector((x*depth,0,0))+tangent*t*width for x,t in [(-1,-1),(1,-1),(1,1),(-1,1)])
            if k:faces.extend(((k-1)*4+q,(k-1)*4+(q+1)%4,k*4+(q+1)%4,k*4+q) for q in range(4))
        faces.extend([(3,2,1,0),(12,13,14,15)])
        obj=mesh_object(label+' cast blade spoke '+str(j),vertices,faces,'Spark_Graphite',label,False)
        bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Cast spoke edge radius','BEVEL');mod.width=.0012;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)

plate=mesh_object('Angled rear licence bracket',[(-.076,-.945,.745),(.076,-.945,.745),(.076,-1.032,.581),(-.076,-1.032,.581)],[(0,1,2,3)],'Spark_Graphite',smooth=False)
bpy.context.view_layer.objects.active=plate;mod=plate.modifiers.new('Plate bracket thickness','SOLIDIFY');mod.thickness=.008;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)

# Controlled neutral lighting; material reflectance remains explicit linear.
bpy.data.lights['Spark studio Key'].energy=520
bpy.data.lights['Spark studio Fill'].energy=260
bpy.data.lights['Spark studio Rear'].energy=430
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.23
root['spark_silhouette_refine']=1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_V1_REFINED='+json.dumps({'seatActualRibDepthMetres':.0028,'forkRakeAuthoredDegrees':24.6,'visualAccepted':False,'licensedMeshesImported':False}))

