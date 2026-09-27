"""Remove intersecting obsolete forehead cards, author a fitted continuous fringe."""
import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
reports=[]
for level in range(3):
 obj=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];old=obj.data
 assert not obj.get('v6_forelock_replacement',False)
 keep=[];removed={}
 for p in old.polygons:
  role=old.materials[p.material_index].name;points=[old.vertices[i].co for i in p.vertices]
  discard=role=='AshV2_HairFibers_Baked' or (role=='AshV4_Forelocks_Baked' and max(v.z for v in points)>1.718)
  discard=discard or (role=='AshV2_Hair_Baked' and min(v.y for v in points)<-.100 and max(v.z for v in points)>1.700)
  if discard:removed[role]=removed.get(role,0)+1
  else:keep.append(p)
 used=sorted(set(i for p in keep for i in p.vertices));mapping={v:i for i,v in enumerate(used)}
 positions=[old.vertices[i].co.copy() for i in used]
 weights=[[(obj.vertex_groups[g.group].name,g.weight) for g in old.vertices[i].groups] for i in used]
 expressions={k.name:[k.data[i].co.copy() for i in used] for k in old.shape_keys.key_blocks}
 faces=[(tuple(mapping[i] for i in p.vertices),p.material_index,p.use_smooth) for p in keep]
 uvs={l.name:[[l.data[i].uv.copy() for i in p.loop_indices] for p in keep] for l in old.uv_layers}
 mats=list(old.materials);names=[g.name for g in obj.vertex_groups]
 obj.shape_key_clear();mesh=bpy.data.meshes.new(obj.name+'_CleanFringe');mesh.from_pydata(positions,[],[f[0] for f in faces]);mesh.update();obj.data=mesh
 obj.vertex_groups.clear()
 for name in names:obj.vertex_groups.new(name=name)
 for mat in mats:mesh.materials.append(mat)
 for p,data in zip(mesh.polygons,faces):p.material_index=data[1];p.use_smooth=data[2]
 for name,values in uvs.items():
  layer=mesh.uv_layers.new(name=name)
  for p,points in zip(mesh.polygons,values):
   for loop,point in zip(p.loop_indices,points):layer.data[loop].uv=point
 for i,values in enumerate(weights):
  for name,w in values:obj.vertex_groups[name].add([i],w,'REPLACE')
 for name,coordinates in expressions.items():
  key=obj.shape_key_add(name=name,from_mix=False);key.value=0
  for v,co in zip(key.data,coordinates):v.co=co
 obj['v6_forelock_replacement']=True;reports.append({'lod':level,'obsoleteFacesRemoved':removed})
paths=[
 ((.051,-.130,1.759),(.051,-.158,1.739),(.015,-.165,1.739),(-.008,-.161,1.717)),
 ((.035,-.133,1.759),(.029,-.162,1.739),(-.009,-.164,1.738),(-.030,-.155,1.717)),
 ((.006,-.132,1.756),(-.014,-.160,1.740),(-.034,-.160,1.736),(-.045,-.150,1.714)),
 ((-.024,-.126,1.755),(-.048,-.151,1.737),(-.052,-.154,1.727),(-.060,-.140,1.706)),
 ((.061,-.123,1.747),(.070,-.142,1.730),(.060,-.151,1.725),(.048,-.149,1.712)),
 ((-.055,-.114,1.744),(-.070,-.136,1.720),(-.071,-.135,1.714),(-.069,-.125,1.698)),
 ((.047,-.131,1.756),(.020,-.162,1.742),(-.018,-.166,1.735),(-.012,-.159,1.724)),
 ((-.013,-.130,1.755),(-.032,-.155,1.737),(-.061,-.148,1.728),(-.055,-.142,1.717))]
collection=bpy.data.collections['AshV6_Equipment'];material=bpy.data.materials['AshV4_Forelocks_Baked']
center=Vector((0,-.041,1.706));radii=Vector((.112,.124,.148))
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
for level,per,segments,sides in [(0,22,18,4),(1,12,14,4),(2,6,9,4)]:
 verts=[];faces=[];uv=[];adjusted=0
 for index,path in enumerate(paths):
  a,b,c,d=[Vector(p) for p in path]
  for strand in range(per):
   offset=(strand-(per-1)/2)*(.005/per);start=len(verts)
   for i in range(segments+1):
    t=i/segments;p=(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d
    tangent=(3*(1-t)**2*(b-a)+6*(1-t)*t*(c-b)+3*t*t*(d-c)).normalized()
    across=tangent.cross(Vector((0,-1,0))).normalized();p+=across*offset*(1-.55*t)
    q=Vector(((p.x-center.x)/radii.x,(p.y-center.y)/radii.y,(p.z-center.z)/radii.z));length=q.length
    theta=math.acos(max(-1,min(1,q.z/length)));phi=abs(math.atan2(q.x,-q.y))
    edge=1.27+.085*math.sin(min(1,phi/.70)*math.pi*.5)**2*(1-smooth((phi-.70)/.40))+.86*smooth((phi-.58)/.65)-.22*smooth((phi-1.75)/(math.pi-1.75))
    # A finite-width clearance band under the rolled edge, not just the
    # enamel surface. It prevents a root ending visibly through the rim.
    if theta<edge+.055 and length>.885:p=center+(p-center)*(.885/length);adjusted+=1
    aa=tangent.orthogonal().normalized();bb=tangent.cross(aa).normalized();radius=.00020*(1-.30*t)
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
 obj.hide_render=level!=0;obj.hide_set(level!=0);reports[level]['newStrands']=per*len(paths);reports[level]['rootSamplesFittedInsideRim']=adjusted
rig.animation_data.action=bpy.data.actions['RB_Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_FRINGE '+json.dumps({'lods':reports,'oldBrowFibersRetained':True,'visualAccepted':False}))
