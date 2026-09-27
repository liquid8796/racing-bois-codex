import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_FittedFringe'];bpy.data.objects.remove(obj,do_unlink=True)
reports=[]
paths=[
 ((.051,-.130,1.759),(.051,-.158,1.739),(.015,-.165,1.739),(-.008,-.161,1.717)),
 ((.035,-.133,1.759),(.029,-.162,1.739),(-.009,-.164,1.738),(-.030,-.155,1.717)),
 ((.006,-.132,1.756),(-.014,-.160,1.740),(-.034,-.160,1.736),(-.045,-.150,1.714)),
 ((-.024,-.126,1.755),(-.048,-.151,1.737),(-.052,-.154,1.727),(-.060,-.140,1.706)),
 ((.061,-.123,1.747),(.070,-.142,1.730),(.060,-.151,1.725),(.048,-.149,1.712)),
 ((-.055,-.114,1.744),(-.070,-.136,1.720),(-.071,-.135,1.714),(-.069,-.125,1.698)),
 ((.047,-.131,1.756),(.020,-.162,1.742),(-.018,-.166,1.735),(-.012,-.159,1.724)),
 ((-.013,-.130,1.755),(-.032,-.155,1.737),(-.061,-.148,1.728),(-.055,-.142,1.717))]
collection=bpy.data.collections['AshV6_Equipment'];material=bpy.data.materials.new('AshV6_Fringe_Source');material.use_nodes=True;shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.011,.006,.0035,1);shader.inputs['Roughness'].default_value=.48
center=Vector((0,-.041,1.706));radii=Vector((.112,.124,.148))
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
for level,per,segments,sides in [(0,22,18,4),(1,12,14,4),(2,6,9,4)]:
 verts=[];faces=[];uv=[];adjusted=0
 for index,path in enumerate(paths):
  a,b,c,d=[Vector(p) for p in path]
  for strand in range(per):
   offset=(strand-(per-1)/2)*(.014/per);start=len(verts);phase=strand*2.399+index*.71;end=.80+.20*(.5+.5*math.sin(strand*1.71+index))
   for i in range(segments+1):
    t=i/segments*end;p=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
    tangent=(3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)).normalized()
    across=tangent.cross(Vector((0,-1,0))).normalized();p+=across*(offset*(1-.20*t)+.0015*math.sin(t*9+phase)*math.sin(t*math.pi));p.y+=.0014*math.sin(t*8+phase)*math.sin(t*math.pi);p.z+=.0022*math.sin(phase)*t*t
    q=Vector(((p.x-center.x)/radii.x,(p.y-center.y)/radii.y,(p.z-center.z)/radii.z));length=q.length
    theta=math.acos(max(-1,min(1,q.z/length)));phi=abs(math.atan2(q.x,-q.y))
    edge=1.27+.085*math.sin(min(1,phi/.70)*math.pi*.5)**2*(1-smooth((phi-.70)/.40))+.86*smooth((phi-.58)/.65)-.22*smooth((phi-1.75)/(math.pi-1.75))
    # A finite-width clearance band under the rolled edge, not just the
    # enamel surface. It prevents a root ending visibly through the rim.
    if theta<edge+.055 and length>.885:p=center+(p-center)*(.885/length);adjusted+=1
    aa=tangent.orthogonal().normalized();bb=tangent.cross(aa).normalized();radius=.00017*(1-.25*t)
    for j in range(sides):
     angle=math.tau*j/sides;verts.append(p+radius*(aa*math.cos(angle)+bb*math.sin(angle)));uv.append((j/sides,t))
     if i:faces.append((start+(i-1)*sides+j,start+(i-1)*sides+(j+1)%sides,start+i*sides+(j+1)%sides,start+i*sides+j))
   faces.extend([tuple(start+j for j in range(sides-1,-1,-1)),tuple(start+segments*sides+j for j in range(sides))])
 mesh=bpy.data.meshes.new('AshV6_Fringe');mesh.from_pydata(verts,[],faces);mesh.update();obj=bpy.data.objects.new('AshV6_L'+str(level)+'_FittedFringe',mesh);collection.objects.link(obj);obj.parent=rig;mesh.materials.append(material)
 layer=mesh.uv_layers.new(name='UV0')
 for p in mesh.polygons:
  p.use_smooth=True
  for j,i in enumerate(p.loop_indices):layer.data[i].uv=(.45+.03*math.cos(j*math.tau/len(p.vertices)),.45+.03*math.sin(j*math.tau/len(p.vertices)))
 group=obj.vertex_groups.new(name='RB_P06_Rider_L0_Head');group.add(list(range(len(verts))),1,'REPLACE');mod=obj.modifiers.new('Preserved head rig','ARMATURE');mod.object=rig
 obj.hide_render=level!=0;obj.hide_set(level!=0);reports.append({'lod':level,'strands':per*len(paths),'rootSamplesFitted':adjusted})
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_FRINGE '+json.dumps({'lods':reports,'oldBrowFibersRetained':True,'visualAccepted':False}))
