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
collection=bpy.data.collections['AshV4_SewnDetails_Source']
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


assert bpy.data.objects.get('AshV4_PantsFlySeam') is None
for x in [.007,.012]:
    points=[project(x,1.004-.115*i/24,offset=.0013) for i in range(25)]
    piping('AshV4_PantsFlySeam',points,.00045)
for sign in [-1,1]:
    points=[project(sign*(.078+.072*i/27),1.007-.066*i/27,offset=.0013) for i in range(28)]
    piping('AshV4_PocketWelt',points,.00065,leather,6)
    points=[project(sign*(.083+.072*i/27),1.007-.066*i/27,offset=.0020) for i in range(28)]
    piping('AshV4_PocketWeltStitch',points,.00042)
    points=[]
    for i in range(36):
        t=i/35;x=sign*(.174+.025*math.sin(t*math.pi));z=.902-.278*t
        p,n,index,d=cloth.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)
        if p is not None:points.append(p+n*.0012)
    if len(points)>12:piping('AshV4_ThighPanelSeam',points,.0005)
    points=[project(sign*(.060+.085*i/25),.948-.024*math.sin(i/25*math.pi),True,.0018) for i in range(26)]
    piping('AshV4_RearPocketTop',points,.0007,leather,6)
# Curved overlapping collar tab. It bridges the neck opening instead of
# treating two disconnected collar ends as a finished fastened jacket.
vertices=[];faces=[];uv=[]
for row in range(4):
    for i in range(13):
        x=-.046+.073*i/12;z=1.544+.021*row/3
        vertices.append((x,-.096+.012*(x/.074)**2,z));uv.append((i/12,row/3))
        if row and i:
            k=row*13+i;faces.append((k-14,k-13,k,k-1))
collar=build('AshV4_CollarOverlapTab',vertices,faces,leather,uv)
active=collar
bpy.ops.object.select_all(action='DESELECT');active.select_set(True);bpy.context.view_layer.objects.active=active
solid=active.modifiers.new('Sewn collar tab thickness','SOLIDIFY');solid.thickness=.0022
bpy.ops.object.modifier_move_up(modifier=solid.name);bpy.ops.object.modifier_apply(modifier=solid.name)
piping('AshV4_CollarOverlapStitch',[Vector(p)+Vector((0,-.0008,0)) for p in vertices[-13:]],.00045)
center=Vector((-.021,-.097,1.555));verts=[];faces=[]
for side in [-1,1]:
    for i in range(24):
        theta=i*math.tau/24;verts.append(center+Vector((.0055*math.cos(theta),side*.0011,.0055*math.sin(theta))))
for i in range(24):j=(i+1)%24;faces.append((i,j,j+24,i+24))
faces.extend([tuple(range(23,-1,-1)),tuple(range(24,48))])
build('AshV4_CollarSnapVisible',verts,faces,metal)
for obj in created:obj['v4_detail']=True;obj['intentional_uv_tiling']=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_PATTERN_FINISH '+json.dumps({'parts':len(created),'vertices':sum(len(o.data.vertices) for o in created),'visualAccepted':False}))
