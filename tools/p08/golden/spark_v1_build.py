"""Original Spark 450 geometry; no Apex body or external model is loaded.

Native coordinates are X/right, Y/forward, Z/up. Shape dimensions are authored
choices recorded in DESIGN_REVIEW.md, not measurements inferred from pixels.
"""
import bpy
import bmesh
import math
import json
from mathutils import Vector

assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
old_scenes = list(bpy.data.scenes)
scene = bpy.data.scenes.new('Spark450_V1_Original')
bpy.context.window.scene = scene
for old in old_scenes:
    bpy.data.scenes.remove(old)
for obj in list(bpy.data.objects):
    if not obj.users_scene:
        bpy.data.objects.remove(obj)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for material in list(bpy.data.materials):
    bpy.data.materials.remove(material)
root = bpy.data.objects.new('RB_Golden_Spark_v1', None)
scene.collection.objects.link(root)
root['primaryConceptSha256'] = 'e358ecf1a809f5373aa45ef92cbd6897ed1e1693cacc73b0f6df697d91bedce6'
root['licensedGeometryImported'] = False
root['visualAccepted'] = False

SPECS = {
    'Spark_Copper': ((.35, .089, .024), .20, .23),
    'Spark_Cream': ((.66, .595, .475), 0, .27),
    'Spark_Graphite': ((.028, .030, .033), .08, .39),
    'Spark_Machined': ((.55, .565, .59), .97, .27),
    'Spark_SatinSteel': ((.43, .405, .355), .97, .34),
    'Spark_Rubber': ((.012, .014, .016), 0, .70),
    'Spark_Leather': ((.050, .024, .013), 0, .57),
    'Spark_Lens': ((.91, .94, .98), 0, .035),
    'Spark_Lamp': ((.85, .85, .82), .08, .19),
    'Spark_Amber': ((.52, .13, .012), .04, .25),
    'Spark_RedLamp': ((.38, .005, .009), .04, .24),
}
for name, (color, metallic, roughness) in SPECS.items():
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    if name in ['Spark_Copper', 'Spark_Cream']:
        shader.inputs['Coat Weight'].default_value = .48
        shader.inputs['Coat Roughness'].default_value = .13
    if name == 'Spark_Lens':
        shader.inputs['Transmission Weight'].default_value = 1
        shader.inputs['IOR'].default_value = 1.46
    if name in ['Spark_Lamp', 'Spark_Amber', 'Spark_RedLamp']:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = .15 if name == 'Spark_Lamp' else .25
    material['colorIntent'] = 'Linear-light shader reflectance, before sRGB texture baking'

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

# Wheel sets are original straight cast-spoke designs, not Apex geometry.
for label, y, width in [('Front', .695, .125), ('Rear', -.695, .160)]:
    pivot = bpy.data.objects.new('RB_Golden_Spark_v1_Wheel_' + label, None)
    scene.collection.objects.link(pivot)
    pivot.parent = root
    pivot.location = (0, y, .315)
    profile = [(-.5,.229),(-.51,.257),(-.46,.284),(-.34,.305),(-.17,.313),(0,.315),(.17,.313),(.34,.305),(.46,.284),(.51,.257),(.5,.229)]
    vertices = []
    faces = []
    segments = 128
    for i in range(segments):
        a = math.tau*i/segments
        for j, (x, radius) in enumerate(profile):
            vertices.append((x*width, y+radius*math.sin(a), .315+radius*math.cos(a)))
            ni, nj = (i+1)%segments, (j+1)%len(profile)
            faces.append((i*len(profile)+j,ni*len(profile)+j,ni*len(profile)+nj,i*len(profile)+nj))
    mesh_object(label+' tyre silhouette',vertices,faces,'Spark_Rubber',label)
    for side in [-1,1]:
        torus(label+' cast rim outer lip '+str(side),(side*width*.37,y,.315),.226,.009,'Spark_Graphite',label)
        torus(label+' rim edge polished line '+str(side),(side*width*.39,y,.315),.229,.0022,'Spark_Machined',label)
    lathe(label+' axle hub',(0,y,.315),(1,0,0),[(-.047,.035),(-.035,.047),(.035,.047),(.047,.035)],'Spark_Graphite',label,32)
    for j in range(10):
        a=math.tau*j/10
        tube(label+' tapered cast spoke '+str(j),[(0,y+.038*math.sin(a),.315+.038*math.cos(a)),
             (0,y+.125*math.sin(a+.025),.315+.125*math.cos(a+.025)),(0,y+.223*math.sin(a+.055),.315+.223*math.cos(a+.055))],.009,'Spark_Graphite',label,8)
    x=.076 if label=='Front' else .105
    radius=.145 if label=='Front' else .116
    lathe(label+' brake annulus',(x,y,.315),(1,0,0),[(-.002,radius),(.002,radius),(.002,radius-.033),(-.002,radius-.033)],'Spark_Machined',label,96,True)
    for j in range(8):
        a=math.tau*j/8
        tube(label+' disc carrier '+str(j),[(x,y+.043*math.sin(a),.315+.043*math.cos(a)),(x,y+(radius-.025)*math.sin(a+.10),.315+(radius-.025)*math.cos(a+.10))],.006,'Spark_Graphite',label,8)
    for side in [-1,1]:
        lathe(label+' axle fastener '+str(side),(side*(width/2+.016),y,.315),(side,0,0),[(0,.025),(.009,.025),(.011,.019)],'Spark_Machined',label,12)

# Tubular cradle, open triangulated seat rails and genuine paired shocks.
for side in [-1,1]:
    x=side*.136
    tube('Upper black frame rail '+str(side),[(x,-.867,.752),(x,-.53,.750),(x,-.10,.770),(side*.088,.366,.870)],.014,'Spark_Graphite',curved=True)
    tube('Lower cradle frame '+str(side),[(side*.088,.362,.873),(side*.137,.366,.580),(side*.144,.287,.298),
         (x,.156,.239),(x,-.201,.240),(x,-.375,.422),(x,-.280,.690),(x,-.105,.770)],.016,'Spark_Graphite',curved=True)
    tube('Seat triangle diagonal '+str(side),[(x,-.470,.741),(side*.139,-.206,.456),(x,-.074,.764)],.013,'Spark_Graphite',curved=True)
    tube('Rear swingarm '+str(side),[(side*.112,-.239,.348),(side*.117,-.460,.330),(side*.110,-.695,.315)],.023,'Spark_Graphite',sides=12)
    top=Vector((side*.177,-.449,.738));bottom=Vector((side*.179,-.610,.354));axis=(top-bottom).normalized()
    tube('Shock dark cartridge '+str(side),[bottom+axis*.04,top-axis*.055],.021,'Spark_Graphite',sides=24)
    tube('Shock piston '+str(side),[top-axis*.075,top-axis*.006],.009,'Spark_Machined',sides=20)
    helper=axis.cross(Vector((1,0,0))).normalized();other=axis.cross(helper).normalized()
    points=[]
    for i in range(161):
        t=i/160;a=math.tau*8*t
        points.append(bottom+axis*(.065+t*.255)+.030*(helper*math.cos(a)+other*math.sin(a)))
    tube('Eight-turn rear shock spring '+str(side),points,.0042,'Spark_Machined',sides=10)
    for label,p in [('upper',top),('lower',bottom)]:
        lathe('Shock '+label+' mount eye '+str(side),p,(1,0,0),[(-.017,.023),(.017,.023),(.017,.010),(-.017,.010)],'Spark_Machined',segments=24,closed=True)
        tube('Shock '+label+' frame pin '+str(side),[p-Vector((.024,0,0)),p+Vector((.024,0,0))],.008,'Spark_Graphite',sides=12)

for y,z in [(-.73,.747),(-.30,.719),(.325,.415)]:
    tube('Frame transverse bridge '+str(y),[(-.136,y,z),(.136,y,z)],.013,'Spark_Graphite')
for side in [-1,1]:
    points=[(side*.152,-.402,.727),(side*.152,-.085,.744),(side*.153,-.193,.532)]
    front=points;back=[(x-side*.009,y,z) for x,y,z in points]
    panel=mesh_object('Triangular side cover '+str(side),front+back,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],'Spark_Graphite',smooth=False)
    bpy.context.view_layer.objects.active=panel;mod=panel.modifiers.new('Pressed corner fillets','BEVEL');mod.width=.016;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    for y,z in [(-.358,.703),(-.125,.714),(-.198,.574)]:
        lathe('Side-cover screw '+str(side),(side*.160,y,z),(side,0,0),[(0,.006),(.003,.006)],'Spark_Machined',segments=12)

# Distinct finned parallel-twin engine and overlapping cast crankcase covers.
box('Lower cast crankcase',(0,.025,.368),(.324,.335,.260),'Spark_Graphite',.055)
box('Cylinder dark core',(0,.117,.588),(.247,.209,.280),'Spark_Graphite',.025)
for i in range(13):
    height=.471+i*.018
    fin=box('Cooling fin plate %02d'%i,(0,.118,height),(.293,.235,.006),'Spark_Graphite',.005)
    fin.data.materials.append(bpy.data.materials['Spark_Machined'])
    for face in fin.data.polygons:
        if abs(face.normal.z)<.35:face.material_index=1
for side in [-1,1]:
    box('Rounded cylinder head '+str(side),(side*.071,.117,.732),(.131,.198,.072),'Spark_Graphite',.025)
    tube('Head cover center seam '+str(side),[(side*.132,.031,.727),(side*.132,.205,.727)],.0022,'Spark_Machined',sides=8)
    for y,z,radius in [(.134,.366,.104),(-.091,.398,.109)]:
        lathe('Rounded crankcase lid '+str(side)+' '+str(y),(side*.171,y,z),(side,0,0),[(0,radius*.93),(.009,radius),(.034,radius),(.041,radius*.89)],'Spark_Graphite',segments=48)
        torus('Crankcase machined rim '+str(side)+' '+str(y),(side*.213,y,z),radius*.90,.0025,'Spark_Machined',segments=48,sides=6)
        for j in range(8):
            a=math.tau*j/8
            lathe('Case bolt '+str(side)+' '+str(y)+' '+str(j),(side*.218,y+radius*.91*math.sin(a),z+radius*.91*math.cos(a)),(side,0,0),[(0,.005),(.004,.005)],'Spark_Machined',segments=6)
    tube('Rear intake rubber boot '+str(side),[(side*.072,-.014,.677),(side*.072,-.093,.677)],.038,'Spark_Rubber',sides=24)
    box('Carburettor body '+str(side),(side*.074,-.099,.659),(.103,.089,.138),'Spark_SatinSteel',.014)
    lathe('Carburettor round side cap '+str(side),(side*.132,-.099,.675),(side,0,0),[(0,.032),(.013,.032),(.017,.025)],'Spark_Machined',segments=32)
    tube('Fuel line '+str(side),[(side*.083,-.081,.732),(side*.142,-.053,.767),(side*.12,.008,.805)],.005,'Spark_Rubber',sides=10,curved=True)
box('Oil cooler body',(0,.360,.581),(.249,.046,.218),'Spark_Graphite',.012)
for i in range(15):
    tube('Oil cooler horizontal fin %02d'%i,[(-.110,.386,.488+i*.012),(.110,.386,.488+i*.012)],.0022,'Spark_Machined',sides=6)

# Original teardrop fuel tank and sculpted brown long saddle.
tank_sections=[(-.100,.778,.825,.028),(-.065,.776,.867,.074),(.012,.777,.937,.142),
               (.143,.780,.987,.185),(.277,.785,.989,.191),(.395,.794,.959,.169),(.462,.813,.910,.104),(.475,.827,.883,.044)]
profile=[]
for j in range(48):
    angle=math.tau*j/48
    profile.append((math.sin(angle),max(.035,.5+.5*math.cos(angle))))
tank=loft('Copper teardrop tank',tank_sections,profile,'Spark_Copper')
lathe('Tank filler rubber gasket',(0,.239,.990),(0,0,1),[(0,.039),(.002,.039)],'Spark_Graphite',segments=48)
lathe('Flush silver fuel cap',(0,.239,.993),(0,0,1),[(0,.033),(.006,.033),(.009,.029)],'Spark_Machined',segments=48)
seat_profile=[(0,1),(.45,.99),(.77,.93),(.94,.77),(1,.40),(.91,.10),(.52,0),(0,0),(-.52,0),(-.91,.10),(-1,.40),(-.94,.77),(-.77,.93),(-.45,.99)]
seat_sections=[(-.963,.794,.828,.051),(-.905,.782,.846,.120),(-.761,.772,.841,.143),
               (-.644,.761,.824,.145),(-.508,.752,.805,.137),(-.345,.751,.800,.126),(-.182,.758,.812,.108),(-.094,.775,.826,.058)]
loft('Long ribbed brown saddle base',seat_sections,seat_profile,'Spark_Leather')
loft('Fitted black seat pan',[(y,bottom-.012,bottom+.004,width*.96) for y,bottom,top,width in seat_sections],seat_profile,'Spark_Graphite')
for side in [-1,1]:
    tube('Saddle edge piping '+str(side),[(side*.050,-.960,.816),(side*.116,-.90,.807),(side*.138,-.76,.803),
         (side*.138,-.64,.788),(side*.131,-.51,.777),(side*.120,-.35,.776),(side*.102,-.185,.788),(side*.055,-.10,.811)],.002,'Spark_Leather',sides=8,curved=True)

# Two stacked right-side silencers joined to two swept headers.
for index,(x,back_y,back_z,front_z) in enumerate([(.231,-.886,.521,.302),(.243,-.887,.423,.260)]):
    points=[((-.065 if index==0 else .065),.239,.666),(.170+index*.033,.340,.642),
            (.214+index*.018,.395,.515),(.222+index*.018,.365,.309),(.218+index*.022,.187,.245+index*.009),
            (x,-.160,.256+index*.015),(x,-.437,front_z)]
    tube('Swept connected header '+str(index),points,.022,'Spark_SatinSteel',sides=20,curved=True)
    a=Vector((x,-.437,front_z));b=Vector((x,back_y,back_z));axis=(b-a).normalized();length=(b-a).length
    lathe('Satin stacked silencer '+str(index),a,axis,[(0,.026),(.045,.039),(length-.028,.042),(length-.005,.039),
          (length-.005,.031),(length-.110,.030),(.042,.030),(0,.020)],'Spark_SatinSteel',segments=40,closed=True)
    lathe('Dark silencer outlet '+str(index),b-axis*.011,axis,[(-.022,.040),(.006,.039),(.006,.029),(-.022,.029)],'Spark_Graphite',segments=32,closed=True)
    tube('Deep silencer throat '+str(index),[b-axis*.130,b-axis*.105],.029,'Spark_Graphite',sides=24)
    tube('Silencer rear frame hanger '+str(index),[(x,-.642,.412+index*.011),(.145,-.567,.503)],.008,'Spark_Machined',sides=12)

# Connected telescopic fork, fenders, round lamp and analog cockpit.
for side in [-1,1]:
    a=Vector((side*.104,.695,.315));b=Vector((side*.104,.465,.971));axis=(b-a).normalized()
    tube('Lower black fork casting '+str(side),[a,a+axis*.325],.026,'Spark_Graphite',sides=24)
    tube('Polished sliding fork tube '+str(side),[a+axis*.282,b],.019,'Spark_Machined',sides=24)
    tube('Fork upper dust collar '+str(side),[a+axis*.290,a+axis*.317],.029,'Spark_Graphite',sides=24)
    tube('Fork lower axle eye '+str(side),[(side*.078,.695,.315),(side*.131,.695,.315)],.033,'Spark_Graphite',sides=24)
    tube('Upper fork sleeve '+str(side),[b-axis*.135,b-axis*.012],.024,'Spark_Graphite',sides=24)
box('Upper triple clamp',(0,.477,.949),(.298,.080,.030),'Spark_Graphite',.01)
box('Lower triple clamp',(0,.519,.829),(.283,.076,.027),'Spark_Graphite',.009)
tube('Steering head',[(0,.355,.792),(0,.414,.964)],.034,'Spark_Graphite',sides=28)

def fender(name,center_y,radius,width,start,end):
    vertices=[];faces=[];rows=28;cols=10
    for k in range(rows+1):
        a=start+(end-start)*k/rows
        for j in range(cols+1):
            q=j/cols*2-1;r=radius-.013*q*q
            vertices.append((q*width/2,center_y+r*math.sin(a),.315+r*math.cos(a)))
            if k and j:
                i=k*(cols+1)+j;faces.append((i-cols-2,i-cols-1,i,i-1))
    obj=mesh_object(name,vertices,faces,'Spark_Graphite')
    bpy.context.view_layer.objects.active=obj;mod=obj.modifiers.new('Stamped fender thickness','SOLIDIFY');mod.thickness=.006;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)
fender('Short black front fender',.695,.342,.153,-.91,.94)
fender('Rear seat fender',-.695,.355,.162,-1.07,.97)

lathe('Round headlamp black bowl',(0,.676,.919),(0,1,0),[(-.063,.054),(-.033,.083),(.012,.100),(.052,.103),(.066,.098)],'Spark_Graphite',segments=56)
lathe('Rolled bright headlight rim',(0,.676,.919),(0,1,0),[(.045,.101),(.056,.106),(.072,.104),(.076,.099),(.073,.094),(.052,.094)],'Spark_Machined',segments=64,closed=True)
lathe('Headlamp reflector',(0,.676,.919),(0,1,0),[(.068,.092),(.054,.084),(.029,.057),(.015,.016),(.020,.009),(.038,.050),(.062,.085)],'Spark_Machined',segments=56,closed=True)
lathe('Headlight bulb',(0,.676,.919),(0,1,0),[(.034,.011),(.060,.015),(.067,.010)],'Spark_Lamp',segments=24)
lathe('Round glass headlight cover',(0,.676,.919),(0,1,0),[(.069,.094),(.078,.070),(.083,.018),(.085,.004)],'Spark_Lens',segments=64)
for side in [-1,1]:
    tube('Headlight support bracket '+str(side),[(side*.094,.539,.878),(side*.118,.630,.915),(side*.100,.665,.919)],.009,'Spark_Graphite',sides=12)
    for label,y,z in [('front',.681,.881),('rear',-.913,.738)]:
        tube(label+' indicator stalk '+str(side),[(side*.105,y,z),(side*.203,y,z)],.009,'Spark_Graphite',sides=12)
        lathe(label+' amber signal '+str(side),(side*.198,y,z),(side,0,0),[(0,.019),(.023,.019),(.027,.016)],'Spark_Amber',segments=28)

tube('Upright swept handlebar',[(-.330,.420,1.020),(-.238,.430,1.022),(-.153,.430,.997),
     (-.073,.440,.991),(.073,.440,.991),(.153,.430,.997),(.238,.430,1.022),(.330,.420,1.020)],.0125,'Spark_Graphite',sides=16,curved=True)
for side in [-1,1]:
    tube('Ribbed rubber hand grip '+str(side),[(side*.244,.425,1.021),(side*.370,.413,1.020)],.020,'Spark_Rubber',sides=24)
    box('Handlebar switchgear '+str(side),(side*.228,.430,1.021),(.047,.047,.047),'Spark_Graphite',.009)
    tube('Polished control lever '+str(side),[(side*.198,.456,1.030),(side*.250,.474,1.021),(side*.352,.462,1.010)],.006,'Spark_Machined',sides=12,curved=True)
    tube('Mirror swept stem '+str(side),[(side*.218,.422,1.041),(side*.224,.418,1.077),(side*.326,.404,1.130)],.0058,'Spark_Graphite',sides=12,curved=True)
    center=(side*.348,.398,1.137)
    lathe('Round mirror black case '+str(side),center,(0,-1,.12),[(-.009,.052),(0,.058),(.011,.057),(.016,.052)],'Spark_Graphite',segments=48)
    lathe('Round mirror glass '+str(side),center,(0,-1,.12),[(.016,.050),(.018,.050)],'Spark_Machined',segments=48)
    axis=(0,-.60,.80)
    lathe('Twin gauge body '+str(side),(side*.057,.459,1.020),axis,[(-.033,.041),(.018,.044),(.024,.042)],'Spark_Graphite',segments=40)
    lathe('Gauge silver rim '+str(side),(side*.057,.459,1.020),axis,[(.023,.043),(.027,.043),(.027,.036),(.023,.036)],'Spark_Machined',segments=40,closed=True)
    lathe('Gauge dark face '+str(side),(side*.057,.459,1.020),axis,[(.024,.035),(.025,.035)],'Spark_Graphite',segments=40)
    tube('Brake or clutch cable '+str(side),[(side*.221,.457,1.014),(side*.121,.527,.896),(side*.128,.517,.697),
         (side*.139,.552,.521)],.0032,'Spark_Rubber',sides=8,curved=True)

lathe('Rear red lamp',(0,-.984,.812),(0,-1,0),[(-.020,.033),(.015,.033),(.021,.029)],'Spark_RedLamp',segments=40)
tube('Rear lamp mount',[(0,-.874,.756),(0,-.958,.785),(0,-.972,.810)],.014,'Spark_Graphite',curved=True)
box('Rear plate bracket',(0,-.983,.695),(.153,.018,.159),'Spark_Graphite',.006)
for side in [-1,1]:
    tube('Footpeg support '+str(side),[(side*.138,-.169,.357),(side*.230,-.180,.335)],.014,'Spark_Machined',sides=16)
    tube('Ribbed rider footpeg '+str(side),[(side*.225,-.180,.335),(side*.300,-.180,.335)],.014,'Spark_Rubber',sides=16)

# Actual original source only. Surface markings/treads/rotor holes and fine
# controls are completed after the first silhouette renders, not claimed here.
root['stage'] = 'complete original silhouette and joined mechanisms; detailing pending'
root['canonicalWheelbaseMetres'] = 1.390
root['riderSeatHeightMetres'] = .800
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print('SPARK_V1_BUILT=' + json.dumps({'meshComponents':sum(o.type=='MESH' for o in root.children_recursive),
      'licensedMeshesImported':False,'visualAccepted':False,'stage':root['stage']}))
