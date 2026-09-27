import bpy,math,json,random
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
collection=bpy.data.collections['AshV4_HairDetails_Source']
for obj in list(collection.objects):
    assert obj.get('v4_hair_detail',False)
    bpy.data.objects.remove(obj,do_unlink=True)
hair=bpy.data.materials['AshV4_Forelock_Source'];nodes=hair.node_tree.nodes;links=hair.node_tree.links;bs=nodes['Principled BSDF']
for link in list(bs.inputs['Base Color'].links):links.remove(link)
bs.inputs['Base Color'].default_value=(.019,.012,.008,1);bs.inputs['Roughness'].default_value=.68
rng=random.Random(48219)
paths=[
 ((.057,-.121,1.783),(.078,-.154,1.759),(.046,-.169,1.750),(.014,-.157,1.728)),
 ((.028,-.117,1.788),(.045,-.159,1.769),(.005,-.170,1.751),(-.029,-.153,1.728)),
 ((-.005,-.112,1.791),(-.014,-.160,1.772),(-.051,-.167,1.749),(-.068,-.147,1.711)),
 ((-.042,-.106,1.786),(-.066,-.144,1.765),(-.070,-.160,1.739),(-.080,-.132,1.699)),
 ((.070,-.088,1.766),(.091,-.123,1.743),(.091,-.137,1.716),(.084,-.114,1.692)),
 ((-.070,-.090,1.760),(-.097,-.122,1.732),(-.092,-.133,1.707),(-.085,-.109,1.683)),
 ((.043,-.118,1.782),(.063,-.164,1.761),(.011,-.170,1.750),(-.011,-.155,1.733)),
 ((-.020,-.107,1.792),(-.019,-.162,1.774),(-.054,-.165,1.759),(-.057,-.153,1.731))]
fibers=[]
for path in paths:
    a,b,c,d=[Vector(p) for p in path]
    for strand in range(23):
        offset=(strand-11)*.00042;phase=rng.uniform(0,math.tau);end=rng.uniform(.88,1)
        points=[]
        for i in range(21):
            t=i/20*end;p=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
            tangent=(3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)).normalized()
            across=tangent.cross(Vector((0,-1,0))).normalized()
            p+=across*(offset*(1-.58*t)+.00065*math.sin(7*t+phase)*math.sin(math.pi*t))
            p.y-=.0007*math.sin(6*t+phase)*math.sin(math.pi*t)
            points.append(p)
        fibers.append((points,rng.uniform(.00010,.00015)))
# Fill the broken alpha-brow gaps with anatomically placed short fibers.
base=bpy.data.objects['AshV4_L0_Skin'];skin_faces=[tuple(p.vertices) for p in base.data.polygons if base.data.materials[p.material_index].name=='AshV4_Skin_Source']
skin_tree=BVHTree.FromPolygons([v.co for v in base.data.vertices],skin_faces,all_triangles=False)
for sign in [-1,1]:
    for i in range(64):
        t=i/63;x=sign*(.013+.052*t);z=1.707-.004*t+.0018*math.sin(t*math.pi)
        p,n,index,distance=skin_tree.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),1)
        if p is None:continue
        p+=n*.00045
        direction=Vector((sign*(.0018+.0015*t),-.0003,.0022-.0014*t))
        fibers.append(([p-direction*.4,p,p+direction*.6,p+direction],.000095))
vertices=[];faces=[];uv=[];sides=4
for strand,(points,radius) in enumerate(fibers):
    start=len(vertices)
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();a=tangent.orthogonal().normalized();b=tangent.cross(a).normalized()
        r=max(.000115,radius*(1-.60*(i/(len(points)-1))**4))
        for j in range(sides):
            angle=j*math.tau/sides;vertices.append(p+r*(a*math.cos(angle)+b*math.sin(angle)));uv.append((j/sides,i/(len(points)-1)))
            if i:faces.append((start+(i-1)*sides+j,start+(i-1)*sides+(j+1)%sides,start+i*sides+(j+1)%sides,start+i*sides+j))
    faces.append(tuple(start+j for j in range(sides-1,-1,-1)));faces.append(tuple(start+(len(points)-1)*sides+j for j in range(sides)))
data=bpy.data.meshes.new('AshV4_AuthoredHairFibers');data.from_pydata(vertices,[],faces);data.update()
obj=bpy.data.objects.new(data.name,data);collection.objects.link(obj);obj.parent=rig;data.materials.append(hair)
layer=data.uv_layers.new(name='UV0')
for p in data.polygons:
    p.use_smooth=True
    pts=[uv[data.loops[i].vertex_index] for i in p.loop_indices]
    if len({v[1] for v in pts})==1:
        for j,i in enumerate(p.loop_indices):layer.data[i].uv=(.5+.4*math.cos(j*math.tau/len(pts)),.5+.4*math.sin(j*math.tau/len(pts)))
    else:
        for i,point in zip(p.loop_indices,pts):layer.data[i].uv=point
attr=data.attributes.new('AshV4_RestMeters','FLOAT_VECTOR','POINT')
for v in data.vertices:attr.data[v.index].vector=v.co
group=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');group.add(list(range(len(vertices))),1,'REPLACE')
mod=obj.modifiers.new('Preserved Ash head deformation','ARMATURE');mod.object=rig;obj['v4_hair_detail']=True;obj['intentional_uv_tiling']=True
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_HAIR_FIBERS '+json.dumps({'fibers':len(fibers),'vertices':len(vertices),'oldRigidRibbonsRemoved':True,'rootBone':'RB_P06_Rider_L0_Head','fidelityAccepted':False}))
