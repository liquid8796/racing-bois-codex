"""Sewn waistband, seam piping and articulated shoulder/elbow quilting."""
import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];PREFIX='RB_P06_Rider_L0_'
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
base=bpy.data.objects['AshV4_L0_Skin']
for key in base.data.shape_keys.key_blocks:key.value=0
bpy.context.view_layer.update()
cloth_index=next(i for i,m in enumerate(base.data.materials) if m.name=='AshV4_TailoredLeather_Source')
cloth_faces=[tuple(p.vertices) for p in base.data.polygons if p.material_index==cloth_index]
cloth_ids=set(i for f in cloth_faces for i in f)
cloth=BVHTree.FromPolygons([v.co for v in base.data.vertices],cloth_faces,all_triangles=False)
surface=BVHTree.FromPolygons([v.co for v in base.data.vertices],[tuple(p.vertices) for p in base.data.polygons],all_triangles=False)
kd=KDTree(len(cloth_ids))
for index in cloth_ids:kd.insert(base.data.vertices[index].co,index)
kd.balance()
leather=bpy.data.materials['AshV4_LeatherDetails_Source'];thread=bpy.data.materials['AshV2_OchreThread_Baked'];metal=bpy.data.materials['AshV2_AgedBrass_Baked']
collection=bpy.data.collections.new('AshV4_SewnDetails_Source');scene.collection.children.link(collection)
created=[]

def project(x,z,back=False,offset=.001):
    p,n,index,distance=cloth.ray_cast(Vector((x,1 if back else -1,z)),Vector((0,-1 if back else 1,0)),2)
    if p is None:raise RuntimeError('Cloth ray missed '+str((x,z,back)))
    return p+n*offset

def build(name,vertices,faces,material,uv=None):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj);obj.parent=rig;data.materials.append(material)
    layer=data.uv_layers.new(name='UV0');cache={}
    for poly in data.polygons:
        poly.use_smooth=True
        if uv:
            points=[uv[data.loops[i].vertex_index] for i in poly.loop_indices]
            area=abs(sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points))))
            if area>1e-12:
                for loop,point in zip(poly.loop_indices,points):layer.data[loop].uv=point
            else:
                for j,loop in enumerate(poly.loop_indices):layer.data[loop].uv=(.5+.45*math.cos(j*math.tau/len(points)),.5+.45*math.sin(j*math.tau/len(points)))
        else:
            n=poly.normal;t=n.orthogonal().normalized();b=n.cross(t).normalized()
            for loop in poly.loop_indices:
                p=data.vertices[data.loops[loop].vertex_index].co;layer.data[loop].uv=(p.dot(t)*8,p.dot(b)*8)
    for vertex in data.vertices:
        p,index,d=kd.find(vertex.co)
        weights=[(base.vertex_groups[g.group].name,g.weight) for g in base.data.vertices[index].groups if g.weight>.00001]
        total=sum(w for name,w in weights)
        for name,weight in weights:
            if name not in cache:cache[name]=obj.vertex_groups.new(name=name)
            cache[name].add([vertex.index],weight/total,'REPLACE')
    attr=data.attributes.new('AshV4_RestMeters','FLOAT_VECTOR','POINT')
    for vertex in data.vertices:attr.data[vertex.index].vector=vertex.co
    mod=obj.modifiers.new('Preserved Ash anatomical rig','ARMATURE');mod.object=rig
    created.append(obj);return obj

def piping(name,points,radius,material=thread,sides=5):
    vertices=[];faces=[];uv=[];length=0
    for i,p in enumerate(points):
        p=Vector(p)
        if i:length+=(p-Vector(points[i-1])).length
        axis=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        tangent=axis.orthogonal().normalized();normal=axis.cross(tangent).normalized()
        for j in range(sides):
            theta=math.tau*j/sides;vertices.append(p+radius*(tangent*math.cos(theta)+normal*math.sin(theta)));uv.append((j/sides,length*8))
            if i:faces.append(((i-1)*sides+j,(i-1)*sides+(j+1)%sides,i*sides+(j+1)%sides,i*sides+j))
    faces.append(tuple(range(sides-1,-1,-1)));faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    return build(name,vertices,faces,material,uv)

# Yoke panel double seams, ending at the actual collar/arm transitions.
for side in [-1,1]:
    for offset in [-.014,.014]:
        points=[]
        for i in range(28):
            x=.061+.152*i/27;z=1.483-.16*(x-.06)+offset
            points.append(project(side*x,z,offset=.0013))
        piping('AshV4_FrontYokeSeam',points,.00048)
    points=[project(side*(.013+.172*i/28),1.396-.006*math.sin(i/28*math.pi),offset=.0011) for i in range(29)]
    piping('AshV4_ChestCrossSeam',points,.00043)
    for dx in [.010,.014]:
        points=[project(side*dx,1.070+.420*i/51,offset=.0013) for i in range(52)]
        piping('AshV4_ZipDoubleTopstitch',points,.00042)
for offset in [-.018,.018]:
    points=[project(-.210+.420*i/56,1.467-.055*abs(-.210+.420*i/56)+offset,True,.0014) for i in range(57)]
    piping('AshV4_BackYokeSeam',points,.0005)

# A real sewn lower waistband follows the continuous shell, with thickness
# and a front opening at the zip. It is not a floating cylinder around hips.
vertices=[];normals=[];faces=[];uv=[];cols=96;rows=4
for row in range(rows):
    z=1.025+.042*row/(rows-1)
    for i in range(cols):
        theta=.035+(math.tau-.070)*i/(cols-1);direction=Vector((math.sin(theta),-math.cos(theta),0))
        center=Vector((0,-.015,z));p,n,index,d=cloth.ray_cast(center+direction*.5,-direction,1)
        if p is None:raise RuntimeError('Waistband did not meet cloth')
        vertices.append(p+n*.002);normals.append(n);uv.append((i/(cols-1),row/(rows-1)))
        if row and i:
            k=row*cols+i;faces.append((k-cols-1,k-cols,k,k-1))
outer_count=len(vertices)
vertices.extend([p-n*.0018 for p,n in zip(vertices[:],normals)])
uv.extend(uv[:])
faces.extend([tuple(i+outer_count for i in reversed(face)) for face in faces[:]])
border=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[r*cols for r in range(rows-2,0,-1)]
for i,a in enumerate(border):b=border[(i+1)%len(border)];faces.append((a,b,b+outer_count,a+outer_count))
build('AshV4_SewnWaistband',vertices,faces,leather,uv)
for row in [0,rows-1]:piping('AshV4_WaistbandTopstitch',[p+normals[row*cols+i]*.0008 for i,p in enumerate(vertices[row*cols:(row+1)*cols])],.00055)

# Quilting follows real shoulder/elbow surfaces. Pads themselves remain the
# fitted source geometry; narrow seams divide their manufactured chambers.
for side,sign in [('L',1),('R',-1)]:
    for part,distances,span in [('UpperArm_',[.003,.030,.057,.084,.108],.70),('Forearm_',[.005,.031,.057],.57)]:
        bone=rig.data.bones[PREFIX+part+side];axis=(bone.tail_local-bone.head_local).normalized()
        outward=Vector((sign,0,0));outward=(outward-axis*outward.dot(axis)).normalized();across=axis.cross(outward).normalized()
        for distance in distances:
            center=bone.head_local+axis*distance;points=[]
            for i in range(18):
                angle=-span+2*span*i/17;direction=outward*math.cos(angle)+across*math.sin(angle)
                p,n,index,d=surface.ray_cast(center+direction*.22,-direction,.35)
                if p is not None:points.append(p+n*.0014)
            if len(points)>8:piping('AshV4_Quilt_'+part+side,points,.00062)

for obj in created:obj['v4_detail']=True;obj['intentional_uv_tiling']=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_SEWN_DETAILS '+json.dumps({'parts':len(created),'vertices':sum(len(o.data.vertices) for o in created),'names':[o.name for o in created],'runtimeLodsNotYetMerged':True,'visualAccepted':False}))
