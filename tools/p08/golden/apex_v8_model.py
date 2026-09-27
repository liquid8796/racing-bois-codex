"""Apex v2 bespoke golden mesh. Send this literal script through Blender MCP.

Reference inspected before authoring: ArtSource/Concepts/P08/Golden/apex-v2.png.
Coordinates in recipe: x lateral, y vertical, z forward, all metres.
"""
import bpy, bmesh, math, json
from mathutils import Vector
ROOT = 'D:/Project/Unity/racing-bois/'
SOURCE = ROOT + 'ArtSource/P08/Golden/Apex/V8/'
OUT = ROOT + 'Assets/RacingBois/Art/P08/Golden/Apex/V8/'
EVIDENCE = ROOT + 'docs/p08/golden/apex/v8/'
NAME = 'RB_Golden_Apex_v8'

def coord(p):
    return Vector((p[0], p[2], p[1]))

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
scene.cycles.samples = 24
scene.cycles.device = 'CPU'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
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
for name in ['Apex_Pearl','Apex_Graphite','Apex_Machined','Apex_Rubber','Apex_Titanium','Apex_Glass','Apex_Lamp','Apex_RedLamp','Apex_Lens']:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    images = {}
    for kind in ['BaseColor','Normal','MetallicSmoothness','Roughness']:
        image = bpy.data.images.load(OUT + name + '_' + kind + '.png', check_existing=True)
        image.reload()
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
        shader.inputs['Transmission Weight'].default_value=.20
    if name=='Apex_Lens':
        shader.inputs['Transmission Weight'].default_value=1.0
        shader.inputs['IOR'].default_value=1.46
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
        modifier.width=bevel;modifier.segments=3
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
    # Four quad bands replace the single low-density fan which previously
    # buckled into planar triangles. A physical edge return defines thickness.
    boundary_steps=4; bands=6
    sampled=[]
    for profile in [outer,inner]:
        boundary=[]
        for i in range(len(profile)):
            a=profile[i];b=profile[(i+1)%len(profile)]
            for j in range(boundary_steps):
                t=j/boundary_steps
                boundary.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
        sampled.append(boundary)
    n=len(sampled[0]); vertices=[]; faces=[]; uv=[]
    def surface(y,z,t):
        # Deliberate rolled shoulder taper: body wraps down to narrow sump,
        # curves toward the nose, and turns inward at the vent perimeter.
        lower_taper=max(0,.68-y)*.32
        rear_taper=max(0,.12-z)*.16
        nose_taper=max(0,z-.66)*.17
        roll=.037*math.sin(t*math.pi)
        return side*(width-lower_taper-rear_taper-nose_taper+roll)
    for k in range(bands+1):
        t=k/bands
        for i in range(n):
            a=sampled[0][i];b=sampled[1][i]
            y=a[0]*(1-t)+b[0]*t;z=a[1]*(1-t)+b[1]*t
            vertices.append((surface(y,z,t),y,z));uv.append((z*1.7,y*1.7))
            if k:
                j=(i+1)%n;faces.append(((k-1)*n+i,(k-1)*n+j,k*n+j,k*n+i))
    # The inner wall ends in the air duct; the outer edge turns in 12 mm.
    for band in [0,bands]:
        begin=len(vertices)
        for i in range(n):
            x,y,z=vertices[band*n+i]
            vertices.append((x-side*.012,y,z));uv.append((z*1.7,y*1.7))
        for i in range(n):
            j=(i+1)%n
            faces.append((band*n+i,band*n+j,begin+j,begin+i))
    return mesh(name,vertices,faces,material,uv=uv,smooth=True)

def sculpted_tank():
    # Faceted shoulder, broad crown, pinched knee scallop. The prior all-round
    # superellipse could only produce a balloon and is not used for this part.
    sections=[(-.205,.846,.070,.805),(-.155,.884,.112,.794),
              (-.070,.970,.166,.788),(.040,1.032,.205,.789),
              (.180,1.053,.220,.795),(.290,1.027,.201,.806),
              (.380,.935,.143,.818),(.425,.870,.066,.832)]
    cross=[(0,1),(.55,.985),(.84,.87),(1,.61),(.91,.30),
           (.60,.03),(0,0),(-.60,.03),(-.91,.30),(-1,.61),(-.84,.87),(-.55,.985)]
    vertices=[];faces=[];uv=[]
    for k,(z,top,width,bottom) in enumerate(sections):
        for j,(xx,yy) in enumerate(cross):
            vertices.append((xx*width,bottom+(top-bottom)*yy,z))
            uv.append((j/len(cross),(z+.22)/.65))
            if k:
                n=len(cross);q=(j+1)%n
                faces.append(((k-1)*n+j,(k-1)*n+q,k*n+q,k*n+j))
    n=len(cross)
    faces.extend([tuple(reversed(range(n))),tuple((len(sections)-1)*n+j for j in range(n))])
    return mesh('Apex tailored tank shoulders',vertices,faces,'Apex_Pearl',bevel=.006,uv=uv)

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

"""Bespoke body skins. Appended after V8's geometry/material helpers."""

def cubic_samples(points, steps=4, closed=False):
    samples=[]
    for i in range(len(points) if closed else len(points)-1):
        p0=Vector(points[(i-1)%len(points)] if closed else points[max(0,i-1)])
        p1=Vector(points[i]);p2=Vector(points[(i+1)%len(points)])
        p3=Vector(points[(i+2)%len(points)] if closed else points[min(len(points)-1,i+2)])
        for step in range(steps):
            t=step/steps
            samples.append((2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)*.5)
    if not closed:samples.append(Vector(points[-1]))
    return samples

def tailored_volume(name,sections,profile,material,steps=4):
    rings=cubic_samples(sections,steps)
    cross=cubic_samples(profile,3,True)
    vertices=[];faces=[];uv=[];n=len(cross)
    for k,section in enumerate(rings):
        z,bottom,top,width=section
        for j,p in enumerate(cross):
            vertices.append((p[0]*width,bottom+(top-bottom)*p[1],z))
            uv.append((j/n,(z+1.1)/2.2))
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+j for j in range(n))])
    return mesh(name,vertices,faces,material,uv=uv)

def skin(name,points,faces,material,thickness=.006,bevel=.0012,smooth=True):
    obj=mesh(name,points,faces,material,smooth=smooth)
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Manufactured skin thickness','SOLIDIFY')
    modifier.thickness=thickness;modifier.offset=-1
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    if bevel:
        modifier=obj.modifiers.new('Subtle manufactured edge','BEVEL')
        modifier.width=bevel;modifier.segments=3;modifier.limit_method='ANGLE';modifier.angle_limit=.45
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj

def curved_patch(name,corners,material,rows=6,cols=8,bulge=0):
    # Four corner Coons strip with a very small continuous camber. Distinct
    # styling creases are separate patches, not a smoothed radial ngon fan.
    a,b,c,d=[Vector(p) for p in corners]
    vertices=[];faces=[]
    normal=(b-a).cross(d-a).normalized()
    for r in range(rows+1):
        t=r/rows
        for j in range(cols+1):
            u=j/cols
            p=a*(1-u)*(1-t)+b*u*(1-t)+c*u*t+d*(1-u)*t
            p+=normal*(bulge*math.sin(math.pi*u)*math.sin(math.pi*t))
            vertices.append(p)
            if r and j:
                k=r*(cols+1)+j;faces.append((k-cols-2,k-cols-1,k,k-1))
    return skin(name,vertices,faces,material)

# The crown and knee scallops follow distinct longitudinal curves. Ring
# density follows profile curvature; no flat tank facets or balloon loft.
tank_cross=[(0,1),(.42,.99),(.73,.91),(.96,.74),(1,.56),(.89,.31),(.63,.04),(0,0),(-.63,.04),(-.89,.31),(-1,.56),(-.96,.74),(-.73,.91),(-.42,.99)]
tailored_volume('Sculpted pearl fuel tank',[
    (-.225,.802,.875,.075),(-.17,.793,.91,.108),(-.07,.785,.990,.169),
    (.055,.789,1.027,.211),(.19,.798,1.026,.212),(.29,.805,.997,.190),
    (.365,.814,.948,.137),(.40,.831,.897,.071)],tank_cross,'Apex_Pearl',4)
tailored_volume('Tank underside knee mounting',[
    (-.235,.772,.819,.074),(-.04,.765,.824,.138),(.20,.785,.826,.17),(.39,.813,.842,.09)],
    [(0,1),(.8,1),(1,.70),(.65,0),(-.65,0),(-1,.70),(-.8,1)],'Apex_Graphite')
rod('Flush fuel cap gasket',(0,1.030,.153),(0,1.033,.153),.043,'Apex_Graphite',sides=48)
rod('Machined fuel filler',(0,1.033,.153),(0,1.035,.153),.035,'Apex_Machined',sides=48)
block('Filler release',(0,1.036,.153),(.014,.002,.028),'Apex_Graphite',.002)
for j in range(6):
    a=j*math.tau/6
    rod('Fuel cap socket screw',(.029*math.cos(a),1.035,.153+.029*math.sin(a)),(.029*math.cos(a),1.037,.153+.029*math.sin(a)),.0021,'Apex_Graphite',sides=6)

seat_cross=[(0,1),(.72,.99),(1,.70),(.92,.14),(.63,0),(-.63,0),(-.92,.14),(-1,.70),(-.72,.99)]
tailored_volume('Contoured rider saddle',[(-.620,.809,.889,.115),(-.573,.788,.854,.135),(-.47,.780,.826,.134),(-.36,.786,.826,.126),(-.25,.795,.837,.108),(-.184,.806,.857,.079)],seat_cross,'Apex_Rubber')
tailored_volume('Tapered white tail shell',[(-1.014,.962,.985,.070),(-.948,.928,.981,.105),(-.838,.858,.932,.139),(-.70,.788,.877,.148),(-.57,.761,.809,.137),(-.43,.765,.794,.121),(-.226,.777,.814,.079)],
    [(0,1),(.65,1),(.97,.88),(1,.59),(.61,.02),(0,0),(-.61,.02),(-1,.59),(-.97,.88),(-.65,1)],'Apex_Pearl')
tailored_volume('Elevated compact passenger saddle',[(-.985,.981,1.012,.063),(-.94,.979,1.014,.09),(-.86,.94,.996,.10),(-.808,.918,.979,.09)],seat_cross,'Apex_Rubber')
for side in [-1,1]:
    tube('Saddle tailored perimeter',[(side*.11,.876,-.620),(side*.134,.843,-.573),(side*.133,.819,-.47),(side*.125,.82,-.36),(side*.106,.831,-.25),(side*.078,.848,-.184)],.0018,'Apex_Graphite',sides=6)
    # Black triangular insert is recessed into the falling shoulder of tail.
    points=[(side*.110,.950,-.944),(side*.136,.885,-.826),(side*.148,.824,-.70),(side*.128,.889,-.847)]
    skin('Rear side black vent insert',points,[(0,1,2,3)],'Apex_Graphite',.002,.001,False)

def fairing_x(y,z):
    return .247-.105*((y-.80)/.63)**2-.025*max(0,z-.54)/.40-.025*max(0,.08-z)/.25

def duct_shell(side):
    # The silhouette and the actual diagonal through-opening use matched
    # boundary correspondence. X comes only from surface position, not band
    # interpolation, so smoothing cannot inflate a ring around the opening.
    outer=[(.799,.776),(.905,.580),(.825,.330),(.645,.052),(.502,.015),(.382,.208),(.195,.440),(.520,.468)]
    inner=[(.763,.447),(.785,.335),(.757,.283),(.687,.243),(.605,.172),(.589,.245),(.694,.346),(.742,.414)]
    samples=[]
    for boundary in [outer,inner]:
        p=[]
        for i in range(len(boundary)):
            a=boundary[i];b=boundary[(i+1)%len(boundary)]
            for j in range(4):
                t=j/4;p.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
        samples.append(p)
    n=len(samples[0]);vertices=[];faces=[];uv=[]
    for k in range(7):
        t=k/6
        for j in range(n):
            a,b=samples[0][j],samples[1][j]
            y=a[0]*(1-t)+b[0]*t;z=a[1]*(1-t)+b[1]*t
            # Tight moulded return only in the last two percent of opening.
            x=fairing_x(y,z)-.003*(max(0,t-.96)/.04)
            vertices.append((side*x,y,z));uv.append((z*1.7,y*1.7))
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    obj=mesh('Pearl side fairing with diagonal through duct',vertices,faces,'Apex_Pearl',uv=uv)
    bpy.context.view_layer.objects.active=obj
    modifier=obj.modifiers.new('Moulded fairing skin','SOLIDIFY');modifier.thickness=.006;modifier.offset=-1
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # Actual recessed walls and honeycomb screen, inset thirty millimetres.
    wall=[];wall_faces=[]
    for depth in [0,.034]:
        for y,z in samples[1]:wall.append((side*(fairing_x(y,z)-.004-depth),y,z))
    for j in range(n):wall_faces.append((j,(j+1)%n,n+(j+1)%n,n+j))
    skin('Intake cavity deep black wall',wall,wall_faces,'Apex_Graphite',.003,.001)
    # Narrow diamond-wire cells occupy the actual opening rather than broad
    # silver grille bars, preserving the reference's deep dark intake.
    for j in range(15):
        t=j/14;y=.611+.147*t;z=.215+.150*t
        x=side*(fairing_x(y,z)-.026)
        rod('Duct screen fine horizontal',(x,y,z-.027),(x,y,z+.028),.0008,'Apex_Machined',sides=4)
    for j in range(5):
        offset=(j-2)*.011
        rod('Duct screen diagonal',(side*.214,.611,.212+offset),(side*.214,.758,.362+offset),.0008,'Apex_Graphite',sides=4)

for side in [-1,1]:
    duct_shell(side)
    # Visible pearl/graphite boundary forms the long deliberate shoulder
    # crease descending from steering head toward the saddle front.
    curved_patch('Spar exposed graphite shoulder',[(side*.135,.937,.38),(side*.186,.88,.31),(side*.171,.759,-.155),(side*.129,.791,-.225)],'Apex_Graphite',bulge=.003)
    curved_patch('Narrow pearl shoulder return',[(side*.153,.938,.37),(side*.177,.949,.416),(side*.187,.855,.180),(side*.179,.813,.072)],'Apex_Pearl',bulge=.002)
    # Belly pan is a contoured volume, with a deliberately sharp upper chine.
    curved_patch('Belly pan outer charcoal',[(side*.165,.37,-.339),(side*.20,.364,.202),(side*.17,.194,.440),(side*.103,.236,-.332)],'Apex_Graphite',bulge=.005)
    curved_patch('Belly upper chamfer',[(side*.136,.399,-.282),(side*.185,.416,.143),(side*.20,.364,.202),(side*.165,.37,-.339)],'Apex_Graphite',bulge=.001)
    # Long lower cooling relief, visually black and set behind white skin.
    skin('Lower cooling relief black',[(side*.215,.520,.066),(side*.223,.477,.128),(side*.214,.358,.290),(side*.186,.371,.201)],[(0,1,2,3)],'Apex_Rubber',.004,.001,False)
    # Tiny flush fasteners at the real panel attachment positions.
    for y,z in [(.800,.466),(.664,.072),(.544,.066),(.301,.408)]:
        x=fairing_x(y,z)
        rod('Flush fairing socket',(side*x,y,z),(side*(x+.0023),y,z),.0055,'Apex_Machined',sides=10)
        rod('Flush fairing socket recess',(side*(x+.0024),y,z),(side*(x+.0028),y,z),.0021,'Apex_Graphite',sides=6)
tailored_volume('Closed angular sump skin',[(-.35,.224,.254,.104),(-.18,.205,.249,.154),(.16,.190,.233,.165),(.44,.183,.200,.146)],
    [(0,1),(1,.85),(1,.4),(.72,0),(-.72,0),(-1,.4),(-1,.85)],'Apex_Graphite')

# Attached windscreen with black centre nose forming one visual spine. The
# painted cheeks are individually fitted around real recessed lamp cavities.
nose_parts_start=len(parts)
for side in [-1,1]:
    points=[];faces=[]
    for r in range(13):
        t=r/12
        for j in range(17):
            q=.16+.84*j/16
            a=Vector((side*q*.209,1.033-.055*q*q,.60+.04*q*q))
            b=Vector((side*q*.225,.840+.090*q**.30,1.015-.109*q*q))
            p=a*(1-t)+b*t
            p.y+=.009*math.sin(t*math.pi)*math.sin(q*math.pi)
            points.append(p)
            if r and j:
                k=r*17+j;faces.append((k-18,k-17,k,k-1))
    skin('Continuous fitted upper nose half',points,faces,'Apex_Pearl',.006,.0015)
    curved_patch('Nose wrapped outer cheek',[(side*.209,.978,.64),(side*.225,.930,.906),(side*.222,.851,.950),(side*.245,.906,.760)],'Apex_Pearl',bulge=.002)
    curved_patch('Nose lower lamp return',[(side*.021,.813,1.022),(side*.226,.837,.970),(side*.223,.853,.952),(side*.025,.833,1.016)],'Apex_Pearl',bulge=.001)
    outline=[(side*.028,.836,1.015),(side*.038,.883,1.005),(side*.206,.920,.915),(side*.226,.873,.947),(side*.212,.849,.966)]
    center=sum((Vector(p) for p in outline),Vector())/len(outline)
    inset=[tuple(center+(Vector(p)-center)*.91) for p in outline]
    n=len(outline)
    ringpoints=outline+inset
    ringfaces=[(j,(j+1)%n,n+(j+1)%n,n+j) for j in range(n)]
    skin('Hollow headlamp perimeter gasket',ringpoints,ringfaces,'Apex_Graphite',.011,.0015,False)
    back=[(x,y,z-.033) for x,y,z in inset]
    skin('Deep lamp rear black enclosure',back,[tuple(range(n))],'Apex_Graphite',.002,.001,False)
    wall=inset+back
    skin('Recessed lamp cavity walls',wall,ringfaces,'Apex_Graphite',.002,.001,False)
    front=[(x,y,z+.0015) for x,y,z in inset]
    skin('Clear flush lamp cover',front,[tuple(range(n))],'Apex_Lens',.001,.0005,False)
    # Projectors live behind the angled lens, not on the outer paint surface.
    for index,(x,y,z,r) in enumerate([(.103,.868,.983,.021),(.173,.880,.953,.014)]):
        rod('Reflector barrel',(side*x,y,z-.025),(side*x,y,z-.004),r,'Apex_Machined',sides=32)
        rod('Projector lens',(side*x,y,z-.004),(side*x,y,z-.001),r*.61,'Apex_Lamp',sides=32)
    # The concept mirror housing is a trapezoidal shell, not an oval lozenge.
    tube('Short fairing mirror bracket',[(side*.190,.984,.57),(side*.268,1.020,.535),(side*.321,1.075,.525)],.007,'Apex_Graphite',sides=12)
    mirror_outline=[(side*.295,1.059,.543),(side*.404,1.075,.538),(side*.412,1.129,.517),(side*.326,1.133,.504)]
    skin('Angular fairing mirror case',mirror_outline,[(0,1,2,3)],'Apex_Graphite',.022,.003,False)
    mc=sum((Vector(p) for p in mirror_outline),Vector())/4
    mirror_face=[tuple(mc+(Vector(p)-mc)*.84+Vector((0,0,-.003))) for p in mirror_outline]
    skin('Inset rear facing mirror',mirror_face,[(0,1,2,3)],'Apex_Machined',.001,.0005,False)

vertices=[];faces=[]
for r in range(16):
    t=r/15
    for j in range(17):
        q=(j/8-1)*.16
        a=Vector((q*.209,1.033-.055*q*q,.60+.04*q*q))
        b=Vector((q*.225,.840+.090*abs(q)**.30,1.015-.109*q*q))
        p=a*(1-t)+b*t
        p.y+=.009*math.sin(t*math.pi)*math.sin(abs(q)*math.pi)
        vertices.append(p)
        if r and j:
            k=r*17+j;faces.append((k-18,k-17,k,k-1))
skin('Graphite central nose spine',vertices,faces,'Apex_Graphite',.004,.001)
curved_patch('White central nose point',[(-.016,.818,1.024),(.016,.818,1.024),(.025,.837,1.017),(-.025,.837,1.017)],'Apex_Pearl',rows=2,cols=4)
vertices=[];faces=[]
for r in range(15):
    t=r/14
    for j in range(21):
        q=j/10-1;width=.158-.027*t
        vertices.append((q*width,1.008+.168*t-.036*q*q,.669-.257*t+.048*q*q))
        if r and j:
            k=r*21+j;faces.append((k-22,k-21,k,k-1))
skin('Swept smoked windscreen',vertices,faces,'Apex_Glass',.003,.001)
for side in [-1,1]:
    tube('Windscreen fitted rubber rim',[(side*(.158-.027*t),1.008+.168*t-.036,.669-.257*t+.048) for t in [j/16 for j in range(17)]],.0024,'Apex_Graphite',sides=6)
    for t in [.05,.29,.51]:
        sphere('Screen fixing screw',(side*(.158-.027*t),1.011+.168*t-.036,.669-.257*t+.048),(.006,.006,.006),'Apex_Machined',segments=10,rings=6)

# Traced concept proportion correction: painted nose ends ~0.10m ahead of
# axle, not at the outer end of the tyre. This retains exact component join
# coordinates by warping every nose subcomponent through the same function.
for obj in parts[nose_parts_start:]:
    world=obj.matrix_world.copy();inv=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co;forward=p.y
        p.y=.48+(forward-.48)*.63
        p.z-=.06*max(0,min(1,(forward-.48)/.54))
        vertex.co=inv@p
    obj.data.update()

for side in [-1,1]:
    curved_patch('Fitted shoulder nose bridge',[(side*.209,.960,.580),(side*.222,.799,.776),(side*.236,.824,.744),(side*.242,.905,.580)],'Apex_Pearl',rows=6,cols=8,bulge=.001)

# Aluminium twin spar chassis, raised rear subframe, swingarm and central shock.
for side in [-1,1]:
    tube('Main box spar upper',[(side*.128,.931,.475),(side*.184,.84,.21),(side*.195,.688,-.18),(side*.17,.478,-.24)],.030,'Apex_Graphite',sides=6)
    tube('Box spar machined edge',[(side*.169,.907,.41),(side*.208,.81,.14),(side*.213,.662,-.19)],.012,'Apex_Machined',sides=6)
    tube('Subframe upper rail',[(side*.172,.721,-.18),(side*.15,.803,-.60),(side*.097,.936,-.93)],.018,'Apex_Graphite',sides=10)
    tube('Subframe triangulation',[(side*.16,.574,-.16),(side*.137,.778,-.64),(side*.11,.872,-.85)],.010,'Apex_Machined',sides=10)
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
for label,z,width in [('Front',.715,.130),('Rear',-.715,.190)]:
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
            tube('Directional shallow tyre channel',points,.0007,'Apex_Rubber',label,sides=4)
    rod(label+' axle hub',(-width*.40,.315,z),(width*.40,.315,z),.040,'Apex_Graphite',label,sides=28)
    for j in range(5):
        a=j*math.tau/5
        for fork in [-1,1]:
            points=[]
            for radius,delta in [(.033,0),(.085,.02),(.158,.10*fork),(.215,.13*fork)]:
                points.append((0,.315+radius*math.cos(a+delta),z+radius*math.sin(a+delta)))
            tube(label+' swept split spoke',points,.012,'Apex_Graphite',label,sides=8)
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


"""Correct upper-body overhangs from the actual concept, preserving wheelbase.

This literal tail of the recipe runs before collection assembly and save.
"""
for obj in parts:
    name=obj.name
    tail = any(name.startswith(prefix) for prefix in ['Contoured rider saddle','Tapered white tail shell','Elevated compact passenger saddle','Saddle tailored perimeter','Rear side black vent insert','Subframe upper rail','Subframe triangulation'])
    pipe = any(name.startswith(prefix) for prefix in ['Under-seat exhaust riser','Twin exhaust branch','Under-seat titanium silencer','Hollow silencer end collar','Dark inner exhaust wall','Recessed dark throat','Exhaust hanging strap'])
    led = name.startswith('Rear LED housing') or name.startswith('Continuous rear LED')
    if not (tail or pipe or led):continue
    world=obj.matrix_world.copy();inv=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co
        z=p.y
        if tail and z<-.55 and p.z>.70:
            t=min(1,(-z-.55)/.45)
            p.y=-.55+(z+.55)*.57;p.z+=.07*t
        if pipe:
            t=max(0,min(1,(-z-.40)/.30))
            rear=max(0,min(1,(-z-.72)/.28))
            p.y+=.17*t;p.z+=(-.065+.10*rear)*t
        if led:
            p.y+=.197;p.z+=.028
        vertex.co=inv@p
    obj.data.update()

# Candidate surfacing experiment; components remain editable. No FBX or
# production descriptor is issued before independent visual review.
for obj in parts+wheel_parts['Front']+wheel_parts['Rear']:
    world=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=world
for obj in parts: obj['asset_group']='Body'
for key in ['Front','Rear']:
    for obj in wheel_parts[key]: obj['asset_group']=key
# Neutral studio lighting. The model remains at gameplay scale/origin.
world=bpy.data.worlds.new('Apex neutral review studio');world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.38,.40,.42,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.42;scene.world=world
floor_mat=bpy.data.materials.new('Studio_Only_Ground');floor_mat.diffuse_color=(.30,.32,.34,1);floor_mat.use_nodes=True
floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.30,.32,.34,1)
floor_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.71
bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-.002));floor=bpy.context.object;floor.name='Studio floor not exported';floor.data.materials.append(floor_mat)
for name,position,power,size in [('Softbox',(2.8,4,1.5),700,3.5),('Edge',(-2.5,2.8,-1.9),1000,2.5),('Front strip',(0,2.3,3.5),300,2.3)]:
    data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.location=coord(position);data.energy=power;data.shape='RECTANGLE';data.size=size;data.size_y=size*.65
    obj.rotation_euler=(coord((0,.65,0))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Apex review camera');camera=bpy.data.objects.new('Apex review camera',data);scene.collection.objects.link(camera);scene.camera=camera
camera.location=coord((3.6,1.42,3.30));camera.rotation_euler=(coord((0,.62,0))-camera.location).to_track_quat('-Z','Y').to_euler();data.lens=64
scene.render.filepath=EVIDENCE+'apex-beauty.png'
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+NAME+'.blend')
print('APEX_V8_CANDIDATE_SAVED '+SOURCE+NAME+'.blend')
