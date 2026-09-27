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
    if obj.type=='MESH' and any(obj.name.startswith(p) for p in ['Rounded cast cooling fin','Inset cast service face','Recessed timing plug','Cylinder head anchor bolt','Spark-plug high tension lead','Grip molded tread ring','Headlight molded vertical prism','Gauge tick','Gauge resting needle','Gauge needle hub']):
        bpy.data.objects.remove(obj,do_unlink=True)
for obj in list(root.children_recursive):
    if obj.type=='MESH' and obj.name.startswith('Cooling fin plate'):
        bpy.data.objects.remove(obj,do_unlink=True)

def rounded_rectangle(width,depth,radius):
    result=[]
    for sx,sy,start in [(1,1,0),(-1,1,math.pi/2),(-1,-1,math.pi),(1,-1,3*math.pi/2)]:
        center=Vector((sx*(width/2-radius),sy*(depth/2-radius)))
        for i in range(7):
            a=start+math.pi/2*i/6;result.append(center+Vector((math.cos(a),math.sin(a)))*radius)
    return result

# The old box bevel was limited by fin thickness and left square corners.
# Author large XY corner radii explicitly while retaining thin fin plates.
for i in range(13):
    z=.471+i*.018;y=.101+(z-.471)*.16
    width=.272+.022*i/12;depth=.207+.010*i/12
    loop=rounded_rectangle(width,depth,.034);n=len(loop)
    vertices=[(p.x,y+p.y,z+height) for height in [-.0025,.0025] for p in loop]
    faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    fin=mesh_object('Rounded cast cooling fin %02d'%i,vertices,faces,'Spark_Graphite',smooth=False)
    fin.data.materials.append(bpy.data.materials['Spark_Machined'])
    for face in fin.data.polygons:
        if abs(face.normal.z)<.4:face.material_index=1
for obj in root.children_recursive:
    if obj.type=='MESH' and obj.name.startswith('Crankcase machined rim'):
        obj.data.materials[0]=bpy.data.materials['Spark_Graphite']
for side in [-1,1]:
    for y,z,radius in [(.134,.366,.104),(-.091,.398,.109)]:
        lathe('Inset cast service face '+str(side)+' '+str(y),(side*.212,y,z),(side,0,0),
              [(0,radius*.86),(.002,radius*.86),(.004,radius*.79),(.004,radius*.26)],'Spark_Graphite',segments=48)
        lathe('Recessed timing plug '+str(side)+' '+str(y),(side*.217,y,z),(side,0,0),[(0,.024),(.002,.023),(.003,.020)],'Spark_Graphite',segments=32)
    # Head bolts and spark-plug boots connect the head to the cylinder body.
    for y in [.059,.191]:
        lathe('Cylinder head anchor bolt '+str(side)+' '+str(y),(side*.100,y,.764),(0,0,1),[(0,.005),(.004,.005)],'Spark_Machined',segments=6)
    tube('Spark-plug high tension lead '+str(side),[(side*.080,.140,.765),(side*.111,.172,.801),(side*.124,.286,.799)],.006,'Spark_Rubber',sides=10,curved=True)
    for i in range(7):
        x=side*(.256+i*.014)
        lathe('Grip molded tread ring '+str(side)+' '+str(i),(x,.424-(abs(x)-.244)*.095,1.021),(side,0,0),[(-.0008,.0204),(.0008,.0204)],'Spark_Rubber',segments=24)

# Moulded optical prisms, actual thin geometry over the circular glass.
for i in range(19):
    x=-.081+i*.162/18;half=math.sqrt(max(0,.089*.089-x*x));points=[]
    for j in range(13):
        z=-half+2*half*j/12;r2=x*x+z*z
        r=math.sqrt(r2)
        depth=.069+(.094-r)*(.009/.024) if r>=.070 else .078+(.070-r)*(.005/.052) if r>=.018 else .083+(.018-r)*(.002/.014)
        points.append((x,.676+depth+.00022,.919+z))
    tube('Headlight molded vertical prism %02d'%i,points,.00048,'Spark_Lens',sides=6)
shader=bpy.data.materials['Spark_Lamp'].node_tree.nodes.get('Principled BSDF');shader.inputs['Emission Strength'].default_value=.6

# Discernible dials when seen from the rider/rear; they remain original marks.
axis=Vector((0,-.60,.80)).normalized();u=Vector((1,0,0));v=axis.cross(u).normalized()
for side in [-1,1]:
    center=Vector((side*.057,.459,1.020))+axis*.027
    for i in range(17):
        angle=math.radians(-130+260*i/16)
        a=center+u*math.sin(angle)*.031+v*math.cos(angle)*.031
        b=center+u*math.sin(angle)*(.026 if i%4==0 else .028)+v*math.cos(angle)*(.026 if i%4==0 else .028)
        tube('Gauge tick '+str(side)+' '+str(i),[a,b],.0007,'Spark_Cream',sides=4)
    tube('Gauge resting needle '+str(side),[center,center+u*-.021+v*-.016],.00065,'Spark_RedLamp',sides=4)
    lathe('Gauge needle hub '+str(side),center,axis,[(0,.003),(.0015,.003)],'Spark_Machined',segments=12)

root['spark_casting_detail']=1
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_CASTING_DETAIL='+json.dumps({'largeFinCornerRadiusMetres':.034,'opticalPrisms':19,'visualAccepted':False,'licensedMeshesImported':False}))

