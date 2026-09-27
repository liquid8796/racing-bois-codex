"""Place the real palm support envelope on R4 and relax fingers on its tangent plane."""
import bpy,math,json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7_PreR4Menu.blend',load_ui=False,use_scripts=False)
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];action=bpy.data.actions['RB_MenuHero'];rig.animation_data.action=action;P='RB_P06_Rider_L0_';bike=bpy.data.objects['RB_Golden_Apex_r4'];vertices=[];faces=[]
for o in bike.children_recursive:
 if o.type!='MESH' or not o.name.startswith('Apex_L0_'):continue
 start=len(vertices);vertices.extend([o.matrix_world@v.co for v in o.data.vertices]);faces.extend([tuple(start+i for i in p.vertices) for p in o.data.polygons])
tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False);targets={};body=bpy.data.objects['AshV7_L0_Skin']
for side,sign,xy in [('L',1,(-.18,-.28)),('R',-1,(-.23,.51))]:
 point,normal,index,d=tree.ray_cast(Vector((xy[0],xy[1],1.6)),Vector((0,0,-1)),1.2);assert point is not None and normal.z>.65
 hand=rig.data.bones[P+'Hand_'+side];long=(rig.data.bones[P+'Finger_Middle_1_'+side].head_local-hand.head_local).normalized();across=(rig.data.bones[P+'Finger_Index_1_'+side].head_local-rig.data.bones[P+'Finger_Pinky_1_'+side].head_local).normalized();across=(across-long*across.dot(long)).normalized();old_normal=across.cross(long).normalized()
 wanted=Vector((-.84,-.54 if side=='L' else .54,0));wanted=(wanted-normal*wanted.dot(normal)).normalized();new_normal=normal*sign;new_across=wanted.cross(new_normal).normalized()
 # Explicit matrix form avoids a guessed ten-millimetre palm thickness.
 source_basis=Matrix((across,long,old_normal)).transposed();desired_basis=Matrix((new_across,wanted,new_normal)).transposed();rotation=desired_basis@source_basis.transposed()
 palm=[]
 for v in body.data.vertices:
  weight=sum(g.weight for g in v.groups if body.vertex_groups[g.group].name==P+'Hand_'+side);delta=v.co-hand.head_local
  if weight>.8 and .045<delta.dot(long)<.095 and abs(delta.dot(across))<.026:palm.append(rotation@delta)
 support=min(v.dot(normal) for v in palm);wrist=point-wanted*.073+normal*(.0012-support)
 targets[side]={'surface':point,'normal':normal,'rotation':rotation,'wrist':wrist,'palmSupportOffset':support,'palmVertices':len(palm)}
def solve(a,end,l1,l2,hint):
 delta=end-a;d=delta.length;assert d<l1+l2-.0001;axis=delta.normalized();length=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-length*length));bend=hint-a-axis*(hint-a).dot(axis);return a+axis*length+bend.normalized()*height
def segment(name,start,direction,reference):
 q=(reference@Vector((0,1,0))).rotation_difference(direction.normalized())@reference;rig.pose.bones[name].matrix=Matrix.Translation(start)@q.to_matrix().to_4x4();bpy.context.view_layer.update()
frames=[1+60*i/16 for i in range(17)]
for frame in frames:
 scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
 for side in ['L','R']:
  target=targets[side];upper=rig.pose.bones[P+'UpperArm_'+side];fore=rig.pose.bones[P+'Forearm_'+side];hand=rig.pose.bones[P+'Hand_'+side];start=upper.head.copy();q1=upper.matrix.to_quaternion();q2=fore.matrix.to_quaternion();elbow=solve(start,target['wrist'],upper.bone.length,fore.bone.length,fore.head.copy())
  segment(upper.name,start,elbow-start,q1);segment(fore.name,elbow,target['wrist']-elbow,q2);hand.matrix=Matrix.Translation(target['wrist'])@(target['rotation']@hand.bone.matrix_local.to_3x3()).to_4x4();bpy.context.view_layer.update()
  changed=[upper,fore,hand]
  for finger in ['Thumb','Index','Middle','Ring','Pinky']:
   for joint in [1,2,3]:
    bone=rig.pose.bones[P+'Finger_'+finger+'_'+str(joint)+'_'+side];direction=target['rotation']@(bone.bone.tail_local-bone.bone.head_local);direction=(direction-target['normal']*direction.dot(target['normal'])).normalized()
    # Slight relaxed tip flex, but the thumb no longer hooks downward and
    # forces the whole palm to float above the supporting surface.
    if joint==3 and finger!='Thumb':direction=(direction-target['normal']*.025).normalized()
    reference=(target['rotation']@bone.bone.matrix_local.to_3x3()).to_quaternion();segment(bone.name,bone.head.copy(),direction,reference);changed.append(bone)
  for bone in changed:bone.rotation_mode='QUATERNION';bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=bone.name)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7_MenuPalmSource.blend',compress=False)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend',compress=False)
print('ASH_V7_PALM_SUPPORT_SOURCE '+json.dumps({'targets':{side:{k:list(v) if isinstance(v,Vector) else v for k,v in target.items() if k!='rotation'} for side,target in targets.items()},'frames':len(frames),'scope':'MenuHero upper-arm/forearm/hand/finger quaternion curves only','preservedRestMeshesAndGameplay':True,'visualAccepted':False}))
