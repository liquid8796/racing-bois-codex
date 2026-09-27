"""Menu-only IK contact fitting against the hash-pinned canonical Apex R4."""
import bpy,math,json
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7_MenuPalmSource.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];action=bpy.data.actions['RB_MenuHero'];rig.animation_data.action=action;PREFIX='RB_P06_Rider_L0_';bike=bpy.data.objects['RB_Golden_Apex_r4'];points=[];faces=[];components=[]
for obj in bike.children_recursive:
 if obj.type!='MESH' or not obj.name.startswith('Apex_L0_'):continue
 offset=len(points);world=[obj.matrix_world@v.co for v in obj.data.vertices];points.extend(world);faces.extend([tuple(offset+i for i in p.vertices) for p in obj.data.polygons])
 adjacency=[set() for _ in obj.data.vertices]
 for edge in obj.data.edges:a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
 todo=set(range(len(world)));membership={};groups=[]
 while todo:
  first=todo.pop();found={first};queue=[first]
  while queue:
   for i in adjacency[queue.pop()]:
    if i in todo:todo.remove(i);found.add(i);queue.append(i)
  index=len(groups)
  for i in found:membership[i]=index
  groups.append(sorted(found))
 grouped_faces=[[] for group in groups]
 for polygon in obj.data.polygons:grouped_faces[membership[polygon.vertices[0]]].append(tuple(polygon.vertices))
 for group,polygons in zip(groups,grouped_faces):
  mapping={i:j for j,i in enumerate(group)};coords=[world[i] for i in group]
  components.append({'points':coords,'faces':[tuple(mapping[i] for i in p) for p in polygons],'min':Vector(tuple(min(p[k] for p in coords) for k in range(3))),'max':Vector(tuple(max(p[k] for p in coords) for k in range(3))),'tree':None})
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
  poly=[tuple(p.vertices) for p in obj.data.polygons if all(i in ids for i in p.vertices)]
  adjacency={i:set() for i in ids}
  for face in poly:
   for index,i in enumerate(face):adjacency[i].add(face[(index+1)%len(face)]);adjacency[face[(index+1)%len(face)]].add(i)
  todo=set(ids);groups=[]
  while todo:
   first=todo.pop();found={first};queue=[first]
   while queue:
    for i in adjacency[queue.pop()]:
     if i in todo:todo.remove(i);found.add(i);queue.append(i)
   groups.append(found)
  hand=rig.data.bones[PREFIX+'Hand_'+side];long=(rig.data.bones[PREFIX+'Finger_Middle_1_'+side].head_local-hand.head_local).normalized();across=(rig.data.bones[PREFIX+'Finger_Index_1_'+side].head_local-rig.data.bones[PREFIX+'Finger_Pinky_1_'+side].head_local).normalized();across=(across-long*across.dot(long)).normalized()
  palm_ids=set(v.index for v in obj.data.vertices if v.index in ids and .045<(v.co-hand.head_local).dot(long)<.095 and abs((v.co-hand.head_local).dot(across))<.026 and any(obj.vertex_groups[g.group].name==PREFIX+'Hand_'+side and g.weight>.8 for g in v.groups))
  selections[level][side]=(ids,poly,groups,palm_ids)
directions=[Vector((.973,.203,.119)).normalized(),Vector((.179,.947,.277)).normalized(),Vector((.231,.137,.963)).normalized()]
def in_bounds(point,component):return all(component['min'][k]-1e-7<=point[k]<=component['max'][k]+1e-7 for k in range(3))
def inside_component(point,component):
 if not in_bounds(point,component):return False
 if component['tree'] is None:component['tree']=BVHTree.FromPolygons(component['points'],component['faces'],all_triangles=False)
 votes=0
 for direction in directions:
  origin=point.copy();hits=0
  for _ in range(80):
   p,n,index,d=component['tree'].ray_cast(origin,direction,5)
   if p is None:break
   hits+=1;origin=p+direction*.000001
  else:raise RuntimeError('Closed component ray traversal did not converge')
  votes+=hits%2
 return votes>=2
def measure():
 rows=[];worst={'L':1,'R':1};pairs={'L':0,'R':0}
 for frame in frames:
  scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update();levels=[]
  for level in range(3):
   obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();coords=[v.co.copy() for v in m.vertices];hands=[]
   for side in ['L','R']:
    ids,polygons,groups,palm_ids=selections[level][side];distances=[];palm_distances=[];candidate_min=Vector(tuple(min(coords[i][k] for i in ids) for k in range(3)));candidate_max=Vector(tuple(max(coords[i][k] for i in ids) for k in range(3)))
    nearby=[c for c in components if all(c['min'][k]<=candidate_max[k] and c['max'][k]>=candidate_min[k] for k in range(3))]
    collisions=len(BVHTree.FromPolygons(coords,polygons,all_triangles=False).overlap(tree));inside_ids=set();contained_groups=0
    if collisions==0:
     for group in groups:
      if any(inside_component(coords[min(group)],c) for c in nearby):inside_ids.update(group);contained_groups+=1
    for i in ids:
     p,n,index,d=tree.find_nearest(coords[i]);signed=(coords[i]-p).dot(n) if collisions else -d if i in inside_ids else d;distances.append(signed)
     if i in palm_ids:palm_distances.append(signed)
    minimum=min(distances);worst[side]=min(worst[side],minimum);pairs[side]+=collisions;hands.append({'side':side,'minimumSignedDistance':minimum,'triangleIntersections':collisions,'containedConnectedGloveParts':contained_groups,'connectedGloveParts':len(groups),'nearestAbsoluteContact':min(abs(d) for d in distances),'gloveVertices':len(ids),'centralPalmVertices':len(palm_ids),'centralPalmMinimumDistance':min(palm_distances)})
   levels.append({'lod':level,'hands':hands});ev.to_mesh_clear()
  rows.append({'frame':frame,'lods':levels})
 return {'samples':rows,'minimumByHand':worst,'intersectionPairsByHand':pairs,'distanceMethod':'Require zero triangle intersections, then one containment sample per connected glove surface part against closed bike components (three deterministic ray directions, majority parity). Connected parts cannot change inside/outside classification without crossing the surface. Report signed Euclidean proximity only after the intersection gate; intersecting iterations use a plane estimate for fitting only.'}
def elbow(a,end,l1,l2,hint):
 delta=end-a;distance=delta.length;assert distance<l1+l2-.0001,'Menu reach exceeded';axis=delta.normalized();along=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-along*along));bend=hint-a-axis*(hint-a).dot(axis)
 if bend.length<.0001:bend=axis.orthogonal()
 return a+axis*along+bend.normalized()*height
def segment(name,start,end,reference):
 rotation=(reference@Vector((0,1,0))).rotation_difference((end-start).normalized())@reference;rig.pose.bones[PREFIX+name].matrix=Matrix.Translation(start)@rotation.to_matrix().to_4x4();bpy.context.view_layer.update()
offset={'L':0.0,'R':0.0};history=[];before=measure()
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
after=measure();passed=all(after['minimumByHand'][s]>=0 and after['intersectionPairsByHand'][s]==0 for s in ['L','R']) and all(h['centralPalmMinimumDistance']<.008 for row in after['samples'] for level in row['lods'] for h in level['hands'])
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_MENU_R4_FIT '+json.dumps({'referenceFbx':'Assets/RacingBois/Art/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4.fbx','referenceSha256':'4e57cfeaefe2e27643c17bb083b04acb15dd483276a02058f05e687f69c16841','menuSampleCount':17,'history':history,'finalOffsets':offset,'passed':passed,'final':after,'changedCurves':'MenuHero rotation_quaternion of six upper arm/forearm/hand bones only','gameplayOrRestGeometryChanges':False,'visualAccepted':False}))
