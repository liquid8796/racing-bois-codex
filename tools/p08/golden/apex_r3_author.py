"""R3 controlled panel authoring on a separate R2 mechanical source.

The locked apex-v2 concept and native R2 views were inspected first. Fixed
wheelbase, tyre diameter, seat and grip contacts remain unchanged. Run only
on direct Blender MCP9878; never writes earlier sources or Assets outputs.
"""
import bpy,bmesh,math,json
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ROOT='D:/Project/Unity/racing-bois/'
scene=bpy.context.scene
root=bpy.data.objects.get('RB_Golden_Apex_v8_r2')
assert root is not None and not any(o.name.startswith('Apex_L0_') for o in root.children_recursive), 'Load the preserved editable R2 first'
root.name='RB_Golden_Apex_r3'
for o in root.children:
    if o.name.endswith('_Wheel_Front'):o.name='RB_Golden_Apex_r3_Wheel_Front'
    if o.name.endswith('_Wheel_Rear'):o.name='RB_Golden_Apex_r3_Wheel_Rear'
remove_prefixes=['Sculpted pearl fuel tank','Tank underside knee mounting','Flush fuel cap gasket','Machined fuel filler','Filler release','Fuel cap socket screw','Tapered white tail shell','Elevated compact passenger saddle','Rear side black vent insert','Pearl side fairing','Intake cavity','Intake dark plenum','Duct screen','Spar exposed graphite shoulder','Narrow pearl shoulder return','Belly pan outer','Belly upper chamfer','Lower cooling relief','Flush fairing socket','Closed angular sump','Continuous fitted upper nose','Nose wrapped outer','Nose lower lamp','Hollow headlamp','Deep lamp rear','Recessed lamp cavity','Clear flush lamp','Reflector barrel','Projector lens','Short fairing mirror','Angular fairing mirror','Inset rear facing mirror','Graphite central nose','White central nose','Swept smoked windscreen','Windscreen fitted rubber','Screen fixing screw','Fitted shoulder nose bridge','Cast tapered twin chassis spar','Box spar machined edge','Recessed inner frame panel','Rear fitted fender','Subframe triangulation']
removed=[]
for o in list(root.children_recursive):
    if o.type=='MESH' and any(o.name.startswith(p) for p in remove_prefixes):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)

def coord(p):return Vector((p[0],p[2],p[1]))

def final_mesh(name,vertices,faces,material,smooth=True):
    # Convex caps use a centre fan. Keeping many collinear edge samples in an
    # ngon lets the FBX triangulator create zero-area ears along straight runs.
    vertices=list(vertices);triangulated=[]
    for face in faces:
        if len(face)>4:
            centre=sum((Vector(vertices[i]) for i in face),Vector())/len(face);index=len(vertices);vertices.append(centre)
            for j in range(len(face)):triangulated.append((index,face[j],face[(j+1)%len(face)]))
        else:triangulated.append(face)
    faces=triangulated
    data=bpy.data.meshes.new(name+'_Mesh');data.from_pydata([coord(v) for v in vertices],[],faces);data.update()
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.parent=root;o['asset_group']='Body'
    data.materials.append(bpy.data.materials[material])
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.validate(clean_customdata=False);data.update()
    uv=data.uv_layers.new(name='UV_ManufacturedFinish_Metres')
    for face in data.polygons:
        face.use_smooth=smooth
        n=face.normal
        axis=0 if abs(n.x)>=max(abs(n.y),abs(n.z)) else 1 if abs(n.y)>=abs(n.z) else 2
        axes=[i for i in range(3) if i!=axis]
        for loop in face.loop_indices:
            p=data.vertices[data.loops[loop].vertex_index].co;uv.data[loop].uv=(p[axes[0]]*2,p[axes[1]]*2)
    return o

def catmull(points,steps=5,closed=False):
    output=[]
    for i in range(len(points) if closed else len(points)-1):
        a=Vector(points[(i-1)%len(points)] if closed else points[max(0,i-1)]);b=Vector(points[i]);c=Vector(points[(i+1)%len(points)]);d=Vector(points[(i+2)%len(points)] if closed else points[min(len(points)-1,i+2)])
        for j in range(steps):
            t=j/steps;output.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    if not closed:output.append(Vector(points[-1]))
    return output

def corner_fillets(points,fraction=.12,steps=5):
    output=[]
    for i,p in enumerate(points):
        previous=Vector(points[(i-1)%len(points)]);p=Vector(p);following=Vector(points[(i+1)%len(points)])
        a=p+(previous-p)*fraction;b=p+(following-p)*fraction
        for j in range(steps+1):
            t=j/steps;output.append(a*(1-t)*(1-t)+2*p*t*(1-t)+b*t*t)
        next_in=following+(p-following)*fraction
        for j in range(1,4):output.append(b*(1-j/4)+next_in*j/4)
    return output

def loft(name,sections,profile,material,steps=5,linear_front=False):
    rings=catmull(sections,steps);verts=[];faces=[];n=len(profile)
    if linear_front:
        for i in range(len(sections)-1):
            if sections[i][0]<.05:continue
            for j in range(steps):rings[i*steps+j]=Vector(sections[i])*(1-j/steps)+Vector(sections[i+1])*(j/steps)
    for k,(z,bottom,top,width) in enumerate(rings):
        for x,y in profile:verts.append((x*width,bottom+y*(top-bottom),z))
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    # Centre fans preserve a closed cap without collinear ngon ear slivers.
    for k,reverse in [(0,True),(len(rings)-1,False)]:
        centre=sum((Vector(verts[k*n+j]) for j in range(n)),Vector())/n;idx=len(verts);verts.append(centre)
        for j in range(n):faces.append((idx,k*n+(j+1)%n,k*n+j) if reverse else (idx,k*n+j,k*n+(j+1)%n))
    return final_mesh(name,verts,faces,material)

def solid_patch(name,points,faces,material,thickness=.005,smooth=True):
    o=final_mesh(name,points,faces,material,smooth)
    if material=='Apex_Pearl':
        side=1 if sum(v.co.x for v in o.data.vertices)>0 else -1
        hint=Vector((side*.25,1,.2)) if 'front cowl' in name else Vector((side,.15,0))
        average=sum((p.normal*p.area for p in o.data.polygons),Vector())
        if average.dot(hint)<0:
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
        o.data.materials.append(bpy.data.materials['Apex_Graphite'])
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Physical panel return','SOLIDIFY');mod.thickness=thickness;mod.offset=-1
    if material=='Apex_Pearl':mod.material_offset=1;mod.material_offset_rim=0
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
    return o

def quad_patch(name,corners,material,camber=.0,rows=7,cols=10):
    a,b,c,d=[Vector(p) for p in corners];normal=(b-a).cross(d-a).normalized();points=[];faces=[]
    for r in range(rows+1):
        t=r/rows
        for j in range(cols+1):
            u=j/cols;points.append(a*(1-u)*(1-t)+b*u*(1-t)+c*u*t+d*(1-u)*t+normal*camber*math.sin(math.pi*u)*math.sin(math.pi*t))
            if r and j:k=r*(cols+1)+j;faces.append((k-cols-2,k-cols-1,k,k-1))
    return solid_patch(name,points,faces,material)

def tube(name,points,r,material,sides=16):
    verts=[];faces=[]
    for i,p in enumerate(points):
        axis=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized();helper=Vector((0,1,0)) if abs(axis.y)<.9 else Vector((1,0,0));u=axis.cross(helper).normalized();v=axis.cross(u).normalized()
        for j in range(sides):a=math.tau*j/sides;verts.append(Vector(p)+r*(u*math.cos(a)+v*math.sin(a)))
        if i:
            for j in range(sides):faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))]);return final_mesh(name,verts,faces,material)

def bowl(name,center,direction,radii,material):
    axis=Vector(direction).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u).normalized();verts=[];faces=[];n=40
    for depth,radius in radii:
        for j in range(n):a=math.tau*j/n;verts.append(Vector(center)+axis*depth+radius*(u*math.cos(a)+v*math.sin(a)))
    for k in range(len(radii)):
        nk=(k+1)%len(radii)
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,nk*n+(j+1)%n,nk*n+j))
    return final_mesh(name,verts,faces,material)

# A crowned centre, held shoulder crease and hollowed knee zone replace the
# single inflated tank cross section. Closely spaced profile rows round the
# pressed crease without smoothing it away into an ellipsoid.
half=[(0,1),(.38,.997),(.64,.945),(.70,.907),(.94,.730),(1,.660),(.99,.550),(.87,.380),(.72,.160),(.53,.040),(0,0)]
profile=half+[(-x,y) for x,y in reversed(half[1:-1])]
tank=loft('R3 Pressed tank with held shoulder and knee scallops',[
    (-.224,.788,.856,.080),(-.17,.775,.942,.117),(-.06,.771,1.029,.183),
    (.05,.790,1.045,.207),(.17,.801,1.024,.208),(.27,.813,.982,.188),(.355,.826,.932,.139),(.397,.838,.898,.074)],profile,'Apex_Pearl',5,True)
for edge in tank.data.edges:
    a,b=edge.vertices
    if a%len(profile)==b%len(profile) and a%len(profile) in [2,3,7,len(profile)-2,len(profile)-3,len(profile)-7]:edge.use_edge_sharp=True
    if a//len(profile)==b//len(profile) and a//len(profile) in [20,25]:edge.use_edge_sharp=True
loft('R3 Tank underside closed mounting',[(-.23,.775,.805,.075),(-.04,.764,.808,.137),(.20,.794,.826,.17),(.39,.815,.846,.08)],[(0,1),(.8,1),(1,.6),(.6,0),(-.6,0),(-1,.6),(-.8,1)],'Apex_Graphite')
tube('R3 Flush filler black gasket',[(0,1.033,.125),(0,1.036,.125)],.041,'Apex_Graphite',48)
tube('R3 Flush machined filler',[(0,1.036,.125),(0,1.038,.125)],.034,'Apex_Machined',48)
for i in range(6):
    a=math.tau*i/6;tube('R3 Filler socket %02d'%i,[(.028*math.sin(a),1.038,.125+.028*math.cos(a)),(.028*math.sin(a),1.040,.125+.028*math.cos(a))],.0024,'Apex_Graphite',6)

# Retain the measured0.82m rider saddle; a wider continuous side/undertray
# encloses its subframe instead of exposing a schematic triangular rack.
tailprofile=[(0,1),(.68,.98),(.91,.88),(1,.72),(.965,.48),(.80,.15),(.56,.02),(0,0),(-.56,.02),(-.80,.15),(-.965,.48),(-1,.72),(-.91,.88),(-.68,.98)]
loft('R3 Sculpted enclosed tail and seat side return',[(-.900,.988,1.015,.070),(-.846,.959,1.020,.112),(-.75,.887,.998,.142),(-.650,.765,.924,.150),(-.552,.704,.833,.145),(-.432,.710,.801,.131),(-.224,.754,.811,.096)],tailprofile,'Apex_Pearl')
loft('R3 Compact passenger saddle',[(-.875,1.011,1.035,.061),(-.832,1.012,1.040,.094),(-.776,.980,1.022,.108),(-.720,.945,.993,.097)],[(0,1),(.7,.99),(1,.7),(.90,.16),(.60,0),(-.60,0),(-.90,.16),(-1,.7),(-.7,.99)],'Apex_Rubber')
loft('R3 Fitted dark underseat tray',[(-.89,.956,.987,.071),(-.80,.873,.955,.111),(-.68,.769,.834,.118),(-.52,.721,.766,.118),(-.25,.742,.779,.081)],[(0,1),(.88,1),(1,.5),(.6,0),(-.6,0),(-1,.5),(-.88,1)],'Apex_Graphite')
for side in [-1,1]:
    points=[(side*.129,.810,-.58),(side*.148,.789,-.19),(side*.160,.670,-.21),(side*.140,.566,-.34),(side*.120,.615,-.47),(side*.120,.738,-.60)]
    solid_patch('R3 Full underseat moulded side enclosure '+str(side),points,[tuple(range(len(points)))],'Apex_Graphite',.012)
    quad_patch('R3 Tail inset charcoal blade '+str(side),[(side*.099,1.004,-.849),(side*.147,.922,-.725),(side*.149,.875,-.676),(side*.133,.934,-.773)],'Apex_Graphite',.002,5,6)
for o in root.children_recursive:
    if o.type!='MESH':continue
    if any(o.name.startswith(p) for p in ['Under-seat exhaust riser','Twin exhaust branch','Under-seat titanium silencer','Hollow silencer end collar','Dark inner exhaust wall','Recessed dark throat','Exhaust hanging strap','Rear LED housing','Continuous rear LED']):
        world=o.matrix_world.copy();inv=world.inverted()
        for v in o.data.vertices:
            p=world@v.co;t=max(0,min(1,(-p.y-.53)/.30));p.y-=.082*t;p.z-=.030*t;v.co=inv@p
        o.data.update()

def fairing_x(y,z):
    # One continuous outer surface shared by the through-duct and its returns.
    waist=.014*math.exp(-((y-.59)/.14)**2-((z-.10)/.19)**2)
    shoulder=.020*math.exp(-((y-.79)/.18)**2-((z-.38)/.27)**2)
    return .224+shoulder-waist-.091*((y-.76)/.60)**2-.018*max(0,z-.62)/.20

def sample_poly(points,steps=5):
    out=[]
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)]
        for j in range(steps):out.append(Vector(a)*(1-j/steps)+Vector(b)*(j/steps))
    return out

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

for side in [-1,1]:
    outer=[(.84,.765),(.920,.512),(.851,.302),(.690,.071),(.515,.030),(.420,.213),(.199,.474),(.571,.503)]
    inner=[(.797,.444),(.807,.322),(.776,.283),(.698,.232),(.606,.177),(.589,.230),(.711,.350),(.773,.412)]
    a=sample_poly(outer);b=sample_poly(inner);n=len(b)
    opening=[(.5671,.0983),(.5347,.1609),(.3882,.2817),(.4179,.2173)]
    verts,faces=constrained_fairing_surface(outer,inner,opening,side)
    main=solid_patch('R3 Curved main fairing with through intake '+str(side),verts,faces,'Apex_Pearl',.005)
    wall=[];faces=[]
    for depth in [0,.006,.041]:
        for y,z in b:wall.append((side*(fairing_x(y,z)-.003-depth),y,z))
    for k in range(2):
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    solid_patch('R3 Recessed black intake return '+str(side),wall,faces,'Apex_Graphite',.004)
    solid_patch('R3 Intake plenum shadow '+str(side),[(side*.173,y,z) for y,z in inner],[tuple(range(len(inner)))],'Apex_Graphite',.005,False)
    for i in range(17):
        t=i/16;y=.616+.155*t;z=.218+.150*t
        tube('R3 Recessed intake grille '+str(side)+' '+str(i),[(side*.198,y,z-.021),(side*.198,y,z+.021)],.0011,'Apex_Graphite',6)
    quad_patch('R3 Upper shoulder black reveal '+str(side),[(side*.130,.914,.398),(side*.188,.843,.294),(side*.160,.765,-.191),(side*.113,.789,-.226)],'Apex_Graphite',.005)
    shared_rear=(side*fairing_x(.420,.213),.420,.213);shared_tip=(side*fairing_x(.199,.474),.199,.474)
    quad_patch('R3 Belly sculpted outer volume '+str(side),[(side*.152,.387,-.348),shared_rear,shared_tip,(side*.097,.235,-.331)],'Apex_Graphite',.007)
    quad_patch('R3 Belly upper chine '+str(side),[(side*.126,.414,-.301),(side*fairing_x(.515,.030),.515,.030),shared_rear,(side*.152,.387,-.348)],'Apex_Graphite',.004)
    solid_patch('R3 Lower diagonal plenum '+str(side),[(side*(fairing_x(y,z)-.031),y,z) for y,z in opening],[tuple(range(len(opening)))],'Apex_Graphite',.003,False)
    lowerwall=[(side*(fairing_x(y,z)-depth),y,z) for depth in [.002,.031] for y,z in opening]
    solid_patch('R3 Lower diagonal black cavity wall '+str(side),lowerwall,[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)],'Apex_Graphite',.002)
    # Flush socket hardware reads as scale, not oversized decorated rivets.
    for i,(y,z) in enumerate([(.813,.463),(.690,.102),(.562,.078),(.307,.431)]):
        x=fairing_x(y,z);tube('R3 Fairing flush bolt '+str(side)+' '+str(i),[(side*x,y,z),(side*(x+.0018),y,z)],.0048,'Apex_Machined',10)
        tube('R3 Fairing bolt recess '+str(side)+' '+str(i),[(side*(x+.0019),y,z),(side*(x+.0025),y,z)],.0019,'Apex_Graphite',6)
    # Slim broad-faced cast spars; no circular tubular silhouette.
    centers=catmull([(side*.127,.919,.475),(side*.164,.844,.28),(side*.183,.756,.018),(side*.186,.654,-.18),(side*.17,.478,-.24)],4)
    profile=[(-.78,-1),(-1,-.78),(-1,.78),(-.78,1),(.78,1),(1,.78),(1,-.78),(.78,-1)];verts=[];faces=[]
    for k,p in enumerate(centers):
        direction=(centers[min(k+1,len(centers)-1)]-centers[max(0,k-1)]).normalized();up=direction.cross(Vector((1,0,0))).normalized()
        for u,v in profile:verts.append(p+Vector((1,0,0))*u*.022+up*v*.026)
        if k:
            for j in range(8):faces.append(((k-1)*8+j,(k-1)*8+(j+1)%8,k*8+(j+1)%8,k*8+j))
    faces.extend([tuple(reversed(range(8))),tuple((len(centers)-1)*8+j for j in range(8))]);final_mesh('R3 Broad faced tapered frame spar '+str(side),verts,faces,'Apex_Graphite',False)

loft('R3 Closed sculpted sump',[(-.35,.225,.258,.103),(-.18,.208,.257,.151),(.16,.190,.235,.165),(.47,.188,.202,.145)],[(0,1),(1,.84),(1,.4),(.7,0),(-.7,0),(-1,.4),(-1,.84)],'Apex_Graphite')

# One continuous moulded front skin per side, with matching optical boundary.
# All points share the same surface function; no floating brow/cheek overlays.
def nose_z(x,y):
    crown=max(0,(y-.952)/.064)
    return .835-.38*(y-.855)-.31*abs(x)-.18*crown**1.2

outer_xy=[(.012,.838),(.020,.918),(.105,1.016),(.217,.980),(.240,.920),(.229,.848)]
inner_xy=[(.025,.854),(.044,.906),(.177,.947),(.217,.928),(.222,.880),(.191,.855)]
for side in [-1,1]:
    outer=corner_fillets(outer_xy,.10,4);inner=corner_fillets(inner_xy,.12,4);n=len(outer);verts=[];faces=[]
    for k in range(8):
        t=k/7
        for j in range(n):
            x,y=outer[j]*(1-t)+inner[j]*t;verts.append((side*x,y,nose_z(x,y)))
            if k:faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    solid_patch('R3 Unified curved front cowl '+str(side),verts,faces,'Apex_Pearl',.005)
    outline=[Vector((side*x,y,nose_z(x,y))) for x,y in inner]
    center=sum(outline,Vector())/n;opening=[center+(p-center)*.945 for p in outline]
    ringfaces=[(j,(j+1)%n,n+(j+1)%n,n+j) for j in range(n)]
    solid_patch('R3 Moulded optical black lip '+str(side),outline+opening,ringfaces,'Apex_Graphite',.006)
    back=[p-Vector((0,0,.061)) for p in opening]
    solid_patch('R3 Closed dark headlight backing '+str(side),back,[tuple(range(n))],'Apex_Graphite',.004,False)
    solid_patch('R3 Optical cavity depth '+str(side),opening+back,ringfaces,'Apex_Graphite',.003)
    # A compound polycarbonate cover has varying normals, so a softbox does
    # not turn the entire flat aperture into a uniform white reflection.
    normal=Vector((side*.31,.38,1)).normalized();lens_center=sum(opening,Vector())/n;points=[];lensfaces=[]
    for k,scale in enumerate([1,.8,.6,.4,.2]):
        for p in opening:points.append(lens_center+(p-lens_center)*scale+normal*(.001+.006*(1-scale*scale)))
        if k:
            for j in range(n):lensfaces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    ci=len(points);points.append(lens_center+normal*.007)
    for j in range(n):lensfaces.append((4*n+j,4*n+(j+1)%n,ci))
    solid_patch('R3 Compound curved protective lens '+str(side),points,lensfaces,'Apex_Lens',.002,True)
    direction=Vector((side*.10,0,1)).normalized();p=Vector((side*.158,.900,nose_z(.158,.900)-.022))
    bowl('R3 Single projector bezel '+str(side),p,direction,[(-.020,.020),(-.018,.029),(-.005,.030),(-.001,.026),(-.003,.023),(-.018,.017)],'Apex_Machined')
    tube('R3 Single main projector '+str(side),[p-direction*.019,p-direction*.006],.019,'Apex_Lamp',40)
    bowl('R3 Projector lens lip '+str(side),p,direction,[(-.005,.020),(-.002,.021),(.000,.019),(-.001,.018)],'Apex_Graphite')
    # The outer lip lies beyond the lamp aperture and shares its lower edge
    # exactly with the main side fairing's upper edge.
    quad_patch('R3 Cowl side return '+str(side),[(side*.217,.980,nose_z(.217,.980)),(side*.240,.920,nose_z(.240,.920)),(side*fairing_x(.84,.765),.84,.765),(side*fairing_x(.920,.512),.920,.512)],'Apex_Pearl',.003)
    tube('R3 Mirror stalk '+str(side),[(side*.179,.982,.546),(side*.249,1.007,.508),(side*.291,1.052,.475)],.007,'Apex_Graphite',16)
    mirror=[(side*.278,1.039,.475),(side*.377,1.055,.467),(side*.384,1.095,.442),(side*.307,1.100,.430)]
    perimeter=corner_fillets(mirror,.12,5);mc=sum(perimeter,Vector())/len(perimeter);verts=[];faces=[];n=len(perimeter)
    for k,(scale,dz) in enumerate([(.88,.018),(1,.009),(1,-.020),(.90,-.027)]):
        verts.extend([mc+(p-mc)*scale+Vector((0,0,dz)) for p in perimeter])
        if k:
            for j in range(n):faces.append(((k-1)*n+j,(k-1)*n+(j+1)%n,k*n+(j+1)%n,k*n+j))
    faces.extend([tuple(reversed(range(n))),tuple(3*n+j for j in range(n))]);final_mesh('R3 Rounded trapezoid mirror case '+str(side),verts,faces,'Apex_Graphite')
    solid_patch('R3 Recessed rear mirror glass '+str(side),[mc+(p-mc)*.83+Vector((0,0,-.028)) for p in perimeter],[tuple(range(n))],'Apex_Machined',.002,False)

verts=[];faces=[]
for r in range(18):
    t=r/17;y=1.016-(1.016-.838)*t
    width=.020+(.105-.020)*(y-.918)/(.098) if y>=.918 else .012+(.020-.012)*(y-.838)/.080
    for j in range(13):
        x=(j/6-1)*width;verts.append((x,y,nose_z(x,y)+.0005))
        if r and j:k=r*13+j;faces.append((k-14,k-13,k,k-1))
solid_patch('R3 Continuous graphite centre spine',verts,faces,'Apex_Graphite',.004)

verts=[];faces=[]
for r in range(15):
    t=r/14
    for j in range(23):
        q=j/11-1;width=.151-.022*t
        base_y=.983-.011*q*q;base_z=nose_z(q*.151,base_y)+.002
        verts.append((q*width,base_y+.145*t-.009*q*q*t,base_z-.230*t))
        if r and j:k=r*23+j;faces.append((k-24,k-23,k,k-1))
solid_patch('R3 Swept attached smoked screen',verts,faces,'Apex_Glass',.003)
for side in [-1,1]:
    tube('R3 Screen fitted rim '+str(side),[(side*(.151-.022*t),.972+.136*t,nose_z(.151,.972)+.002-.230*t) for t in [i/16 for i in range(17)]],.0027,'Apex_Graphite',8)
tube('R3 Screen base seated gasket',[(q*.151,.983-.011*q*q,nose_z(q*.151,.983-.011*q*q)+.003) for q in [i/16-1 for i in range(33)]],.0033,'Apex_Graphite',8)

for name,center in [('Rear LED housing',(0,1.004,-.909)),('Continuous rear LED',(0,1.005,-.917))]:
    obj=bpy.data.objects[name];world=obj.matrix_world.copy();inv=world.inverted();actual=sum((world@v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
    for vertex in obj.data.vertices:vertex.co=inv@(world@vertex.co+coord(center)-actual)
    obj.data.update()
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    assert len(obj.data.uv_layers)==1,'Unexpected secondary UV ownership: '+obj.name
    obj.data.uv_layers.active.name='UV0_SurfaceMetres'
root['screen_rim_revision']=8
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=860;scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('APEX_R3_AUTHORED '+json.dumps({'removedR2Components':len(removed),'meshComponents':sum(o.type=='MESH' for o in root.children_recursive),'fixedSeatMetres':.82,'fixedWheelbaseMetres':1.43,'visualAccepted':False}))
