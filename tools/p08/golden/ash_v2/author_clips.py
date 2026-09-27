"""Analytical 2-bone cosmetic poses for Ash's fitted anatomical rest rig.

Positions below are rider-local metres, Y up and forward Z. The known runtime
bike-to-rider placement is (0,-.08,-.32); contact targets are diagnostic, not
an acceptance of all bike/rider combinations. No root motion drives gameplay.
"""
import bpy,math,json
from mathutils import Vector,Matrix,Quaternion
rig=bpy.data.objects['RB_P06_Rider_Rig']
PREFIX='RB_P06_Rider_L0_'
ORDER=['Hip','Torso','Head','UpperArm_L','Forearm_L','Hand_L','UpperArm_R','Forearm_R','Hand_R','Thigh_L','Shin_L','Foot_L','Thigh_R','Shin_R','Foot_R']
def cv(p):return Vector((p[0],-p[2],p[1]))
def y_up(p):return Vector((p.x,p.z,-p.y))
REST={}
for name in ORDER:
    bone=rig.data.bones[PREFIX+name]
    REST[name]=(y_up(bone.head_local),y_up(bone.tail_local))
def length(name):return (REST[name][1]-REST[name][0]).length
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def lean(v,degrees):
    angle=math.radians(degrees);c=math.cos(angle);s=math.sin(angle)
    return Vector((v.x,c*v.y-s*v.z,s*v.y+c*v.z))
def solve_limb(a,end,l1,l2,hint):
    delta=end-a;distance=min(max(delta.length,.001),l1+l2-.0005)
    axis=delta.normalized();end=a+axis*distance
    projection=(l1*l1-l2*l2+distance*distance)/(2*distance)
    height=math.sqrt(max(0,l1*l1-projection*projection))
    bend=hint-a-axis*(hint-a).dot(axis)
    if bend.length<.0001:bend=axis.cross(Vector((0,1,0)))
    bend.normalize()
    return a+axis*projection+bend*height,end
def pose_points(kind,t,side=1):
    riding=kind not in ['Idle','Run','Fall']
    amount=math.sin(math.pi*t)
    angle=46 if riding else 0
    if kind=='Attack':angle=32
    if kind=='Hit':angle=46-14*amount
    hip=Vector((0,.904,-.05)) if riding else REST['Hip'][0].copy()
    if kind=='Run':
        hip.y+=.018*math.sin(t*math.tau*2);angle=8
    if kind=='Idle':
        angle=.25*math.sin(t*math.tau)
        hip.y-=.030
    points={}
    points['Hip']=(hip,hip+lean(REST['Hip'][1]-REST['Hip'][0],angle))
    torso_head=hip+lean(REST['Torso'][0]-REST['Hip'][0],angle)
    neck=hip+lean(REST['Torso'][1]-REST['Hip'][0],angle)
    points['Torso']=(torso_head,neck)
    points['Head']=(neck,neck+lean(REST['Head'][1]-REST['Head'][0],8 if riding else 0))
    for label,sign in [('L',1),('R',-1)]:
        shoulder=hip+lean(REST['UpperArm_'+label][0]-REST['Hip'][0],angle)
        if riding:
            wrist=Vector((sign*.314,1.027,.636));hand_direction=Vector((-sign*.025,-.048,.121))
            elbow_hint=Vector((sign*.47,1.20,.30))
        else:
            wrist=Vector((sign*.292,.965,.069));hand_direction=Vector((sign*.01,-.160,.025))
            elbow_hint=Vector((sign*.34,1.22,-.10))
        if kind=='Attack' and sign==side:
            wrist=wrist.lerp(Vector((sign*.67,1.27,.71)),amount)
            hand_direction=Vector((sign*.13,0,.035));elbow_hint=Vector((sign*.52,1.15,.25))
        if kind=='Run':
            swing=math.sin(t*math.tau)*sign
            wrist=Vector((sign*.25,1.04,-.20*swing+.08));elbow_hint=Vector((sign*.30,1.18,-.22))
            hand_direction=Vector((0,-.11,.06))
        elbow,wrist=solve_limb(shoulder,wrist,length('UpperArm_'+label),length('Forearm_'+label),elbow_hint)
        points['UpperArm_'+label]=(shoulder,elbow)
        points['Forearm_'+label]=(elbow,wrist)
        points['Hand_'+label]=(wrist,wrist+hand_direction.normalized()*length('Hand_'+label))
        thigh=hip+lean(REST['Thigh_'+label][0]-REST['Hip'][0],angle)
        if riding:
            ankle=Vector((sign*.255,.466,-.102));foot_direction=Vector((sign*.028,-.044,.178));hint=Vector((sign*.21,.76,.44))
        else:
            ankle=Vector((sign*.155,.075,.016));foot_direction=REST['Foot_'+label][1]-REST['Foot_'+label][0];hint=Vector((sign*.16,.54,.13))
        if kind=='Kick' and sign==side:
            ankle=ankle.lerp(Vector((sign*.70,.59,.36)),amount)
            foot_direction=Vector((sign*.06,-.03,.15));hint=Vector((sign*.64,.73,.42))
        if kind=='Run':
            swing=math.sin(t*math.tau)*sign
            ankle=Vector((sign*.13,.106+max(0,-swing)*.18,.21*swing))
            foot_direction=Vector((0,-.06-.03*max(0,-swing),.19));hint=Vector((sign*.14,.53,.38))
        knee,ankle=solve_limb(thigh,ankle,length('Thigh_'+label),length('Shin_'+label),hint)
        points['Thigh_'+label]=(thigh,knee);points['Shin_'+label]=(knee,ankle)
        points['Foot_'+label]=(ankle,ankle+foot_direction.normalized()*length('Foot_'+label))
    if kind=='Lean':
        a=math.radians(10*side);c=math.cos(a);s=math.sin(a)
        for name in ORDER:
            pair=[]
            for p in points[name]:
                d=p-hip;pair.append(hip+Vector((d.x*c-d.y*s,d.x*s+d.y*c,d.z)))
            points[name]=tuple(pair)
    if kind=='Fall':
        a=math.radians(82*smooth(t));c=math.cos(a);s=math.sin(a)
        fall_hip=hip+Vector((.24*smooth(t),-.57*smooth(t),-.05*smooth(t)))
        for name in ORDER:
            pair=[]
            for p in points[name]:
                d=p-hip;pair.append(fall_hip+Vector((d.x*c+d.y*s,-d.x*s+d.y*c,d.z)))
            points[name]=tuple(pair)
    if kind=='Remount':
        start=pose_points('Idle',0)
        for name in ORDER:points[name]=tuple(a.lerp(b,smooth(t)) for a,b in zip(start[name],points[name]))
    return points
def apply_pose(kind,t,side=1):
    targets=pose_points(kind,t,side)
    for name in ORDER:
        head,tail=targets[name];rest=rig.data.bones[PREFIX+name]
        direction=cv(tail-head).normalized()
        delta=(rest.tail_local-rest.head_local).normalized().rotation_difference(direction)
        rotation=delta@rest.matrix_local.to_quaternion()
        pose=rig.pose.bones[PREFIX+name];pose.rotation_mode='QUATERNION'
        pose.matrix=Matrix.Translation(cv(head))@rotation.to_matrix().to_4x4()
        bpy.context.view_layer.update()
    grip=.82
    if kind=='Idle':grip=.10
    elif kind=='Run':grip=.52
    elif kind=='Fall':grip=.40-.24*smooth(t)
    elif kind=='Remount':grip=.10+.72*smooth(t)
    for bone in rig.pose.bones:
        if not bone.name.startswith(PREFIX+'Finger_'):continue
        parts=bone.name[len(PREFIX):].split('_');digit=parts[1];segment=int(parts[2]);label=parts[3]
        amount=1.0 if kind=='Attack' and ((label=='L' and side>0) or (label=='R' and side<0)) else grip
        degrees=[48,68,38][segment-1]*amount
        if digit=='Thumb':degrees=[16,32,20][segment-1]*amount
        rotation=Matrix.Rotation(math.radians(degrees),4,'X')
        if digit=='Thumb' and segment==1:
            rotation=Matrix.Rotation(math.radians((-25 if label=='L' else 25)*amount),4,'Z')@rotation
        rest=rig.data.bones[bone.name].matrix_local.to_4x4()
        bone.rotation_mode='QUATERNION';bone.rotation_quaternion=(rest.inverted()@rotation@rest).to_quaternion()
    bpy.context.view_layer.update()
    return targets

rig.animation_data_clear()
apply_pose('Idle',0)
print('ASH_ANATOMICAL_IDLE_POSE_APPLIED')

"""Appended literally to pose_library.py by the preparation step."""
for previous in list(bpy.data.actions):
    if previous.name.startswith('RB_'):bpy.data.actions.remove(previous)
CLIPS=[('RB_Ride',1,'Ride',True,1),('RB_LeanLeft',1,'Lean',True,1),('RB_LeanRight',1,'Lean',True,-1),
       ('RB_AttackLeft',.5,'Attack',False,1),('RB_AttackRight',.5,'Attack',False,-1),
       ('RB_KickLeft',.55,'Kick',False,1),('RB_KickRight',.55,'Kick',False,-1),
       ('RB_Hit',.35,'Hit',False,1),('RB_Fall',.6,'Fall',False,1),('RB_Run',.8,'Run',True,1),
       ('RB_Remount',.8,'Remount',False,1),('RB_Idle',1,'Idle',True,1)]
scene=bpy.context.scene;scene.render.fps=30
clip_receipt=[]
for name,duration,kind,loop,side in CLIPS:
    rig.animation_data_create();action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    count=max(2,round(duration*30));action['loop']=loop;action['root_motion']=False;action['anatomical_retarget']='AshV2'
    for i in range(count+1):
        scene.frame_set(i+1);apply_pose(kind,i/count,side)
        for bone in rig.pose.bones:
            bone.keyframe_insert(data_path='location',frame=i+1,group=bone.name)
            bone.keyframe_insert(data_path='rotation_quaternion',frame=i+1,group=bone.name)
            bone.keyframe_insert(data_path='scale',frame=i+1,group=bone.name)
    clip_receipt.append({'name':name,'frames':[1,count+1],'duration':count/30,'loop':loop,'rootMotion':False,'bones':len(rig.pose.bones)})
    print('ASH_CLIP_AUTHORED '+name)
rig.animation_data.action=None
scene.frame_set(1);apply_pose('Idle',0)
scene.frame_start=1;scene.frame_end=31
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend')
print('ASH_MATCHING_CLIPS '+json.dumps(clip_receipt))
