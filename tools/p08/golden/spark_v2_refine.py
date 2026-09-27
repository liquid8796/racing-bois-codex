"""Spark V2 geometry candidate: original rounded engine castings and controlled tank/seat refinement.
Run only through the pinned direct MCP in the owned Spark session; no V1 source is saved.
"""
import bpy,bmesh,math,json
from mathutils import Vector
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V1/RB_Golden_Spark_v1_editable.blend')
scene=bpy.context.scene
scene.blendermcp_auto_start_server=False
root=bpy.data.objects['RB_Golden_Spark_v1']
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_fork.blend',compress=True)
root.name='RB_Golden_Spark_v2'

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

# Retain the complete wheel, brake, steering, frame, exhaust and contact-related geometry.
replace_prefixes=['Lower cast crankcase','Cylinder dark core','Rounded cylinder head','Head cover center seam',
    'Rounded cast cooling fin','Rounded crankcase lid','Crankcase machined rim','Case bolt','Inset cast service face',
    'Recessed timing plug','Cylinder head anchor bolt','Spark-plug high tension lead','Rear intake rubber boot',
    'Carburettor body','Carburettor round side cap','Fuel line','Copper teardrop tank','Long ribbed brown saddle base',
    'Fitted black seat pan','Saddle edge piping','Passenger leather strap']
preserved={}
removed=[]
for obj in list(root.children_recursive):
    if obj.type=='MESH' and any(obj.name.startswith(prefix) for prefix in replace_prefixes):
        removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
    elif obj.type=='MESH' and obj.name not in ['Tank filler rubber gasket','Flush silver fuel cap']:
        preserved[obj.name]=([tuple(vertex.co) for vertex in obj.data.vertices],[tuple(face.vertices) for face in obj.data.polygons],[tuple(row) for row in obj.matrix_world])

def material(name,color,metal,roughness):
    value=bpy.data.materials.new(name);value.use_nodes=True
    shader=value.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Metallic'].default_value=metal;shader.inputs['Roughness'].default_value=roughness
    return value

material('SparkV2_CastBlack',(.027,.029,.031),.58,.32)
material('SparkV2_FinEdge',(.125,.136,.143),.86,.31)
material('SparkV2_CastAlloy',(.28,.29,.30),.88,.34)
material('SparkV2_LeatherEdge',(.030,.013,.006),0,.52)

def closed_spline(points,steps=7):
    values=[]
    for i in range(len(points)):
        a,b,c,d=[Vector(points[k%len(points)]) for k in [i-1,i,i+1,i+2]]
        for j in range(steps):
            t=j/steps
            values.append(.5*(2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return values

def side_casting(name,outline,material_name):
    """Curved lobed casing with rounded shoulders; no rectangular block core."""
    loop=closed_spline(outline,6);n=len(loop);vertices=[];faces=[]
    center=Vector((.005,.381))
    for x,scale in [(-.184,.86),(-.178,.96),(-.153,1),(-.100,1.016),(.100,1.016),(.153,1),(.178,.96),(.184,.86)]:
        for p in loop:
            q=center+(p-center)*scale;vertices.append((x,q.x,q.y))
    for ring in range(1,8):
        faces.extend(((ring-1)*n+j,(ring-1)*n+(j+1)%n,ring*n+(j+1)%n,ring*n+j) for j in range(n))
    faces.extend([tuple(reversed(range(n))),tuple(7*n+j for j in range(n))])
    return mesh_object(name,vertices,faces,material_name)

case=side_casting('V2 conjoined lobed crankcase',[
    (-.247,.343),(-.222,.450),(-.170,.510),(-.079,.530),(.014,.505),(.096,.528),
    (.202,.486),(.246,.407),(.230,.298),(.157,.245),(.040,.228),(-.083,.232),(-.192,.260)],'SparkV2_CastBlack')

# Two round cylinder barrels share one continuous fin casting; the lobe boundaries are visible in the quarter view.
for side in [-1,1]:
    core=lathe('V2 cylinder barrel '+str(side),(side*.079,.104,.454),(0,.18,1),
        [(0,.077),(.028,.080),(.185,.078),(.245,.083)],'SparkV2_CastBlack',segments=48)
    for vertex in core.data.vertices:
        vertex.co.y=.104+(vertex.co.y-.104)*1.12

def paired_fin(name,z,radius,depth_scale,thickness):
    n=96;loop=[];vertices=[];faces=[];a=.079
    for j in range(n):
        angle=math.tau*j/n;cosine=math.cos(angle);sine=math.sin(angle)
        distance=abs(a*cosine)+math.sqrt(max(0,radius*radius-a*a*sine*sine))
        loop.append(Vector((distance*cosine,distance*sine*depth_scale)))
    y=.102+(z-.454)*.18
    for dz,scale in [(-thickness*.5,.982),(-thickness*.25,1),(thickness*.25,1),(thickness*.5,.982)]:
        vertices.extend((p.x*scale,y+p.y*scale,z+dz) for p in loop)
    for k in range(1,4):faces.extend(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j) for j in range(n))
    faces.extend([tuple(reversed(range(n))),tuple(3*n+j for j in range(n))])
    obj=mesh_object(name,vertices,faces,'SparkV2_CastBlack',smooth=False)
    obj.data.materials.append(bpy.data.materials['SparkV2_FinEdge'])
    for face in obj.data.polygons:
        if abs(face.normal.z)<.55:face.material_index=1;face.use_smooth=True
    return obj

for i in range(15):
    z=.480+i*.0124
    paired_fin('V2 rounded twin fin %02d'%i,z,.105+.004*math.sin(math.pi*i/14),1.14,.0050)
for i in range(4):paired_fin('V2 cylinder head fin %02d'%i,.673+i*.008,.111,1.12,.0048)

# Domed, separate rocker housings and their small gasket flanges replace the two square head covers.
for side in [-1,1]:
    cap=lathe('V2 domed rocker cover '+str(side),(side*.083,.145,.698),(0,0,1),
        [(0,.078),(.004,.083),(.010,.082),(.031,.076),(.047,.061),(.055,.032),(.056,.006)],'SparkV2_CastBlack',segments=56)
    for vertex in cap.data.vertices:vertex.co.y=.145+(vertex.co.y-.145)*1.26
    rim=lathe('V2 rocker gasket flange '+str(side),(side*.083,.145,.700),(0,0,1),[(0,.084),(.003,.084)],'SparkV2_FinEdge',segments=56)
    for vertex in rim.data.vertices:vertex.co.y=.145+(vertex.co.y-.145)*1.26
    for y in [.073,.207]:
        lathe('V2 head stud boss '+str(side)+' '+str(y),(side*.120,y,.691),(0,0,1),[(0,.010),(.016,.010),(.021,.007)],'SparkV2_CastBlack',segments=20)
        lathe('V2 head fastener '+str(side)+' '+str(y),(side*.120,y,.710),(0,0,1),[(0,.0055),(.005,.0055)],'SparkV2_FinEdge',segments=6)
    tube('V2 ignition boot '+str(side),[(side*.085,.156,.738),(side*.085,.170,.767)],.011,'Spark_Rubber',sides=16)
    tube('V2 connected ignition lead '+str(side),[(side*.085,.166,.756),(side*.122,.198,.779),(side*.142,.279,.793)],.0048,'Spark_Rubber',sides=10,curved=True)

# Rounded covers emerge from the common casting; perimeter bosses, ribs and recessed plugs establish mechanical connections.
for side in [-1,1]:
    for label,y,z,radius in [('clutch',-.101,.391,.119),('generator',.130,.367,.101)]:
        center=(side*.166,y,z)
        cover=lathe('V2 joined '+label+' cover '+str(side),center,(side,0,0),
            [(0,radius*.88),(.010,radius),(.025,radius),(.043,radius*.93),(.050,radius*.66),(.052,.014)],'SparkV2_CastBlack',segments=64)
        torus('V2 '+label+' gasket line '+str(side),(side*.190,y,z),radius*.983,.0019,'SparkV2_FinEdge',segments=64,sides=6)
        lathe('V2 '+label+' recessed timing cap '+str(side),(side*.219,y,z),(side,0,0),[(0,.019),(.001,.020),(.003,.017)],'SparkV2_CastBlack',segments=32)
        for j in range(9):
            angle=math.tau*j/9+.12;by=y+radius*.96*math.sin(angle);bz=z+radius*.96*math.cos(angle)
            lathe('V2 '+label+' bolt boss '+str(side)+' '+str(j),(side*.179,by,bz),(side,0,0),[(0,.010),(.020,.010),(.023,.008)],'SparkV2_CastBlack',segments=18)
            lathe('V2 '+label+' bolt '+str(side)+' '+str(j),(side*.203,by,bz),(side,0,0),[(0,.0045),(.004,.0045)],'SparkV2_FinEdge',segments=6)
        for angle in [.35,2.45,3.90]:
            tube('V2 '+label+' cast rib '+str(side)+' '+str(angle),[(side*.211,y+radius*.65*math.sin(angle),z+radius*.65*math.cos(angle)),
                (side*.204,y+radius*.88*math.sin(angle),z+radius*.88*math.cos(angle))],.0036,'SparkV2_CastBlack',sides=8)
    for y,z in [(-.206,.477),(.210,.448),(-.150,.267),(.148,.263)]:
        lathe('V2 case perimeter fastener '+str(side)+' '+str(y),(side*.173,y,z),(side,0,0),[(0,.008),(.010,.008),(.014,.0045)],'SparkV2_FinEdge',segments=8)
    # Rear engine mounts connect the case to the existing cradle; these are authored mechanical joints.
    tube('V2 rear engine mounting lug '+str(side),[(side*.130,-.166,.472),(side*.141,-.220,.431),(side*.137,-.246,.406)],.021,'SparkV2_CastBlack',sides=20)
    lathe('V2 rear mounting through bolt '+str(side),(side*.120,-.239,.426),(side,0,0),[(0,.009),(.047,.009)],'SparkV2_FinEdge',segments=12)

# Cast intake bodies, rubber collars and fuel hoses fill the functional intake space rather than adding a decorative block.
for side in [-1,1]:
    x=side*.079
    tube('V2 inlet runner '+str(side),[(x,.054,.698),(x,-.005,.692),(x,-.046,.678)],.030,'Spark_Rubber',sides=28,curved=True)
    for y,z in [(.027,.695),(-.033,.682)]:
        lathe('V2 intake retaining collar '+str(side)+' '+str(y),(x,y,z),(0,-1,-.10),[(-.004,.032),(.004,.032),(.004,.030),(-.004,.030)],'SparkV2_FinEdge',segments=32,closed=True)
    body=lathe('V2 round carburettor casting '+str(side),(x,-.043,.678),(0,-1,0),[(0,.032),(.012,.043),(.047,.047),(.076,.041),(.084,.031)],'SparkV2_CastAlloy',segments=40)
    lathe('V2 carburettor float bowl '+str(side),(x,-.088,.641),(0,0,-1),[(0,.038),(.027,.037),(.041,.023),(.042,.006)],'SparkV2_CastBlack',segments=36)
    lathe('V2 carburettor vacuum dome '+str(side),(x,-.081,.714),(0,0,1),[(0,.037),(.012,.036),(.024,.023),(.027,.006)],'SparkV2_CastBlack',segments=36)
    lathe('V2 carb side adjustment cap '+str(side),(side*.117,-.085,.678),(side,0,0),[(0,.023),(.011,.023),(.015,.017)],'SparkV2_CastAlloy',segments=36)
    lathe('V2 throttle adjuster '+str(side),(side*.135,-.085,.678),(side,0,0),[(0,.006),(.006,.006)],'SparkV2_FinEdge',segments=8)
    tube('V2 airbox inlet elbow '+str(side),[(x,-.117,.678),(x,-.160,.664),(x,-.184,.637)],.030,'Spark_Rubber',sides=24,curved=True)
    tube('V2 fuel feed '+str(side),[(x,-.084,.729),(side*.129,-.051,.767),(side*.112,.025,.778)],.0048,'Spark_Rubber',sides=10,curved=True)
    # Original exhaust starts are retained exactly; flange collars mechanically join them to the new head.
    exhaust_x=side*.065
    lathe('V2 exhaust port flange '+str(side),(exhaust_x,.239,.666),(0,1,0),[(-.020,.039),(-.002,.039),(.001,.033)],'SparkV2_CastBlack',segments=32)
    for dx in [-.032,.032]:lathe('V2 exhaust stud '+str(side)+' '+str(dx),(exhaust_x+dx,.228,.666),(0,1,0),[(0,.004),(.026,.004)],'SparkV2_FinEdge',segments=8)

# Full lower sidewalls and a more controlled teardrop shoulder; preserve the original UV paint without modifying image bytes.
tank_sections=[(-.110,.767,.834,.030),(-.057,.767,.888,.082),(.025,.767,.957,.151),
    (.135,.770,1.004,.194),(.252,.775,1.001,.199),(.348,.782,.967,.166),(.404,.810,.910,.087),(.427,.839,.878,.027)]
half=[(0,1),(.38,.993),(.69,.944),(.91,.809),(1,.58),(1,.32),(.965,.077),(.71,.019),(0,.035)]
profile=half+[(-x,z) for x,z in reversed(half[1:-1])]
tank=loft('V2 copper teardrop tank',tank_sections,profile,'Spark_Copper')
ring_vertices=(len(tank_sections)-1)*5*len(profile)+len(profile);uv=tank.data.uv_layers.active
for face in tank.data.polygons:
    cap=any(i>=ring_vertices for i in face.vertices)
    wrap=not cap and any(i%16==0 for i in face.vertices) and any(i%16==15 for i in face.vertices)
    for loop in face.loop_indices:
        index=tank.data.loops[loop].vertex_index;p=tank.data.vertices[index].co
        if cap:uv.data[loop].uv=((.025 if p.y<0 else .975)+p.x*.04,.50+p.z*.03)
        else:
            v=(index%16)/16
            if wrap and index%16==0:v=1
            uv.data[loop].uv=(.05+.90*(p.y+.110)/.537,v)
hit,point,normal,index=tank.ray_cast(Vector((0,.239,2)),Vector((0,0,-1)))
assert hit
old_cap=bpy.data.objects['Tank filler rubber gasket'];old_height=min((old_cap.matrix_world@v.co).z for v in old_cap.data.vertices)
for name in ['Tank filler rubber gasket','Flush silver fuel cap']:bpy.data.objects[name].location.z+=point.z-old_height

# Thicker joined cushion, lower edge piping and an explicit passenger strap; rider contact stays at z=.800.
seat_sections=[(-.930,.784,.858,.056),(-.885,.766,.883,.123),(-.749,.756,.871,.146),
    (-.631,.744,.838,.145),(-.493,.731,.808,.135),(-.340,.733,.800,.126),(-.182,.744,.814,.107),(-.104,.771,.833,.057)]
seat_profile=[(0,1),(.45,.989),(.77,.935),(.94,.77),(1,.40),(.92,.09),(.53,0),(0,0),(-.53,0),(-.92,.09),(-1,.40),(-.94,.77),(-.77,.935),(-.45,.989)]
rings=catmull(seat_sections,24);vertices=[];faces=[];n=len(seat_profile)
for k,(y,bottom,top,width) in enumerate(rings):
    for x,z in seat_profile:
        groove=math.exp(-(math.sin(math.pi*(y+.948)/.032)/.25)**2)
        height=bottom+z*(top-bottom)-.0027*groove*max(0,min(1,(z-.52)/.40))
        vertices.append((x*width,y,height))
    if k:faces.extend(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j) for j in range(n))
faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+j for j in range(n))])
seat=mesh_object('V2 shaped leather saddle',vertices,faces,'Spark_Leather')
loft('V2 fitted saddle pan',[(y,bottom-.010,bottom+.004,width*.97) for y,bottom,top,width in seat_sections],seat_profile,'Spark_Graphite')
for side in [-1,1]:
    tube('V2 sewn cushion edge '+str(side),[(side*width*.945,y,bottom+.012) for y,bottom,top,width in seat_sections],.0022,'SparkV2_LeatherEdge',sides=8,curved=True)
vertices=[];faces=[]
for row,y in enumerate([-.709,-.704,-.678,-.673]):
    for col in range(25):
        x=-.148+col*.296/24
        hit,point,normal,index=seat.ray_cast(Vector((x,y,2)),Vector((0,0,-1)))
        vertices.append((x,y,point.z+.0030 if hit else .772))
        if row and col:
            i=row*25+col;faces.append((i-26,i-25,i,i-1))
strap=mesh_object('V2 wrapped passenger strap',vertices,faces,'SparkV2_LeatherEdge')
bpy.context.view_layer.objects.active=strap;modifier=strap.modifiers.new('Leather strap thickness','SOLIDIFY');modifier.thickness=.0028;modifier.offset=-1;bpy.ops.object.modifier_apply(modifier=modifier.name)

for name,position in {'Forward':(0,1.1,0),'Semantic_Left':(-.5,0,0),'Semantic_Right':(.5,0,0),
    'Ground_Front':(0,.695,0),'Ground_Rear':(0,-.695,0),'Contact_Seat':(0,-.340,.800),
    'Contact_Grip_L':(-.330,.420,1.020),'Contact_Grip_R':(.330,.420,1.020),
    'Contact_Foot_L':(-.270,-.180,.335),'Contact_Foot_R':(.270,-.180,.335)}.items():
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=root;obj.location=position

bpy.context.view_layer.update()
for name,before in preserved.items():
    obj=bpy.data.objects[name]
    after=([tuple(vertex.co) for vertex in obj.data.vertices],[tuple(face.vertices) for face in obj.data.polygons],[tuple(row) for row in obj.matrix_world])
    assert before==after,'Unowned geometry changed: '+name
hit,point,normal,index=seat.ray_cast(Vector((0,-.340,2)),Vector((0,0,-1)))
assert hit and abs(point.z-.800)<.003,'Rider seat contact moved'
root['stage']='V2 rounded engine and tank/seat refinement; render review required'
root['visualAccepted']=False;root['primaryConceptSha256']='e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6'
root['sideConceptSha256']='ad5478c942350462a34d12b1ba9f9714cb00a595ff9465bc1d000cf6b5e7ad0b'
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_editable.blend',compress=True)
print('SPARK_V2_REFINED='+json.dumps({'source':bpy.data.filepath,'removedComponents':removed,'preservedMeshCount':len(preserved),'riderSeatSurfaceZ':point.z,
    'newMeshComponents':sum(obj.type=='MESH' and obj.name.startswith('V2 ') for obj in root.children_recursive),'wheelbaseMetres':1.390,'visualAccepted':False,'exported':False,'licensedGeometryImported':False}))
