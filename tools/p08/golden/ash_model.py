"""Original Ash v2 character candidate, executed only through live Blender MCP.

Inspected reference: ArtSource/Concepts/P08/Golden/ash-v2.png. This recipe is an
authoring candidate, not a visual acceptance or production-ready declaration.
Coordinates are x lateral, y up, z forward in metres; the P06 reflection is
retained to bind the existing generic skeleton without renaming its paths.
"""
import bpy,bmesh,math,json
from mathutils import Vector,Quaternion

ROOT='D:/Project/Unity/racing-bois/'
SOURCE=ROOT+'ArtSource/P08/Golden/Ash/'
OUT=ROOT+'Assets/RacingBois/Art/P08/Golden/Ash/'
EVIDENCE=ROOT+'docs/p08/golden/ash/'
PREFIX='RB_P06_Rider_L0_'
NAME='RB_Golden_Ash'

def coord(p):return Vector((-p[0],-p[2],p[1]))
def semantic(p):return (-p.x,p.z,-p.y)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def gauss(value,center,span):return math.exp(-((value-center)/span)**2)

if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
# ash_open_rig.py loads the trusted rig in a separate MCP operation so the
# window/view layer context is settled before mesh Edit-mode operators run.
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.parent=None
for obj in list(bpy.data.objects):
    if obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
for mat in list(bpy.data.materials):
    if mat.users==0 and mat.name.startswith('Ash_'):bpy.data.materials.remove(mat)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
scene.render.resolution_percentage=100

root=bpy.data.objects.new(NAME,None);scene.collection.objects.link(root)
rig.name='RB_P06_Rider_Rig';rig.parent=root;rig.animation_data_clear()
for bone in rig.pose.bones:
    bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion((1,0,0,0))
if len(rig.data.bones)!=15:raise RuntimeError('Shared rider rig contract changed')

materials={}
for name in ['Ash_Skin','Ash_Jacket','Ash_Amber','Ash_Trousers','Ash_BootLeather','Ash_Helmet','Ash_Rubber','Ash_Hair','Ash_Metal','Ash_Eye','Ash_Iris','Ash_Lip']:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links;shader=nodes.get('Principled BSDF')
    images={}
    for kind in ('BaseColor','Normal','MetallicSmoothness','Roughness'):
        image=bpy.data.images.load(OUT+name+'_'+kind+'.png',check_existing=True)
        if kind!='BaseColor':image.colorspace_settings.name='Non-Color'
        image.pack();node=nodes.new('ShaderNodeTexImage');node.image=image;images[kind]=node
    links.new(images['BaseColor'].outputs['Color'],shader.inputs['Base Color'])
    links.new(images['Roughness'].outputs['Color'],shader.inputs['Roughness'])
    separate=nodes.new('ShaderNodeSeparateColor');links.new(images['MetallicSmoothness'].outputs['Color'],separate.inputs['Color'])
    links.new(separate.outputs['Red'],shader.inputs['Metallic'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.20 if name=='Ash_Skin' else .22
    links.new(images['Normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    if name=='Ash_Skin':shader.inputs['Subsurface Weight'].default_value=.08;shader.inputs['Subsurface Radius'].default_value=(1,.42,.21);shader.inputs['Specular IOR Level'].default_value=.23
    if name=='Ash_Helmet':shader.inputs['Coat Weight'].default_value=.3;shader.inputs['Coat Roughness'].default_value=.3
    materials[name]=mat

parts=[]
def active(obj):
    bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_viewport=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj

def clean(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    for face in obj.data.polygons:face.use_smooth=True

def unwrap(obj):
    active(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.015,area_weight=.7)
    bpy.ops.object.mode_set(mode='OBJECT');obj.data.uv_layers.active.name='UV0_OriginalSurface'

def blend_weights(point,role):
    x,y,z=point;side='L' if x<0 else 'R'
    if role=='head':return {'Head':1.0}
    if role=='neck':
        t=smooth((y-1.40)/.085);return {'Torso':1-t,'Head':t}
    if role=='jacket':
        if abs(x)>.175 and y<1.415:
            arm=smooth((abs(x)-.165)/.067)
            elbow=smooth((1.137-y)/.11)
            return {'Torso':1-arm,'UpperArm_'+side:arm*(1-elbow),'Forearm_'+side:arm*elbow}
        torso=smooth((y-.96)/.15);return {'Hip':1-torso,'Torso':torso}
    if role=='pants':
        hip=smooth((y-.82)/.13);knee=smooth((y-.445)/.12)
        return {'Hip':hip,'Thigh_'+side:(1-hip)*knee,'Shin_'+side:(1-hip)*(1-knee)}
    if role.startswith('fixed:'):return {role.split(':',1)[1]:1.0}
    if role=='boot':
        shin=smooth((y-.105)/.09);return {'Shin_'+side:shin,'Foot_'+side:1-shin}
    if role=='glove':
        forearm=smooth((y-.793)/.065);return {'Hand_'+side:1-forearm,'Forearm_'+side:forearm}
    raise RuntimeError(role)

def weight(obj,role):
    groups={}
    for vertex in obj.data.vertices:
        values={key:value for key,value in blend_weights(semantic(obj.matrix_world@vertex.co),role).items() if value>1e-6}
        total=sum(values.values())
        for name,value in values.items():
            if name not in groups:groups[name]=obj.vertex_groups.new(name=PREFIX+name)
            groups[name].add([vertex.index],value/total,'REPLACE')
    obj['anatomical_role']=role

def finish(obj,name,material,role=None,uv=True):
    obj.name=name;active(obj);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    clean(obj)
    if uv:unwrap(obj)
    obj.data.materials.clear();obj.data.materials.append(materials[material])
    if role:weight(obj,role)
    parts.append(obj);return obj

def mesh(name,vertices,faces,material,role=None,uv=True):
    data=bpy.data.meshes.new(name);data.from_pydata([coord(p) for p in vertices],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    return finish(obj,name,material,role,uv)

def ellipsoid(name,pos,radii,material,role=None,segments=24,rings=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=coord(pos))
    obj=bpy.context.object;obj.scale=(radii[0],radii[2],radii[1])
    return finish(obj,name,material,role)

def tube(name,points,radii,material,role=None,sides=8,cap=True):
    if not isinstance(radii,list):radii=[radii]*len(points)
    verts=[];faces=[]
    for i,point in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        tangent.normalize();helper=Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
        a=tangent.cross(helper).normalized();b=tangent.cross(a).normalized()
        for j in range(sides):verts.append(Vector(point)+radii[i]*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)))
        if i:
            for j in range(sides):faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    if cap:faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,material,role)

def loft(name,rings,material,role=None,sides=32,fold=0):
    vertices=[];faces=[]
    for row,(x,y,z,rx,rz) in enumerate(rings):
        for j in range(sides):
            theta=j*math.tau/sides
            relief=fold*(math.sin(y*75+theta*2.2)*.65+math.sin(y*131-theta*3.1)*.35)
            relief*=.3+.7*gauss(y,1.10,.16) if y>1 else .35+.65*gauss(y,.51,.11)
            vertices.append((x+(rx+relief)*math.sin(theta),y,z+(rz+relief)*math.cos(theta)))
        if row:
            for j in range(sides):faces.append(((row-1)*sides+j,(row-1)*sides+(j+1)%sides,row*sides+(j+1)%sides,row*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(rings)-1)*sides+j for j in range(sides))])
    return mesh(name,vertices,faces,material,role)

def joined(objects,name):
    active(objects[0])
    for obj in objects:obj.select_set(True)
    bpy.ops.object.join();obj=bpy.context.object;obj.name=name
    for old in objects:
        if old in parts:parts.remove(old)
    parts.append(obj);return obj

def continuous(objects,name,material,role,voxel=.005,ratio=.50):
    obj=joined(objects,name);active(obj)
    modifier=obj.modifiers.new('Continuous connected garment volume','REMESH');modifier.mode='VOXEL';modifier.voxel_size=voxel
    modifier.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier=obj.modifiers.new('Relax sewn surface','SMOOTH');modifier.factor=1.05;modifier.iterations=3
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier=obj.modifiers.new('Surface topology budget','DECIMATE');modifier.ratio=ratio
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    clean(obj);unwrap(obj);weight(obj,role);obj.data.materials.clear();obj.data.materials.append(materials[material])
    return obj

# Jacket shell: sewn shoulder junctions are unioned into the torso surface.
coat=[loft('Jacket torso construction',[(0,.945,0,.150,.096),(0,.98,0,.158,.101),(0,1.04,0,.154,.103),(0,1.11,0,.156,.110),(0,1.19,0,.172,.115),(0,1.28,0,.186,.112),(0,1.35,0,.188,.098),(0,1.39,0,.152,.081),(0,1.422,0,.072,.061)],'Ash_Jacket',sides=48,fold=.0035)]
for sign,side in [(-1,'L'),(1,'R')]:
    rings=[]
    for i in range(22):
        t=i/21;y=1.398-t*.573
        cx=sign*(.215+.023*smooth(t/.25))
        radius=.048+(1-t)*.010-.009*smooth((t-.75)/.25)
        rings.append((cx,y,.014*smooth((t-.5)/.5),radius,radius*.96))
    coat.append(loft('Connected sleeve '+side,rings,'Ash_Jacket',sides=32,fold=.004))
    coat.append(ellipsoid('Shoulder seam support '+side,(sign*.187,1.360,0),(.058,.035,.065),'Ash_Jacket'))
coat=continuous(coat,'Ash_Jacket_Continuous','Ash_Jacket','jacket',.0065,.34)

# Trousers are one continuous pelvis/crotch/leg surface, not capped cylinders.
pants=[loft('Trouser pelvis',[(0,.827,0,.124,.079),(0,.866,0,.145,.090),(0,.915,0,.150,.098),(0,.965,0,.149,.094)],'Ash_Trousers',sides=40,fold=.002)]
for sign,side in [(-1,'L'),(1,'R')]:
    rings=[]
    for i in range(28):
        t=i/27;y=.925-t*.746;rx=.087-(.087-.043)*t
        rx+=.007*gauss(y,.52,.055)
        rings.append((sign*.108,y,.006*gauss(y,.50,.09),rx,rx*.96))
    pants.append(loft('Connected trouser leg '+side,rings,'Ash_Trousers',sides=32,fold=.003))
pants=continuous(pants,'Ash_Trousers_Continuous','Ash_Trousers','pants',.0065,.32)

def jacket_surface(x,y,offset=.002):
    hit,location,normal,index=coat.ray_cast(coord((x,y,.6)),coord((0,0,-1)))
    return semantic(location)[2]+offset if hit else .04

# Constructed jacket shoulder/arm panels follow the garment surface and move
# with the same continuously blended weights, rather than staying on one bone.
for sign,side in [(-1,'L'),(1,'R')]:
    points=[(sign*.072,1.378,.077),(sign*.13,1.359,.091),(sign*.188,1.336,.082),(sign*.227,1.314,.063),(sign*.25,1.27,.054),(sign*.257,1.16,.051),(sign*.252,1.08,.054),(sign*.250,.982,.052),(sign*.25,.89,.040)]
    # Sewn stripe ribbon with its own panel width and edge seam.
    verts=[]
    for i,p in enumerate(points):
        width=.022 if i<4 else .014
        verts.extend([(p[0]-width,p[1],jacket_surface(p[0]-width,p[1])),(p[0]+width,p[1],jacket_surface(p[0]+width,p[1]))])
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(points)-1)]
    panel=mesh('Amber sewn shoulder and sleeve panel '+side,verts,faces,'Ash_Amber','jacket')
    active(panel);mod=panel.modifiers.new('Leather panel thickness','SOLIDIFY');mod.thickness=.0015;bpy.ops.object.modifier_apply(modifier=mod.name)
    tube('Shoulder panel stitch '+side,[(p[0]-sign*.014,p[1],jacket_surface(p[0]-sign*.014,p[1],.0035)) for p in points],.0007,'Ash_Amber','jacket',6)
    # Shaped low-profile shoulder armor and elbow patch, kept beneath cloth.
    for y in [1.316,1.331,1.346]:
        tube('Shoulder stitched rib '+side,[(sign*.218,y,jacket_surface(sign*.218,y,.003)),(sign*.244,y,jacket_surface(sign*.244,y,.003)),(sign*.259,y,jacket_surface(sign*.259,y,.003))],.0014,'Ash_Jacket','jacket',6)
    ellipsoid('Elbow reinforcement '+side,(sign*.237,1.082,-.049),(.047,.068,.013),'Ash_Jacket','jacket',24,14)
    tube('Outer sleeve seam '+side,[(sign*.286,1.277,0),(sign*.294,1.16,0),(sign*.290,1.08,.012),(sign*.282,.917,.018),(sign*.280,.84,.018)],.0011,'Ash_Amber','jacket',6)
    tube('Jacket front panel seam '+side,[(sign*.138,.964,.060),(sign*.143,1.075,.074),(sign*.162,1.205,.071),(sign*.176,1.306,.046)],.0011,'Ash_Amber','jacket',6)
    tube('Angled zip pocket '+side,[(sign*.106,1.087,.083),(sign*.121,1.19,.091)],.0021,'Ash_Metal','jacket',6)
    tube('Trouser side seam '+side,[(sign*.163,.933,.060),(sign*.174,.804,.019),(sign*.172,.65,.010),(sign*.175,.533,.008),(sign*.163,.42,.005),(sign*.15,.20,.005)],.0011,'Ash_Jacket','pants',6)
    # Articulated knee: flexible accordion ribs above a shaped pad.
    ellipsoid('Knee abrasion patch '+side,(sign*.108,.491,.071),(.055,.065,.013),'Ash_Jacket','pants',24,16)
    for i in range(7):
        y=.558+i*.008
        tube('Knee stretch fold '+side,[(sign*.108-.049,y,.060),(sign*.108,y+.003,.078),(sign*.108+.049,y,.060)],.0022,'Ash_Jacket','pants',8)
    # Cuffs and a real boot upper taper around the ankle, separate from sole.
    loft('Jacket fitted wrist cuff '+side,[(sign*.238,.827,.014,.049,.045),(sign*.238,.864,.014,.048,.045)],'Ash_Jacket','glove',32)
    boot_parts=[loft('Boot upper '+side,[(sign*.108,.06,.025,.055,.090),(sign*.108,.105,.008,.056,.069),(sign*.108,.19,0,.053,.055),(sign*.108,.27,0,.058,.059)],'Ash_BootLeather',sides=32),
                ellipsoid('Boot instep '+side,(sign*.108,.078,.055),(.060,.046,.120),'Ash_BootLeather',segments=32,rings=18),
                ellipsoid('Boot toe box '+side,(sign*.108,.063,.146),(.060,.030,.069),'Ash_BootLeather',segments=32,rings=16)]
    boot=continuous(boot_parts,'Ash_boot_upper_'+side,'Ash_BootLeather','boot',.0045,.35)
    # Profiled sole: toe is rounded and heel thickens towards the rear.
    outlines=[]
    for y in [.008,.019,.033]:
        ring=[]
        for j in range(40):
            a=j*math.tau/40;z=.059+.161*math.cos(a);width=.058+.008*max(0,math.cos(a))
            ring.append((sign*.108+width*math.sin(a),y,z))
        outlines.extend(ring)
    faces=[]
    for row in range(2):
        for j in range(40):faces.append((row*40+j,row*40+(j+1)%40,(row+1)*40+(j+1)%40,(row+1)*40+j))
    faces.extend([tuple(reversed(range(40))),tuple(range(80,120))])
    mesh('Boot rubber welt sole '+side,outlines,faces,'Ash_Rubber','boot')
    for y in [.137,.201,.246]:
        points=[(sign*.108+.059*math.sin(a),y,.005+.060*math.cos(a)) for a in [math.tau*j/40 for j in range(41)]]
        tube('Boot leather strap '+side,points,.006,'Ash_BootLeather','boot',8)
        p=(sign*(.108+.059),y,.007)
        tube('Boot strap buckle '+side,[(p[0],y-.010,-.010),(p[0],y+.010,-.010),(p[0],y+.010,.024),(p[0],y-.010,.024),(p[0],y-.010,-.010)],.0026,'Ash_Metal','boot',8)
    tube('Toe cap double seam '+side,[(sign*.108-.054,.072,.143),(sign*.108-.031,.097,.136),(sign*.108,.105,.131),(sign*.108+.031,.097,.136),(sign*.108+.054,.072,.143)],.0015,'Ash_Amber','boot',6)
    # Glove palm, four tapered curled fingers and opposing thumb are fused to
    # one anatomical volume. Finger joints retain curved rather than ball forms.
    glove_parts=[ellipsoid('Glove palm construction '+side,(sign*.238,.788,.019),(.038,.046,.025),'Ash_Jacket',segments=24,rings=16)]
    for j in range(4):
        xx=sign*.238+(j-1.5)*.017
        length=[.047,.058,.054,.043][j]
        points=[(xx,.778,.015),(xx,.757,.021),(xx,.746-length*.25,.035),(xx,.756-length*.65,.053),(xx,.77-length,.057)]
        glove_parts.append(tube('Glove finger '+side+str(j),points,[.0093,.0095,.0085,.0078,.0067],'Ash_Jacket',sides=12))
    glove_parts.append(tube('Opposing thumb '+side,[(sign*.210,.808,.020),(sign*.190,.790,.026),(sign*.189,.771,.043),(sign*.202,.756,.052)],[.014,.013,.0105,.008],'Ash_Jacket',sides=14))
    continuous(glove_parts,'Ash_glove_connected_'+side,'Ash_Jacket','glove',.0028,.42)
    for j in range(4):
        xx=sign*.238+(j-1.5)*.017
        ellipsoid('Glove knuckle leather '+side+str(j),(xx,.788,-.006),(.010,.012,.006),'Ash_Rubber','glove',16,8)
        tube('Glove finger stitch '+side+str(j),[(xx-.005,.782,-.003),(xx-.005,.759,.006),(xx-.005,.744,.019)],.0007,'Ash_Amber','glove',5)

# Waist band and closure hardware remain flush to the garment.
loft('Jacket hem band',[(0,.95,0,.153,.099),(0,.986,0,.157,.104)],'Ash_Jacket','jacket',48)
tube('Jacket center closure',[(0,.957,.104),(0,1.08,.113),(0,1.23,.121),(0,1.37,.086),(0,1.407,.062)],.0022,'Ash_Metal','jacket',8)
for i in range(47):
    y=.97+i*.0089;z=.102+.017*gauss(y,1.2,.18)
    tube('Zipper teeth '+str(i),[(-.003,y,z),(0,y+.001,z+.003),(.003,y,z)],.00075,'Ash_Metal','jacket',5)
loft('Open leather collar',[(0,1.388,0,.076,.066),(0,1.434,0,.068,.060)],'Ash_Jacket','neck',48)
loft('Anatomical neck',[(0,1.403,0,.052,.049),(0,1.453,.001,.052,.049),(0,1.516,.010,.048,.047)],'Ash_Skin','neck',40)

# Continuous adult face. The section table sets a 24 cm head, angular jaw and
# skull; local sculpt displacement creates actual nose/cheek/lip/eye sockets.
sections=[(1.498,.031,.023,.044),(1.508,.044,.018,.050),(1.523,.060,.005,.069),(1.542,.070,-.004,.082),(1.563,.076,-.007,.087),(1.586,.080,-.010,.091),(1.610,.080,-.011,.091),(1.635,.079,-.012,.091),(1.660,.077,-.012,.090),(1.685,.077,-.015,.091),(1.707,.072,-.019,.086),(1.724,.060,-.020,.073),(1.738,.038,-.023,.049),(1.744,.002,-.025,.003)]
def section(y):
    for i in range(len(sections)-1):
        a,b=sections[i:i+2]
        if a[0]<=y<=b[0]:
            t=(y-a[0])/(b[0]-a[0]);return tuple(a[k]*(1-t)+b[k]*t for k in range(1,4))
    return sections[-1][1:]
def face_depth(x,y,base):
    nose=.031*gauss(x,0,.014)*gauss(y,1.610,.038)+.015*gauss(x,0,.019)*gauss(y,1.589,.012)+.004*gauss(abs(x),.012,.007)*gauss(y,1.588,.009)
    cheek=.008*gauss(abs(x),.053,.018)*gauss(y,1.598,.020)
    socket=-.012*gauss(abs(x),.039,.021)*gauss(y,1.643,.012)
    brow=.008*gauss(abs(x),.039,.026)*gauss(y,1.662,.012)
    lip=.0048*gauss(x,0,.029)*(gauss(y,1.558,.005)+gauss(y,1.550,.005))
    chin=.008*gauss(x,0,.033)*gauss(y,1.517,.011)
    return base+nose+cheek+socket+brow+lip+chin
verts=[];faces=[];nr=72;ns=96
for row in range(nr):
    y=1.498+(1.744-1.498)*row/(nr-1);width,center,depth=section(y)
    for j in range(ns):
        theta=(j/ns-.5)*math.tau;x=width*math.sin(theta);z=center+depth*math.cos(theta)
        if math.cos(theta)>0:z=face_depth(x,y,z)
        x+=.0007*gauss(y,1.56,.08)*math.cos(theta)*math.sin(theta*2)
        verts.append((x,y,z))
    if row:
        for j in range(ns):faces.append(((row-1)*ns+j,(row-1)*ns+(j+1)%ns,row*ns+(j+1)%ns,row*ns+j))
faces.extend([tuple(reversed(range(ns))),tuple((nr-1)*ns+j for j in range(ns))])
head=mesh('Ash_continuous_facial_anatomy',verts,faces,'Ash_Skin','head',False)
uv=head.data.uv_layers.new(name='UV0_DedicatedHead')
for polygon in head.data.polygons:
    js=[head.data.loops[i].vertex_index%ns for i in polygon.loop_indices];crosses=max(js)-min(js)>ns/2
    for li in polygon.loop_indices:
        vi=head.data.loops[li].vertex_index;j=vi%ns
        uv.data[li].uv=(1.0 if crosses and j==0 else j/ns,1-(vi//ns)/(nr-1))

for sign in [-1,1]:
    # Embedded eyes and anatomically shaped lids; eye spheres are never used
    # for cheeks, nose or an entire exposed face.
    cx=sign*.0375;cy=1.644;cz=.054
    ellipsoid('Sclera', (cx,cy,cz),(.0153,.0087,.008),'Ash_Eye','head',32,20)
    ellipsoid('Brown iris',(cx,cy+.0003,.0612),(.0052,.0052,.0013),'Ash_Iris','head',24,16)
    ellipsoid('Pupil',(cx,cy+.0004,.0624),(.0022,.0024,.0005),'Ash_Hair','head',20,12)
    upper=[];lower=[]
    for j in range(17):
        t=j/16;xx=cx+(t-.5)*.034
        upper.append((xx,cy+.0005+.0048*math.sin(math.pi*t),.053+.009*math.sin(math.pi*t)))
        lower.append((xx,cy+.0005-.0032*math.sin(math.pi*t),.053+.009*math.sin(math.pi*t)))
    tube('Upper eyelid',upper,[.0014]*17,'Ash_Skin','head',8)
    tube('Lower eyelid',lower,[.0010]*17,'Ash_Skin','head',8)
    brow=[]
    for j in range(17):
        t=j/16;xx=cx+sign*(t-.5)*.043;yy=1.666+.004*math.sin(math.pi*t)
        width,center,depth=section(yy);base=center+depth*math.sqrt(max(0,1-(xx/width)**2));zz=face_depth(xx,yy,base)+.001
        brow.extend([(xx,yy,zz),(xx,yy+.0022*math.sin(math.pi*t),zz+.0005)])
    mesh('Tapered brow hair',brow,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(16)],'Ash_Hair','head')
    ellipsoid('Nostril recess',(sign*.010,1.581,.103),(.0035,.0015,.0016),'Ash_Hair','head',20,12)
    # Ear cartilage surface: tapered leaf with depressed concha and raised helix.
    ear=[];earfaces=[];count=36;rows=7
    for r in range(rows):
        t=r/(rows-1)
        for j in range(count):
            angle=j*math.tau/count
            xx=sign*(.080+.019*math.sin(math.pi*t)*(.7+.3*math.cos(angle)))
            yy=1.622+t*.031*math.cos(angle)
            zz=-.003+t*.017*math.sin(angle)
            ear.append((xx,yy,zz))
        if r:
            for j in range(count):earfaces.append(((r-1)*count+j,(r-1)*count+(j+1)%count,r*count+(j+1)%count,r*count+j))
    earobj=mesh('Ear helix and concha',ear,earfaces,'Ash_Skin','head')
    active(earobj);mod=earobj.modifiers.new('Ear cartilage thickness','SOLIDIFY');mod.thickness=.003;bpy.ops.object.modifier_apply(modifier=mod.name)
    tube('Ear inner antihelix',[(sign*.091,1.641,-.006),(sign*.094,1.624,-.006),(sign*.090,1.610,.003)],.003,'Ash_Skin','head',10)

# Soft vermilion geometry makes expression shapes tangible without giant lips.
for label,y,curve,depth in [('upper',1.557,.0008,.081),('lower',1.552,-.0010,.081)]:
    pts=[]
    for j in range(25):
        t=j/24;xx=(t-.5)*.058
        pts.append((xx,y+curve*math.sin(math.pi*t)+(.0007*math.cos(t*math.pi*4) if label=='upper' else 0),depth+.010*math.sin(math.pi*t)))
    tube('Natural '+label+' lip',pts,[.0006+.0006*math.sin(math.pi*j/24) for j in range(25)],'Ash_Lip','head',8)
tube('Closed mouth line',[(-.025,1.555,.082),(-.014,1.555,.089),(0,1.5545,.092),(.014,1.555,.089),(.025,1.555,.082)],.0003,'Ash_Lip','head',6)

# Dark cropped hair follows the skull. Crown is largely under the open helmet;
# tapered sweeps at forehead/temples provide a natural asymmetrical hairline.
for i in range(32):
    angle=(i/32)*math.tau
    pos=(.074*math.sin(angle),1.704+.009*math.sin(i*2.1),-.024+.072*math.cos(angle))
    direction=1 if math.sin(angle)>0 else -1
    points=[pos,(pos[0]+direction*.006,pos[1]-.008,pos[2]+.006),(pos[0]+direction*.009,pos[1]-.027,pos[2]+.010)]
    tube('Tapered hair sweep '+str(i),points,[.0032,.0028,.0004],'Ash_Hair','head',8)
for i in range(29):
    x=-.065+i*.0046
    tube('Forehead swept fringe '+str(i),[(x,1.711,.065),(x-.009,1.696,.077),(x-.014,1.682+.006*math.sin(i*.8),.076)],[.0031,.0024,.0004],'Ash_Hair','head',8)

# An actual open-face shell: front lower aperture remains empty. Its upper
# sphere sector blends to low side/rear coverage, leaving the face visible.
def helmet_shell(name,offset,material):
    verts=[];faces=[];rows=22;cols=80
    for row in range(rows):
        t=row/(rows-1)
        for j in range(cols):
            phi=(j/cols-.5)*math.tau
            # Open front above eyebrows; sides/rear extend below the ears.
            bottom=.39-.90*smooth((abs(phi)-.67)/.8)
            latitude=bottom+(math.pi/2-bottom)*t
            verts.append(((.106+offset)*math.cos(latitude)*math.sin(phi),1.678+(.132+offset)*math.sin(latitude),-.028+(.120+offset)*math.cos(latitude)*math.cos(phi)))
        if row:
            for j in range(cols):faces.append(((row-1)*cols+j,(row-1)*cols+(j+1)%cols,row*cols+(j+1)%cols,row*cols+j))
    obj=mesh(name,verts,faces,material,'head')
    active(obj);mod=obj.modifiers.new('Real shell thickness','SOLIDIFY');mod.thickness=.0035;mod.offset=-1;bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj
helmet_shell('Ivory open face helmet shell',.007,'Ash_Helmet')
helmet_shell('Helmet black energy absorbing liner',-.001,'Ash_Rubber')
for sign in [-1,1]:
    tube('Helmet padded cheek rim',[(sign*.085,1.691,.063),(sign*.099,1.672,.052),(sign*.104,1.646,.037),(sign*.107,1.62,.025),(sign*.103,1.603,.011),(sign*.091,1.595,-.022)],.0055,'Ash_Rubber','head',12)
    tube('Adjustable chin strap',[(sign*.097,1.614,.018),(sign*.094,1.589,.023),(sign*.080,1.553,.029),(sign*.058,1.526,.035),(sign*.029,1.511,.039),(0,1.507,.041)],.0024,'Ash_BootLeather','head',10)
    for y,z in [(1.640,.025),(1.703,.057)]:
        ellipsoid('Helmet rivet',(sign*.104,y,z),(.003,.003,.002),'Ash_Metal','head',16,10)

# Goggles parked over the helmet: twin curved frames, lens inset and bridge.
for sign in [-1,1]:
    center=(sign*.052,1.769,.071)
    points=[]
    for j in range(49):
        a=math.tau*j/48
        points.append((center[0]+.040*math.cos(a),center[1]+.025*math.sin(a),center[2]-.008*abs(math.cos(a))))
    tube('Raised goggles leather frame',points,.006,'Ash_BootLeather','head',10)
    tube('Raised goggles metal edge',[(p[0],p[1],p[2]+.004) for p in points],.0018,'Ash_Metal','head',8)
    ellipsoid('Raised amber lens',(center[0],center[1],center[2]),(.035,.021,.004),'Ash_Iris','head',32,18)
tube('Goggle nose bridge',[(-.013,1.773,.076),(0,1.767,.082),(.013,1.773,.076)],.005,'Ash_BootLeather','head',10)
tube('Elastic goggle strap',[(-.097,1.77,.045),(-.114,1.754,-.006),(-.101,1.734,-.080),(0,1.726,-.145),(.101,1.734,-.080),(.114,1.754,-.006),(.097,1.77,.045)],.006,'Ash_Rubber','head',10)

# Rest candidate, three independent topology levels. Geometry is constructed
# before adding facial shape keys, so exported shape data stays valid.
body=joined(parts[:],'Ash_L0_Skin')
active(body);scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');body.parent=rig
clean(body)
for level,ratio in [(1,.46),(2,.18)]:
    obj=body.copy();obj.data=body.data.copy();scene.collection.objects.link(obj);obj.name='Ash_L'+str(level)+'_Skin'
    active(obj);mod=obj.modifiers.new('Distance topology reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name);clean(obj);obj.hide_render=True

for obj in [o for o in rig.children if o.type=='MESH']:
    # Normalise after joins and simplification. Keep at most four significant
    # influences, preserving continuous shoulder/hip blending.
    for vertex in obj.data.vertices:
        ranked=sorted([(g.weight,g.group) for g in vertex.groups if g.weight>1e-7],reverse=True)[:4]
        influences=[(index,value) for value,index in ranked]
        total=sum(w for _,w in influences)
        if total<=0:raise RuntimeError('Unweighted Ash vertex')
        previous_groups=[g.group for g in vertex.groups]
        for index in previous_groups:obj.vertex_groups[index].remove([vertex.index])
        for index,value in influences:obj.vertex_groups[index].add([vertex.index],value/total,'REPLACE')
    obj.shape_key_add(name='Basis');happy=obj.shape_key_add(name='Happy');focused=obj.shape_key_add(name='Focused')
    for vertex in obj.data.vertices:
        x,y,z=semantic(vertex.co)
        if 1.539<y<1.574 and z>.068 and abs(x)<.038:
            happy.data[vertex.index].co.z+=.006*min(1,(abs(x)/.030)**1.5)*gauss(y,1.556,.017)
        if 1.658<y<1.681 and z>.045 and abs(x)<.072:
            focused.data[vertex.index].co.z-=.0035*gauss(abs(x),.023,.029)
        if 1.542<y<1.563 and z>.075 and abs(x)<.035:
            focused.data[vertex.index].co.x*=.985
    mod=obj.modifiers.new('Generic fifteen bone deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False

def marker(name,pos):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=root;obj.location=coord(pos)
marker('Forward',(0,0,.6));marker('Ground_L',(-.108,0,.06));marker('Ground_R',(.108,0,.06))
active(root)
for obj in root.children_recursive:obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=OUT+NAME+'.fbx',use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
for obj in root.children_recursive:
    if obj.type=='MESH':obj.hide_render='_L0_' not in obj.name
world=bpy.data.worlds.new('Ash neutral inspection world');world.use_nodes=True;scene.world=world
world.node_tree.nodes.get('Background').inputs[0].default_value=(.12,.14,.17,1);world.node_tree.nodes.get('Background').inputs[1].default_value=.45
target=(0,1.03,0)
for name,position,power,size in [('Key',(2.5,3.5,3.0),450,3),('Fill',(-2.5,2.2,2),220,3),('Rim',(-1.4,3,-2),550,2)]:
    data=bpy.data.lights.new('Ash_'+name,'AREA');obj=bpy.data.objects.new('Ash_'+name,data);scene.collection.objects.link(obj)
    obj.location=coord(position);obj.rotation_euler=(coord(target)-obj.location).to_track_quat('-Z','Y').to_euler();data.energy=power;data.shape='DISK';data.size=size
camera_data=bpy.data.cameras.new('Ash_ReviewCamera');camera=bpy.data.objects.new('Ash_ReviewCamera',camera_data);scene.collection.objects.link(camera)
camera.location=coord((1.7,1.12,3.5));camera.rotation_euler=(coord((0,.96,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=75;scene.camera=camera
scene.render.resolution_x=1000;scene.render.resolution_y=1300
scene.render.filepath=EVIDENCE+'ash-fullbody.png';scene.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+NAME+'.blend')
records=[]
for obj in rig.children:
    if obj.type!='MESH':continue
    obj.data.calc_loop_triangles();records.append({'name':obj.name,'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),'materials':[m.name for m in obj.data.materials]})
print('ASH_CANDIDATE_AUTHORED '+json.dumps({'source':SOURCE+NAME+'.blend','fbx':OUT+NAME+'.fbx','meshes':records,'visualAcceptance':'pending actual inspection','productionReady':False}))
