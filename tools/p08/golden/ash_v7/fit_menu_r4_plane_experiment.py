"""Menu-only IK contact fitting against the hash-pinned canonical Apex R4."""
import bpy,math,json
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];action=bpy.data.actions['RB_MenuHero'];rig.animation_data.action=action;PREFIX='RB_P06_Rider_L0_';bike=bpy.data.objects['RB_Golden_Apex_r4'];points=[];faces=[]
for obj in bike.children_recursive:
 if obj.type!='MESH' or not obj.name.startswith('Apex_L0_'):continue
 offset=len(points);points.extend([obj.matrix_world@v.co for v in obj.data.vertices]);faces.extend([tuple(offset+i for i in p.vertices) for p in obj.data.polygons])
tree=BVHTree.FromPolygons(points,faces,all_triangles=False);frames=[1+60*i/16 for i in range(17)];baseline=[]
for frame in frames:
 scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();row={}
 for side in ['L','R']:
  upper=rig.pose.bones[PREFIX+'UpperArm_'+side];fore=rig.pose.bones[PREFIX+'Forearm_'+side];hand=rig.pose.bones[PREFIX+'Hand_'+side]
  row[side]={'shoulder':upper.head.copy(),'elbow':fore.head.copy(),'wrist':hand.head.copy(),'upperQ':upper.matrix.to_quaternion(),'foreQ':fore.matrix.to_quaternion(),'handQ':hand.matrix.to_quaternion()}
 baseline.append(row)
selections={}
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];selections[level]={}
 for side in ['L','R']:
  ids=set()
  for v in obj.data.vertices:
   if any((obj.vertex_groups[g.group].name==PREFIX+'Hand_'+side or ('Finger_' in obj.vertex_groups[g.group].name and obj.vertex_groups[g.group].name.endswith('_'+side))) and g.weight>.15 for g in v.groups):ids.add(v.index)
  poly=[tuple(p.vertices) for p in obj.data.polygons if all(i in ids for i in p.vertices)];selections[level][side]=(ids,poly)
def measure():
 rows=[];worst={'L':1,'R':1};pairs={'L':0,'R':0}
 for frame in frames:
  scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();levels=[]
  for level in range(3):
   obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();coords=[v.co.copy() for v in m.vertices];hands=[]
   for side in ['L','R']:
    ids,polygons=selections[level][side];distances=[]
    for i in ids:
     p,n,index,d=tree.find_nearest(coords[i]);distances.append((coords[i]-p).dot(n))
    collisions=len(BVHTree.FromPolygons(coords,polygons,all_triangles=False).overlap(tree));minimum=min(distances);worst[side]=min(worst[side],minimum);pairs[side]+=collisions;hands.append({'side':side,'minimumSignedDistance':minimum,'triangleIntersections':collisions,'nearestAbsoluteContact':min(abs(d) for d in distances),'gloveVertices':len(ids)})
   levels.append({'lod':level,'hands':hands});ev.to_mesh_clear()
  rows.append({'frame':frame,'lods':levels})
 return {'samples':rows,'minimumByHand':worst,'intersectionPairsByHand':pairs}
def elbow(a,end,l1,l2,hint):
 delta=end-a;distance=delta.length;assert distance<l1+l2-.0001,'Menu reach exceeded';axis=delta.normalized();along=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-along*along));bend=hint-a-axis*(hint-a).dot(axis)
 if bend.length<.0001:bend=axis.orthogonal()
 return a+axis*along+bend.normalized()*height
def segment(name,start,end,reference):
 rotation=(reference@Vector((0,1,0))).rotation_difference((end-start).normalized())@reference;rig.pose.bones[PREFIX+name].matrix=Matrix.Translation(start)@rotation.to_matrix().to_4x4();bpy.context.view_layer.update()
offset={'L':0.0,'R':0.0};history=[];before=measure()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7_PreR4Menu.blend',compress=False)
for iteration in range(5):
 current=before if iteration==0 else measure();history.append({'iteration':iteration,'minimumByHand':current['minimumByHand'],'intersections':current['intersectionPairsByHand'],'verticalOffsets':dict(offset)})
 if all(current['minimumByHand'][s]>=.0004 and current['intersectionPairsByHand'][s]==0 for s in ['L','R']):break
 for side in ['L','R']:
  if current['minimumByHand'][side]<.0004:offset[side]+=.0012-current['minimumByHand'][side]
  elif current['intersectionPairsByHand'][side]:offset[side]+=.0015
  assert abs(offset[side])<.075,'Menu fit displacement exceeds allowed local adjustment'
 for index,frame in enumerate(frames):
  scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
  for side in ['L','R']:
   base=baseline[index][side];wrist=base['wrist']+Vector((0,0,offset[side]));joint=elbow(base['shoulder'],wrist,rig.data.bones[PREFIX+'UpperArm_'+side].length,rig.data.bones[PREFIX+'Forearm_'+side].length,base['elbow'])
   segment('UpperArm_'+side,base['shoulder'],joint,base['upperQ']);segment('Forearm_'+side,joint,wrist,base['foreQ']);rig.pose.bones[PREFIX+'Hand_'+side].matrix=Matrix.Translation(wrist)@base['handQ'].to_matrix().to_4x4();bpy.context.view_layer.update()
   for part in ['UpperArm_','Forearm_','Hand_']:
    bone=rig.pose.bones[PREFIX+part+side];bone.rotation_mode='QUATERNION';bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=bone.name)
after=measure();passed=all(after['minimumByHand'][s]>=0 and after['intersectionPairsByHand'][s]==0 for s in ['L','R'])
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_MENU_R4_FIT '+json.dumps({'referenceFbx':'Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4.fbx','referenceSha256':'4e57cfeaefe2e27643c17bb083b04acb15dd483276a02058f05e687f69c16841','menuSampleCount':17,'history':history,'finalOffsets':offset,'passed':passed,'final':after,'changedCurves':'MenuHero rotation_quaternion of six upper arm/forearm/hand bones only','gameplayOrRestGeometryChanges':False,'visualAccepted':False}))
