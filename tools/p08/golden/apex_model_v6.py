"""Apex v2 bespoke golden mesh. Send this literal script through Blender MCP.

Reference inspected before authoring: ArtSource/Concepts/P08/Golden/apex-v2.png.
Coordinates in recipe: x lateral, y vertical, z forward, all metres.
"""
import bpy, bmesh, math, json
from mathutils import Vector
ROOT = 'D:/Project/Unity/racing-bois/'
SOURCE = ROOT + 'ArtSource/P08/Golden/Apex/V6/'
OUT = ROOT + 'Assets/RacingBois/Art/P08/Golden/Apex/V6/'
EVIDENCE = ROOT + 'docs/p08/golden/apex/v6/'
NAME = 'RB_Golden_Apex_v6'

def coord(p):
    return Vector((p[0], -p[2], p[1]))

bpy.ops.wm.save_as_mainfile(filepath=SOURCE + 'scene-before-apex.blend')
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for data in list(bpy.data.meshes):
    if data.users==0:bpy.data.meshes.remove(data)
for data in list(bpy.data.materials):
    if data.users==0 and data.name.startswith('Apex_'):bpy.data.materials.remove(data)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100

def empty(name, parent=None, position=(0,0,0)):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    obj.location = coord(position)
    return obj

root = empty(NAME)
front_pivot = empty(NAME + '_Wheel_Front', root, (0,.315,.715))
rear_pivot = empty(NAME + '_Wheel_Rear', root, (0,.315,-.715))
parts = []
wheel_parts = {'Front':[], 'Rear':[]}
materials = {}
for name in ['Apex_Pearl','Apex_Graphite','Apex_Machined','Apex_Rubber','Apex_Titanium','Apex_Glass','Apex_Lamp','Apex_RedLamp','Apex_Carbon','Apex_Leather']:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    images = {}
    for kind in ['BaseColor','Normal','MetallicSmoothness','Roughness']:
        image = bpy.data.images.load(OUT + name + '_' + kind + '.png', check_existing=True)
        if kind != 'BaseColor': image.colorspace_settings.name='Non-Color'
        image.pack()
        node=nodes.new('ShaderNodeTexImage');node.image=image;node.extension='REPEAT'
        images[kind]=node
    links.new(images['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
    links.new(images['Roughness'].outputs['Color'],shader.inputs['Roughness'])
    separate=nodes.new('ShaderNodeSeparateColor')
    links.new(images['MetallicSmoothness'].outputs['Color'],separate.inputs['Color'])
    links.new(separate.outputs['Red'],shader.inputs['Metallic'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.38
    links.new(images['Normal'].outputs['Color'],normal.inputs['Color'])
    links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    if name=='Apex_Pearl': shader.inputs['Coat Weight'].default_value=.48;shader.inputs['Coat Roughness'].default_value=.24
    if name=='Apex_Carbon': shader.inputs['Coat Weight'].default_value=.30;shader.inputs['Coat Roughness'].default_value=.32
    if name=='Apex_Glass':
        shader.inputs['Coat Weight'].default_value=.55
        shader.inputs['Transmission Weight'].default_value=.42
    if name in ['Apex_Lamp','Apex_RedLamp']:
        image=bpy.data.images.load(OUT+name+'_Emission.png',check_existing=True);image.pack()
        node=nodes.new('ShaderNodeTexImage');node.image=image
        links.new(node.outputs['Color'],shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value=.8 if name=='Apex_Lamp' else 1.5
    materials[name]=mat

def assign(obj, material, group='Body', bevel=0, smooth=True, uv_mode='smart'):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        modifier=obj.modifiers.new('Physical edge radius','BEVEL')
        modifier.width=bevel;modifier.segments=2
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free()
    if not obj.data.uv_layers: obj.data.uv_layers.new(name='UV0_SurfaceMetres')
    if uv_mode=='smart':
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025,area_weight=.7)
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        # Analytic cylindrical surfaces need a separate planar chart for end
        # caps; otherwise all cap UVs would share the same longitudinal value.
        layer=obj.data.uv_layers.active
        for polygon in obj.data.polygons:
            points=[layer.data[i].uv.copy() for i in polygon.loop_indices]
            area=abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points))))*.5
            if area < 1e-10:
                dominant=0
                for axis in [1,2]:
                    if abs(polygon.normal[axis])>abs(polygon.normal[dominant]):dominant=axis
                axes=[axis for axis in range(3) if axis!=dominant]
                for loop in polygon.loop_indices:
                    vertex=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                    layer.data[loop].uv=(vertex[axes[0]]*2+.5,vertex[axes[1]]*2+.5)
    obj.data.materials.clear();obj.data.materials.append(materials[material])
    for polygon in obj.data.polygons: polygon.use_smooth=smooth and len(polygon.vertices)<=4
    if smooth and bevel:
        modifier=obj.modifiers.new('Area weighted manufactured normals','WEIGHTED_NORMAL')
        modifier.keep_sharp=True;modifier.weight=35
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj['surface_uv']='Full material field; manufactured surfaces intentionally share a seamless physical finish. No swatch atlas.'
    (parts if group=='Body' else wheel_parts[group]).append(obj)
    return obj

def mesh(name, vertices, faces, material, group='Body', bevel=0, smooth=True, uv=None):
    data=bpy.data.meshes.new(name);data.from_pydata([coord(p) for p in vertices],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    if uv:
        layer=data.uv_layers.new(name='UV0_SurfaceMetres')
        for face in data.polygons:
            for loop in face.loop_indices: layer.data[loop].uv=uv[data.loops[loop].vertex_index]
    return assign(obj,material,group,bevel,smooth,'preserve' if uv else 'smart')

def tube(name, points, radius, material, group='Body', sides=12):
    vertices=[];faces=[];uv=[]
    distances=[0]
    for i in range(1,len(points)): distances.append(distances[-1]+(Vector(points[i])-Vector(points[i-1])).length)
    for i,p in enumerate(points):
        direction=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        helper=Vector((0,1,0)) if abs(direction.y)<.95 else Vector((1,0,0))
        a=direction.cross(helper).normalized();b=direction.cross(a).normalized()
        for j in range(sides):
            angle=j*math.tau/sides
            vertices.append(Vector(p)+radius*(a*math.cos(angle)+b*math.sin(angle)))
            uv.append((j/sides,distances[i]*3))
        if i:
            for j in range(sides):faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,material,group,uv=uv)

def rod(name,a,b,radius,material,group='Body',sides=20):
    return tube(name,[a,b],radius,material,group,sides)

def block(name,position,size,material,bevel=.008,group='Body'):
    bpy.ops.mesh.primitive_cube_add(size=1,location=coord(position))
    obj=bpy.context.object;obj.name=name;obj.dimensions=(size[0],size[2],size[1])
    return assign(obj,material,group,bevel)

def sphere(name,position,size,material,group='Body',segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=coord(position))
    obj=bpy.context.object;obj.name=name;obj.scale=(size[0]/2,size[2]/2,size[1]/2)
    return assign(obj,material,group)

def loft(name,sections,material,group='Body',sides=24,power=2.6):
    # Each section is z, centre height, half width, half height. Superelliptic
    # cross sections form an authored sport tank/tail rather than scaled spheres.
    # Cubic interpolation follows the authored control profile; three samples
    # between controls remove the longitudinal facets without replacing the
    # sporting silhouette with a generic ellipsoid.
    interpolated=[]
    for i in range(len(sections)-1):
        p0=sections[max(0,i-1)];p1=sections[i];p2=sections[i+1];p3=sections[min(len(sections)-1,i+2)]
        for step in range(3):
            t=step/3;t2=t*t;t3=t2*t
            value=[.5*((2*p1[a])+(-p0[a]+p2[a])*t+(2*p0[a]-5*p1[a]+4*p2[a]-p3[a])*t2+(-p0[a]+3*p1[a]-3*p2[a]+p3[a])*t3) for a in range(4)]
            value[2]=max(.003,value[2]);value[3]=max(.003,value[3]);interpolated.append(value)
    sections=interpolated+[sections[-1]]
    vertices=[];faces=[];uv=[]
    for k,(z,y,rx,ry) in enumerate(sections):
        for j in range(sides):
            angle=j*math.tau/sides;c=math.cos(angle);s=math.sin(angle)
            vertices.append((rx*math.copysign(abs(c)**(2/power),c),y+ry*math.copysign(abs(s)**(2/power),s),z))
            uv.append((j/sides,(z+1.1)/2.2))
        if k:
            for j in range(sides):faces.append(((k-1)*sides+j,(k-1)*sides+(j+1)%sides,k*sides+(j+1)%sides,k*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(sections)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,material,group,uv=uv)

def panel(name,outline,side,width,material,thickness=.009,bevel=.004):
    # Closed skin. The visible x coordinate follows body flow with longitudinal
    # taper, rather than extruding a generic flat fairing across the entire bike.
    front=[(side*(width+.027*math.sin((z+.20)*math.pi)-.045*max(0,.65-y)),y,z) for y,z in outline]
    back=[(x-side*thickness,y,z) for x,y,z in front]
    n=len(front);faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    for i in range(n):faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    return mesh(name,front+back,faces,material,bevel=bevel,smooth=False)

def ring_panel(name,outer,inner,side,width,material):
    n=len(outer);vertices=[];faces=[]
    middle=[(a[0]*.50+b[0]*.50,a[1]*.50+b[1]*.50) for a,b in zip(outer,inner)]
    for index,profile in enumerate([outer,middle,inner]):
        bulge=.028 if index==1 else 0
        vertices.extend((side*(width+.028*math.sin((z+.20)*math.pi)-.075*max(0,.65-y)+bulge),y,z) for y,z in profile)
    for profile in [outer,inner]:
        vertices.extend((side*(width+.028*math.sin((z+.20)*math.pi)-.075*max(0,.65-y)-.010),y,z) for y,z in profile)
    for i in range(n):
        j=(i+1)%n
        faces.extend([(i,j,n+j,n+i),(n+i,n+j,2*n+j,2*n+i),(3*n+i,4*n+i,4*n+j,3*n+j),(i,3*n+i,3*n+j,j),(2*n+i,2*n+j,4*n+j,4*n+i)])
    return mesh(name,vertices,faces,material,bevel=.0035,smooth=True)

def torus(name,center,major,minor,material,group='Body',segments=64,minor_segments=12):
    vertices=[];faces=[];uv=[]
    for i in range(segments):
        a=i*math.tau/segments
        for j in range(minor_segments):
            b=j*math.tau/minor_segments
            vertices.append((center[0]+minor*math.sin(b),center[1]+(major+minor*math.cos(b))*math.cos(a),center[2]+(major+minor*math.cos(b))*math.sin(a)))
            uv.append((i/segments,j/minor_segments))
            faces.append((i*minor_segments+j,((i+1)%segments)*minor_segments+j,((i+1)%segments)*minor_segments+(j+1)%minor_segments,i*minor_segments+(j+1)%minor_segments))
    return mesh(name,vertices,faces,material,group,uv=uv)

def annulus(name,center,outer,inner,depth,material,group='Body',segments=64):
    vertices=[];faces=[]
    for x in [-depth/2,depth/2]:
        for radius in [outer,inner]:
            vertices.extend((center[0]+x,center[1]+radius*math.cos(j*math.tau/segments),center[2]+radius*math.sin(j*math.tau/segments)) for j in range(segments))
    for j in range(segments):
        k=(j+1)%segments
        faces.extend([(j,k,segments+k,segments+j),(2*segments+j,3*segments+j,3*segments+k,2*segments+k),(j,2*segments+j,2*segments+k,k),(segments+j,segments+k,3*segments+k,3*segments+j)])
    return mesh(name,vertices,faces,material,group,smooth=False)

def exhaust_sleeve(name,start,end,outer,inner,material):
    direction=(Vector(end)-Vector(start)).normalized()
    a=direction.cross(Vector((1,0,0))).normalized();b=direction.cross(a).normalized()
    vertices=[];faces=[];segments=32
    for centre in [start,end]:
        for radius in [outer,inner]:
            for j in range(segments):
                angle=j*math.tau/segments
                # Slightly squared tube section follows the angular rear
                # concept while preserving a real hollow bore and wall.
                c=math.cos(angle);s=math.sin(angle)
                vertices.append(Vector(centre)+radius*(a*math.copysign(abs(c)**.76,c)+b*math.copysign(abs(s)**.76,s)))
    for j in range(segments):
        k=(j+1)%segments
        faces.extend([(j,k,segments+k,segments+j),(2*segments+j,3*segments+j,3*segments+k,2*segments+k),(j,2*segments+j,2*segments+k,k),(segments+j,segments+k,3*segments+k,3*segments+j)])
    obj=mesh(name,vertices,faces,material,smooth=True)
    for polygon in obj.data.polygons:polygon.use_smooth=polygon.index%4>=2
    return obj

# Bespoke broad, low sporting tank: pinched knee region, raised shoulders and
# sloping crown, ending before low clip-ons; no tall roadster common body.
loft('Apex sculpted tank',[(-.22,.82,.105,.052),(-.15,.865,.15,.098),(-.02,.92,.203,.134),(.14,.95,.229,.145),(.29,.94,.217,.14),(.39,.89,.155,.088),(.43,.85,.074,.03)],'Apex_Pearl',sides=32,power=3.0)
loft('Tank lower mount',[(-.23,.79,.098,.045),(-.06,.82,.15,.07),(.18,.83,.188,.065),(.37,.82,.12,.04)],'Apex_Graphite',sides=24)
rod('Recessed fuel filler',(0,1.087,.14),(0,1.094,.14),.047,'Apex_Graphite',sides=40)
rod('Machined fuel cap',(0,1.091,.14),(0,1.099,.14),.036,'Apex_Machined',sides=40)
block('Fuel filler latch',(0,1.100,.14),(.021,.003,.034),'Apex_Graphite',.002)
loft('Split rider saddle',[(-.58,.843,.127,.028),(-.50,.823,.142,.029),(-.38,.813,.139,.031),(-.25,.815,.12,.032),(-.16,.824,.095,.027)],'Apex_Rubber',sides=28,power=3.6)
loft('Raised tail shell',[(-1.008,1.004,.077,.020),(-.94,.985,.118,.036),(-.82,.93,.152,.050),(-.66,.87,.156,.060),(-.51,.801,.142,.034),(-.22,.789,.10,.032)],'Apex_Pearl',sides=28,power=3.5)
loft('Passenger pad',[(-.963,1.032,.072,.013),(-.91,1.030,.109,.023),(-.82,.997,.11,.03),(-.785,.983,.096,.019)],'Apex_Rubber',sides=24,power=3.6)
for side in [-1,1]:
    tube('Seat piping',[(side*.13,.846,-.58),(side*.143,.846,-.49),(side*.141,.841,-.37),(side*.119,.845,-.25),(side*.091,.849,-.16)],.0021,'Apex_Graphite',sides=6)
    panel('Tail side intake',[(.954,-.936),(.925,-.842),(.874,-.690),(.900,-.827)],side,.13,'Apex_Graphite',.007,.002)

# Fairing shell is built around its visible air duct. Inner black duct walls
# and a recessed radiator plane make the opening actual negative space.
for side in [-1,1]:
    outer=[(.984,.50),(.940,.73),(.826,.79),(.590,.64),(.310,.53),(.350,.30),(.570,-.17),(.735,-.14)]
    inner=[(.830,.41),(.807,.46),(.760,.43),(.687,.34),(.647,.26),(.670,.20),(.738,.28),(.805,.34)]
    ring_panel('Eight edge upper fairing',outer,inner,side,.235,'Apex_Pearl')
    ring_panel('Recessed intake wall',inner,[(y-.014,z-.02) for y,z in inner],side,.218,'Apex_Graphite')
    panel('Intake backing',[(.808,.40),(.780,.44),(.659,.26),(.677,.215)],side,.19,'Apex_Graphite',.01,.002)
    for j in range(9):
        y=.675+j*.014;z=.245+j*.014
        rod('Intake grille fin',(side*.22,y,z-.025),(side*.22,y,z+.060),.0024,'Apex_Machined',sides=5)
    panel('Fairing shoulder diagonal',[(.945,.53),(.924,.36),(.827,.045),(.785,-.195),(.761,-.225),(.799,.025),(.916,.39)],side,.188,'Apex_Graphite',.01,.003)
    panel('Carbon lower belly pan',[(.407,-.225),(.360,.075),(.288,.53),(.176,.49),(.218,-.26),(.278,-.46)],side,.188,'Apex_Graphite',.012,.003)
    panel('Lower side relief vent',[(.460,-.20),(.352,.10),(.285,.27),(.299,.045)],side,.236,'Apex_Rubber',.01,.002)
    for y,z in [(.898,.55),(.590,-.12),(.373,.43),(.745,-.10)]:
        rod('Fairing Dzus fastener',(side*.268,y,z),(side*.275,y,z),.007,'Apex_Machined',sides=8)
        rod('Fastener inset',(side*.275,y,z),(side*.277,y,z),.0031,'Apex_Graphite',sides=6)
loft('Closed shaped sump fairing',[(-.46,.257,.075,.011),(-.31,.244,.18,.027),(-.08,.218,.192,.034),(.23,.213,.17,.035),(.49,.191,.135,.016)],'Apex_Graphite',sides=16,power=3.4)

# Open, fitted nose shell: the upper white skin is only six millimetres thick.
# It leaves a real open lamp cavity instead of burying lights in a solid loft.
nose_sections=[(.47,1.044,.203,.025),(.56,1.074,.231,.033),(.67,1.070,.246,.045),(.79,1.010,.238,.043),(.89,.954,.205,.034),(.975,.916,.145,.021)]
vertices=[];faces=[];uv=[];cols=17
for r,(z,height,width,drop) in enumerate(nose_sections):
    for j in range(cols):
        q=j/(cols-1)*2-1
        vertices.append((q*width,height-drop*abs(q)**1.4,z+.012*q*q))
        uv.append((j/(cols-1),r/(len(nose_sections)-1)))
for r in range(len(nose_sections)-1):
    for j in range(cols-1):
        i=r*cols+j;faces.append((i,i+1,i+1+cols,i+cols))
nose=mesh('Fitted nose upper shell',vertices,faces,'Apex_Pearl',uv=uv)
bpy.context.view_layer.objects.active=nose
modifier=nose.modifiers.new('Nose skin thickness','SOLIDIFY');modifier.thickness=.006
bpy.ops.object.modifier_apply(modifier=modifier.name)
for side in [-1,1]:
    nose_side=[(side*.231,1.041,.56),(side*.246,1.025,.67),(side*.238,.967,.79),(side*.205,.920,.89),(side*.218,.832,.966),(side*.252,.874,.83),(side*.261,.954,.64)]
    n=len(nose_side)
    mesh('Nose cheek side shell',nose_side+[(x-side*.006,y,z) for x,y,z in nose_side],[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Apex_Pearl',bevel=.004,smooth=False)
    tube('Lower nose return',[(side*.017,.819,1.019),(side*.096,.818,1.005),(side*.208,.824,.971),(side*.258,.857,.837)],.008,'Apex_Pearl',sides=10)
mesh('Sharp central nose keel',[(-.014,.818,1.020),(.014,.818,1.020),(.017,.918,.976),(-.017,.918,.976),(-.014,.818,1.005),(.014,.818,1.005),(.017,.918,.961),(-.017,.918,.961)],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)],'Apex_Pearl',bevel=.002,smooth=False)
# Two headlamp assemblies set into a dark gasket-shaped sweep below the brow.
for side in [-1,1]:
    outline=[(side*.030,.853,.999),(side*.043,.895,.982),(side*.197,.924,.921),(side*.222,.882,.946),(side*.205,.855,.971)]
    outline=[(x,y-.025,z+.014) for x,y,z in outline]
    back=[(x,y-.003,z-.016) for x,y,z in outline];n=len(outline)
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh('Recessed headlamp gasket',outline+back,faces,'Apex_Graphite',bevel=.004,smooth=False)
    c=Vector((side*.139,.858,.984))
    smaller=[tuple(c+(Vector(p)-c)*.78+Vector((0,0,.005))) for p in outline]
    mesh('Swept clear lamp lens',smaller+[(x,y-.004,z-.012) for x,y,z in smaller],faces,'Apex_Glass',bevel=.003,smooth=False)
    for index,shift in enumerate([-.038,.026]):
        x=side*(.133+shift)
        rod('Inset projector housing',(x,.857+shift*.15,.975),(x,.864+shift*.15,1.001),.020 if index==0 else .013,'Apex_Machined',sides=24)
        rod('Projector optic',(x,.864+shift*.15,1.001),(x,.865+shift*.15,1.004),.013 if index==0 else .008,'Apex_Lamp',sides=24)

# Connected windscreen: front fairing base at y=1.02, curling rearward to 1.19.
vertices=[];faces=[];uv=[];rows=10;cols=17
for r in range(rows):
    t=r/(rows-1)
    for j in range(cols):
        q=2*j/(cols-1)-1
        width=.185-.053*t
        vertices.append((q*width,1.043+.156*t-.040*q*q,.699-.270*t+.023*q*q))
        uv.append((j/(cols-1),t))
for r in range(rows-1):
    for j in range(cols-1):
        i=r*cols+j;faces.append((i,i+1,i+1+cols,i+cols))
screen=mesh('Connected swept windscreen',vertices,faces,'Apex_Glass',uv=uv)
bpy.context.view_layer.objects.active=screen
modifier=screen.modifiers.new('4 mm polycarbonate','SOLIDIFY');modifier.thickness=.004
bpy.ops.object.modifier_apply(modifier=modifier.name)
for side in [-1,1]:
    tube('Windscreen gasket',[(side*(.185-.053*t),1.043+.156*t-.040,.699-.270*t+.023) for t in [j/12 for j in range(13)]],.004,'Apex_Rubber',sides=8)
    for t in [.06,.35,.64]:
        sphere('Screen screw',(side*(.185-.053*t),1.047+.156*t-.040,.699-.270*t+.023),(.01,.009,.011),'Apex_Machined',segments=12,rings=6)
    tube('Fairing mirror arm',[(side*.224,1.016,.595),(side*.29,1.047,.57),(side*.36,1.073,.51)],.009,'Apex_Graphite',sides=12)
    mirror=loft('Angular aero mirror',[(-.035,0,.02,.008),(0,.009,.047,.024),(.08,.015,.057,.024),(.111,.003,.042,.016)],'Apex_Graphite',sides=12,power=3.6)
    mirror.location=coord((side*.358,1.065,.44));mirror.rotation_euler.z=side*.40
    sphere('Mirror glass',(side*.366,1.088,.463),(.090,.042,.006),'Apex_Machined',segments=20,rings=8)

# Aluminium twin spar chassis, raised rear subframe, swingarm and central shock.
for side in [-1,1]:
    tube('Main box spar upper',[(side*.128,.931,.475),(side*.184,.84,.21),(side*.195,.688,-.18),(side*.17,.478,-.24)],.044,'Apex_Graphite',sides=6)
    tube('Box spar machined edge',[(side*.169,.907,.41),(side*.208,.81,.14),(side*.213,.662,-.19)],.012,'Apex_Machined',sides=6)
    tube('Subframe upper rail',[(side*.172,.721,-.18),(side*.15,.803,-.60),(side*.097,.936,-.93)],.018,'Apex_Graphite',sides=10)
    tube('Subframe triangulation',[(side*.16,.574,-.16),(side*.137,.778,-.64),(side*.11,.872,-.85)],.013,'Apex_Machined',sides=10)
    panel('Sculpted alloy swingarm',[(.44,-.205),(.445,-.29),(.352,-.73),(.265,-.79),(.259,-.683),(.338,-.33)],side,.161,'Apex_Graphite',.045,.007)
    rod('Swingarm pivot',(side*.14,.421,-.217),(side*.207,.421,-.217),.038,'Apex_Machined',sides=32)
    rod('Pivot inset',(side*.209,.421,-.217),(side*.213,.421,-.217),.023,'Apex_Graphite',sides=24)
    rod('Rear axle block',(side*.145,.315,-.715),(side*.217,.315,-.715),.030,'Apex_Machined',sides=24)
    rod('Rear axle hex',(side*.217,.315,-.715),(side*.227,.315,-.715),.023,'Apex_Graphite',sides=6)
    for y,z in [(.695,-.17),(.762,-.28),(.80,-.56)]:
        rod('Frame fixing',(side*.176,y,z),(side*.209,y,z),.012,'Apex_Machined',sides=8)
rod('Monoshock piston',(0,.706,-.32),(0,.432,-.46),.018,'Apex_Machined',sides=20)
rod('Monoshock damper',(0,.697,-.326),(0,.523,-.412),.032,'Apex_Titanium',sides=24)
coil=[]
for i in range(145):
    t=i/144;coil.append((.043*math.cos(t*math.tau*9),.675-.151*t+.020*math.sin(t*math.tau*9),-.345-.073*t+.036*math.sin(t*math.tau*9)))
tube('Shock coil',coil,.006,'Apex_Machined',sides=6)

# Compact inclined four-cylinder engine with real casting/case boundaries.
block('Compact lower crankcase',(0,.449,-.045),(.315,.24,.335),'Apex_Graphite',.05)
block('Inclined cylinder bank',(0,.632,.05),(.322,.186,.184),'Apex_Graphite',.018)
block('Four-cylinder head cover',(0,.731,.075),(.344,.044,.215),'Apex_Machined',.016)
for side in [-1,1]:
    rod('Clutch and alternator cover',(side*.147,.448,-.054),(side*.197,.448,-.054),.112 if side==1 else .101,'Apex_Graphite',sides=40)
    rod('Case machined roundel',(side*.198,.448,-.054),(side*.202,.448,-.054),.055,'Apex_Machined',sides=32)
    rod('Case roundel center',(side*.204,.448,-.054),(side*.206,.448,-.054),.047,'Apex_Graphite',sides=32)
    for j in range(9):
        angle=j*math.tau/9
        y=.448+.094*math.cos(angle);z=-.054+.094*math.sin(angle)
        rod('Engine case bolt',(side*.192,y,z),(side*.213,y,z),.0065,'Apex_Machined',sides=6)
    for y in [.575,.615,.655,.695]:
        block('Casting reinforcing rib',(side*.159,y,.048),(.016,.008,.135),'Apex_Machined',.002)
    tube('Coolant hose',[(side*.126,.715,.129),(side*.18,.67,.245),(side*.15,.48,.281),(side*.087,.39,.24)],.015,'Apex_Rubber',sides=10)
for z,y,width in [(.346,.552,.32),(.343,.580,.325),(.340,.608,.33),(.337,.636,.335),(.334,.664,.34),(.331,.692,.345)]:
    rod('Radiator cooling channel',(-width/2,y,z),(width/2,y,z),.005,'Apex_Machined',sides=6)
for x in [-.14,-.10,-.06,-.02,.02,.06,.10,.14]:
    rod('Radiator vertical fin',(x,.51,.35),(x,.729,.319),.0018,'Apex_Graphite',sides=4)

# Four headers collect below the crankcase, then a central pipe rises to two
# under-seat titanium cans. Exactly two rear-facing exhaust openings.
for x in [-.117,-.039,.039,.117]:
    tube('Swept exhaust header',[(x,.667,.156),(x,.634,.226),(x,.542,.26),(x,.37,.23),(x*.8,.253,.112),(x*.55,.242,-.14)],.020,'Apex_Titanium',sides=12)
loft('Four into one collector',[(-.25,.258,.08,.042),(-.13,.241,.074,.034),(.01,.241,.095,.031)],'Apex_Titanium',sides=16)
tube('Under-seat exhaust riser',[(0,.27,-.22),(.07,.36,-.37),(.105,.53,-.45),(.087,.72,-.60),(0,.804,-.70)],.037,'Apex_Titanium',sides=16)
for side in [-1,1]:
    tube('Twin exhaust branch',[(0,.801,-.70),(side*.064,.833,-.77),(side*.064,.88,-.91)],.035,'Apex_Titanium',sides=16)
    exhaust_sleeve('Under-seat titanium silencer',(side*.064,.851,-.755),(side*.064,.934,-.986),.050,.037,'Apex_Titanium')
    exhaust_sleeve('Hollow silencer end collar',(side*.064,.921,-.953),(side*.064,.939,-1.003),.051,.037,'Apex_Machined')
    exhaust_sleeve('Dark inner exhaust wall',(side*.064,.907,-.921),(side*.064,.935,-.991),.036,.031,'Apex_Graphite')
    rod('Recessed dark throat',(side*.064,.895,-.884),(side*.064,.908,-.923),.031,'Apex_Rubber',sides=24)
    tube('Exhaust hanging strap',[(side*.118,.90,-.865),(side*.107,.851,-.842),(side*.036,.837,-.835)],.006,'Apex_Graphite',sides=6)
block('Rear LED housing',(0,1.005,-1.002),(.163,.019,.014),'Apex_Graphite',.003)
block('Continuous rear LED',(0,1.006,-1.011),(.141,.009,.007),'Apex_RedLamp',.002)

# Real axle-aligned wheels: slightly wider rear section, five sculpted spoke
# pairs, machined rims, front twin rotors and left drive chain.
for label,z,width in [('Front',.715,.118),('Rear',-.715,.183)]:
    vertices=[];faces=[];uv=[];segments=88
    profile=[(-.5,.232),(-.50,.260),(-.43,.285),(-.30,.307),(0,.315),(.30,.307),(.43,.285),(.5,.260),(.5,.232)]
    for i in range(segments):
        a=i*math.tau/segments
        for j,(xx,radius) in enumerate(profile):
            vertices.append((xx*width,.315+radius*math.cos(a),z+radius*math.sin(a)))
            uv.append((i/segments,j/(len(profile)-1)))
            ni=(i+1)%segments;nj=(j+1)%len(profile)
            faces.append((i*len(profile)+j,ni*len(profile)+j,ni*len(profile)+nj,i*len(profile)+nj))
    mesh(label+' crowned road tyre',vertices,faces,'Apex_Rubber',label,uv=uv)
    for side in [-1,1]:
        torus(label+' bead', (side*width*.49,.315,z),.234,.008,'Apex_Rubber',label,segments=72,minor_segments=8)
        torus(label+' machined rim lip',(side*width*.41,.315,z),.220,.011,'Apex_Machined',label,segments=72,minor_segments=8)
        torus(label+' rim shoulder',(side*width*.35,.315,z),.214,.016,'Apex_Graphite',label,segments=64,minor_segments=8)
        for i in range(32):
            a=i*math.tau/32+(0 if side==1 else .055)
            points=[]
            for k in range(6):
                t=k/5;xx=side*width*(.02+.38*t);angle=a+.22*t;radius=.316-.026*t*t
                points.append((xx,.315+radius*math.cos(angle),z+radius*math.sin(angle)))
            tube('Directional shallow tyre channel',points,.0017,'Apex_Graphite',label,sides=4)
    rod(label+' axle hub',(-width*.40,.315,z),(width*.40,.315,z),.040,'Apex_Graphite',label,sides=28)
    for j in range(5):
        a=j*math.tau/5
        for fork in [-1,1]:
            points=[]
            for radius,delta in [(.033,0),(.085,.02),(.158,.10*fork),(.215,.13*fork)]:
                points.append((0,.315+radius*math.cos(a+delta),z+radius*math.sin(a+delta)))
            tube(label+' swept split spoke',points,.0095,'Apex_Graphite',label,sides=8)
    for side in ([-1,1] if label=='Front' else [1]):
        x=side*(.075 if label=='Front' else .108);radius=.150 if label=='Front' else .114
        annulus(label+' brake swept ring',(x,.315,z),radius,radius-.037,.0038,'Apex_Machined',label,segments=88)
        for j in range(9):
            a=j*math.tau/9
            rod(label+' disc carrier arm',(x,.315+.045*math.cos(a),z+.045*math.sin(a)),(x,.315+(radius-.031)*math.cos(a+.12),z+(radius-.031)*math.sin(a+.12)),.007,'Apex_Graphite',label,sides=5)
        for j in range(48):
            a=j*math.tau/48;r=radius-.010-(j%2)*.014
            # Dark recessed drill marker has thickness below the rotor face;
            # tiny hardware kept in LOD0 only by simplification.
            rod('Recessed rotor drilling',(x-side*.002,.315+r*math.cos(a),z+r*math.sin(a)),(x+side*.0025,.315+r*math.cos(a),z+r*math.sin(a)),.0026,'Apex_Graphite',label,sides=6)
    rod(label+' spindle',(-.105,.315,z),(.105,.315,z),.016,'Apex_Machined',label,sides=24)

# Front forks rake back from axle to steering head; calipers fixed to legs.
for side in [-1,1]:
    x=side*.11
    rod('Inverted fork upper',(x,.941,.474),(x,.544,.635),.026,'Apex_Titanium',sides=24)
    rod('Fork chrome stanchion',(x,.599,.613),(x,.357,.710),.019,'Apex_Machined',sides=24)
    rod('Axle clamp',(x,.405,.693),(x,.315,.715),.034,'Apex_Graphite',sides=24)
    rod('Fork dust collar',(x,.555,.630),(x,.534,.639),.028,'Apex_Graphite',sides=24)
    block('Radial four-piston caliper',(side*.090,.386,.605),(.034,.105,.040),'Apex_Graphite',.009)
    for y in [.360,.393,.418]:
        rod('Caliper piston cap',(side*.094,y,.610),(side*.113,y,.610),.012,'Apex_Machined',sides=16)
    tube('Front brake line',[(side*.13,.879,.506),(side*.143,.718,.581),(side*.14,.50,.612),(side*.102,.427,.610)],.0028,'Apex_Rubber',sides=6)
rod('Lower triple clamp',(-.14,.83,.514),(.14,.83,.514),.030,'Apex_Graphite',sides=16)
rod('Upper triple clamp',(-.14,.947,.473),(.14,.947,.473),.024,'Apex_Machined',sides=16)
rod('Steering stem',(0,.872,.499),(0,.973,.458),.022,'Apex_Graphite',sides=24)
for side in [-1,1]:
    rod('Clip-on stalk',(side*.115,.924,.486),(side*.248,.927,.412),.012,'Apex_Machined',sides=16)
    rod('Clip-on rubber grip',(side*.241,.927,.418),(side*.344,.927,.361),.019,'Apex_Rubber',sides=24)
    rod('Handlebar end weight',(side*.342,.927,.364),(side*.365,.927,.351),.020,'Apex_Graphite',sides=24)
    tube('Sculpted brake clutch lever',[(side*.241,.929,.441),(side*.284,.920,.437),(side*.366,.916,.394)],.005,'Apex_Machined',sides=10)
    block('Switchgear',(side*.228,.93,.421),(.039,.033,.044),'Apex_Graphite',.007)
    block('Control switch',(side*.229,.95,.421),(.013,.007,.020),'Apex_RedLamp',.002)
    panel('Rear-set foot bracket',[(.437,-.212),(.393,-.294),(.323,-.315),(.353,-.161)],side,.222,'Apex_Machined',.012,.003)
    rod('Knurled rider foot peg',(side*.226,.342,-.249),(side*.318,.342,-.249),.014,'Apex_Graphite',sides=16)
    for j in range(8):
        rod('Foot peg grip rib',(side*(.233+j*.010),.342,-.249),(side*(.235+j*.010),.342,-.249),.015,'Apex_Machined',sides=10)
    tube('Foot control lever',[(side*.245,.339,-.247),(side*.256,.324,-.142),(side*.286,.324,-.133)],.005,'Apex_Machined',sides=8)
block('Instrument housing',(0,.956,.441),(.166,.036,.088),'Apex_Graphite',.012)
block('Instruments black screen',(0,.978,.441),(.137,.006,.061),'Apex_Glass',.006)
block('Instrument lit telltale',(0,.982,.436),(.043,.003,.014),'Apex_Lamp',.002)
block('Front brake reservoir',(.17,.978,.447),(.046,.030,.040),'Apex_Graphite',.006)

# Close-fitting front fender arc, real curvature above tyre (not a block).
for label,z,width,start,end in [('Front',.715,.144,-1.0,1.05),('Rear',-.715,.186,-.95,.60)]:
    vertices=[];faces=[];uv=[];rows=27;cols=9
    for i in range(rows):
        a=start+(end-start)*i/(rows-1)
        for j in range(cols):
            q=j/(cols-1)*2-1;radius=.352-.024*q*q
            vertices.append((q*width*.5,.315+radius*math.cos(a),z+radius*math.sin(a)))
            uv.append((j/(cols-1),i/(rows-1)))
    for i in range(rows-1):
        for j in range(cols-1):
            k=i*cols+j;faces.append((k,k+1,k+1+cols,k+cols))
    fender=mesh(label+' fitted fender',vertices,faces,'Apex_Graphite',uv=uv)
    bpy.context.view_layer.objects.active=fender
    modifier=fender.modifiers.new('Fender mould thickness','SOLIDIFY');modifier.thickness=.004
    bpy.ops.object.modifier_apply(modifier=modifier.name)

# Left chain and sprockets, continuous upper/lower run to output shaft.
annulus('Rear drive sprocket',(-.114,.315,-.715),.123,.070,.008,'Apex_Titanium','Rear',segments=72)
for j in range(36):
    a=j*math.tau/36
    block('Rear sprocket tooth',(-.114,.315+.125*math.cos(a),-.715+.125*math.sin(a)),(.009,.010,.012),'Apex_Titanium',.001,'Rear')
rod('Front output sprocket',(-.115,.416,-.238),(-.140,.416,-.238),.046,'Apex_Titanium',sides=24)
for height in [.0,1.0]:
    for j in range(26):
        t=j/25;z=-.715+.477*t;y=(.440-.010*t) if height else (.190+.181*t)
        block('Individual chain roller plate',(-.126,y,z),(.014,.009,.016),'Apex_Titanium',.0015)
        rod('Chain roller pin',(-.137,y,z),(-.116,y,z),.0037,'Apex_Machined',sides=8)

# Contacts/markers are separate from visual meshes and retained in FBX.
for name,position in {
    'Forward':(0,0,1.10),'Ground_Front':(0,0,.715),'Ground_Rear':(0,0,-.715),
    'Contact_Seat':(0,.824,-.37),'Contact_Grip_L':(-.294,.927,.389),'Contact_Grip_R':(.294,.927,.389),
    'Contact_Foot_L':(-.286,.342,-.249),'Contact_Foot_R':(.286,.342,-.249)
}.items(): empty(name,root,position)

def join_group(objects,name,parent,pivot):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    obj=bpy.context.object;obj.name=name
    scene.cursor.location=coord(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world
    return obj

# Keep editable named manufacturing parts in the .blend authoring source.
# Only the separately assembled runtime root is selected for FBX export.
source_collection=bpy.data.collections.get('Apex_Source_Components')
if source_collection is None:
    source_collection=bpy.data.collections.new('Apex_Source_Components');scene.collection.children.link(source_collection)
source_collection.hide_render=True;source_collection.hide_viewport=True
for obj in parts+wheel_parts['Front']+wheel_parts['Rear']:
    editable=obj.copy();editable.data=obj.data.copy();source_collection.objects.link(editable)
    editable.name='Source_'+obj.name
    editable['authoring_component']=True

body=join_group(parts,'Apex_L0_Body',root,(0,0,0))
front=join_group(wheel_parts['Front'],'Apex_L0_Front',front_pivot,(0,.315,.715))
rear=join_group(wheel_parts['Rear'],'Apex_L0_Rear',rear_pivot,(0,.315,-.715))
for original in [body,front,rear]:
    for level,ratio in [(1,.45),(2,.15)]:
        duplicate=original.copy();duplicate.data=original.data.copy();scene.collection.objects.link(duplicate)
        duplicate.name=original.name.replace('_L0_','_L'+str(level)+'_')
        bpy.context.view_layer.objects.active=duplicate
        modifier=duplicate.modifiers.new('LOD silhouette-preserving reduction','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        duplicate.hide_render=True
for obj in root.children_recursive:
    if obj.type=='MESH':
        bpy.context.view_layer.objects.active=obj
        modifier=obj.modifiers.new('Final export triangulation','TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        # Thin manufactured bevel faces and solidify rims can inherit collapsed
        # UVs. Give those exact triangles a metric planar chart rather than
        # moving them into a subpixel strip or changing the rest of the unwrap.
        uv=obj.data.uv_layers.active
        for polygon in obj.data.polygons:
            points=[uv.data[i].uv.copy() for i in polygon.loop_indices]
            area=abs(sum(points[i].x*points[(i+1)%len(points)].y-points[(i+1)%len(points)].x*points[i].y for i in range(len(points))))*.5
            if area<1e-12:
                dominant=0
                for axis in [1,2]:
                    if abs(polygon.normal[axis])>abs(polygon.normal[dominant]):dominant=axis
                axes=[axis for axis in range(3) if axis!=dominant]
                for loop in polygon.loop_indices:
                    vertex=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                    uv.data[loop].uv=(vertex[axes[0]]*2+.5,vertex[axes[1]]*2+.5)
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in root.children_recursive:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=OUT+NAME+'.fbx',use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')

# Neutral studio lighting. The model remains at gameplay scale/origin.
world=bpy.data.worlds.new('Apex neutral review studio');world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.105,.12,.14,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.35;scene.world=world
floor_mat=bpy.data.materials.new('Studio_Only_Ground');floor_mat.diffuse_color=(.095,.10,.115,1);floor_mat.use_nodes=True
floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.095,.10,.115,1)
floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.71
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002));floor=bpy.context.object;floor.name='Studio floor not exported';floor.data.materials.append(floor_mat)
for name,position,power,size in [('Softbox',(2.8,4,1.5),700,3.5),('Edge',(-2.5,2.8,-1.9),1000,2.5),('Front strip',(0,2.3,3.5),300,2.3)]:
    data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=coord(position);data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=size*.65
    obj.rotation_euler=(coord((0,.65,0))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Apex review camera');camera=bpy.data.objects.new('Apex review camera',data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=coord((2.85,1.52,3.45));camera.rotation_euler=(coord((0,.62,0))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=64
scene.render.filepath=EVIDENCE+'apex-beauty.png'
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+NAME+'.blend')
counts=[]
for level in range(3):
    meshes=[o for o in root.children_recursive if o.type=='MESH' and '_L'+str(level)+'_' in o.name]
    for obj in meshes:obj.data.calc_loop_triangles()
    counts.append({'level':level,'triangles':sum(len(o.data.loop_triangles) for o in meshes),'meshes':[o.name for o in meshes]})
print('APEX_GEOMETRY_EXPORTED '+json.dumps({'lods':counts,'materials':[m.name for m in body.data.materials],'source':SOURCE+NAME+'.blend','fbx':OUT+NAME+'.fbx'}))
