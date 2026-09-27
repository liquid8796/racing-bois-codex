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

HAND_CONTACTS={}
FOOT_CONTACTS={}
for label,sign in [('L',1),('R',-1)]:
    hand=rig.data.bones[PREFIX+'Hand_'+label]
    across=(rig.data.bones[PREFIX+'Finger_Index_1_'+label].head_local-rig.data.bones[PREFIX+'Finger_Pinky_1_'+label].head_local).normalized()
    longitudinal=(rig.data.bones[PREFIX+'Finger_Middle_1_'+label].head_local-hand.head_local).normalized()
    across=(across-longitudinal*across.dot(longitudinal)).normalized()
    normal=across.cross(longitudinal).normalized()
    desired_across=Vector((-sign*.875,-.484,0)).normalized()
    desired_long=Vector((0,-.94,-.34))
    desired_long=(desired_long-desired_across*desired_long.dot(desired_across)).normalized()
    desired_normal=desired_across.cross(desired_long).normalized()
    source_frame=Matrix((across,longitudinal,normal)).transposed()
    desired_frame=Matrix((desired_across,desired_long,desired_normal)).transposed()
    rotation=(desired_frame@source_frame.transposed()).to_quaternion()
    # Anatomical palm centre lies 77mm distal to the wrist. Its contact face
    # is 10mm below the joint plane; the grip centre is another 19mm inward.
    rest_grip=hand.head_local+longitudinal*.077-normal*(sign*.029)
    grip=bpy.data.objects['Contact_Grip_'+label].matrix_world.translation.copy()
    wrist=grip-rotation@(rest_grip-hand.head_local)+desired_normal*(sign*.011)+desired_long*.009
    HAND_CONTACTS[label]={'wrist':y_up(wrist),'rotation':rotation,'across':across,
        'normal':normal,'desiredNormal':desired_normal,'longitudinal':longitudinal,
        'grip':grip,'desiredAcross':desired_across,'desiredLong':desired_long}
    foot=rig.data.bones[PREFIX+'Foot_'+label]
    shoes=bpy.data.objects['AshV2_Shoes']
    sole=[v.co.copy() for v in shoes.data.vertices if sign*v.co.x>0 and abs(v.co.x-foot.head_local.x)<.023 and -.145<v.co.y<-.095 and v.co.z<.033]
    assert len(sole)>3,'Missing anatomical sole contact vertices'
    contact=sum(sole,Vector())/len(sole)
    peg=bpy.data.objects['Contact_Foot_'+label].matrix_world.translation.copy()+Vector((0,0,.014))
    # The actual runtime rubber sole sits about 10.5mm below the source
    # shoe foundation. Offset measured evaluated sole, not the base shoe.
    ankle=peg-(contact-foot.head_local)+Vector((0,0,.0105))
    FOOT_CONTACTS[label]={'ankle':y_up(ankle),'soleRest':contact,'pegTop':peg}

def pose_points(kind,t,side=1):
    riding=kind not in ['Idle','Run','Fall']
    amount=math.sin(math.pi*t)
    angle=50 if riding else 0
    if kind=='Attack':angle=32
    if kind=='Hit':angle=46-14*amount
    hip=Vector((0,.994,-.05)) if riding else REST['Hip'][0].copy()
    if kind=='Run':
        hip.y+=.018*math.sin(t*math.tau*2);angle=8
    if kind=='Idle':
        angle=.25*math.sin(t*math.tau)
        hip.y-=.030
    if kind=='Lean':hip.x+=.020*side
    points={}
    points['Hip']=(hip,hip+lean(REST['Hip'][1]-REST['Hip'][0],angle))
    torso_head=hip+lean(REST['Torso'][0]-REST['Hip'][0],angle)
    neck=hip+lean(REST['Torso'][1]-REST['Hip'][0],angle)
    if kind=='Lean':
        torso_head.x+=.035*side;neck.x+=.075*side
    points['Torso']=(torso_head,neck)
    points['Head']=(neck,neck+lean(REST['Head'][1]-REST['Head'][0],8 if riding else 0))
    for label,sign in [('L',1),('R',-1)]:
        shoulder=hip+lean(REST['UpperArm_'+label][0]-REST['Hip'][0],angle)
        if kind=='Lean':shoulder.x+=.065*side
        if riding:
            wrist=HAND_CONTACTS[label]['wrist'].copy();hand_direction=y_up(HAND_CONTACTS[label]['rotation']@(rig.data.bones[PREFIX+'Hand_'+label].tail_local-rig.data.bones[PREFIX+'Hand_'+label].head_local))
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
            ankle=FOOT_CONTACTS[label]['ankle'].copy();foot_direction=REST['Foot_'+label][1]-REST['Foot_'+label][0];hint=Vector((sign*.25,.80,.46))
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
        if name.startswith('Hand_') and kind not in ['Idle','Run','Fall']:
            label=name[-1];contact_rotation=HAND_CONTACTS[label]['rotation']@rest.matrix_local.to_quaternion()
            amount=1.0
            if kind=='Attack' and ((label=='L' and side>0) or (label=='R' and side<0)):amount=1-math.sin(math.pi*t)
            if kind=='Remount':amount=smooth(t)
            rotation=rotation.slerp(contact_rotation,amount)
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
        degrees=[69,96,57][segment-1]*amount
        if digit=='Thumb':degrees=[16,32,20][segment-1]*amount
        axis=HAND_CONTACTS[label]['across']*(-1 if label=='L' else 1)
        rotation=Matrix.Rotation(math.radians(degrees),4,axis)
        if digit=='Thumb' and segment==1:
            rotation=Matrix.Rotation(math.radians((-38 if label=='L' else 38)*amount),4,HAND_CONTACTS[label]['normal'])@rotation
        rest=rig.data.bones[bone.name].matrix_local.to_4x4()
        bone.rotation_mode='QUATERNION';bone.rotation_quaternion=(rest.inverted()@rotation@rest).to_quaternion()
    bpy.context.view_layer.update()

    # Ride contact is solved from the real finite cylinder and anatomical
    # phalanx lengths. Each joint follows its own circular arc; this prevents
    # the short pinky from over-curling under shared Euler angles.
    if kind not in ['Idle','Run','Fall']:
        for label,sign in [('L',1),('R',-1)]:
            if kind=='Attack' and sign==side:continue
            grip=HAND_CONTACTS[label]['grip'];axis=Vector((sign*.875,.484,0)).normalized()
            for digit in ['Index','Middle','Ring','Pinky']:
                for segment in [1,2,3]:
                    bone=rig.pose.bones[PREFIX+'Finger_'+digit+'_'+str(segment)+'_'+label]
                    head=bone.head.copy();old_direction=(bone.tail-head).normalized()
                    centre=grip+axis*(head-grip).dot(axis);radial=head-centre;start_radius=radial.length
                    # 39mm bone-centre radius accounts for glove thickness
                    # and LBS corner shortening measured in the actual mesh.
                    span=bone.length;radius=max(.039,start_radius-span*.97)
                    cosine=max(-1,min(1,(start_radius*start_radius+radius*radius-span*span)/(2*max(.0001,start_radius)*radius)))
                    angle=math.acos(cosine)*sign*(-1 if digit=='Thumb' else 1)
                    end=centre+Quaternion(axis,angle)@radial.normalized()*radius
                    rotation=old_direction.rotation_difference((end-head).normalized())@bone.matrix.to_quaternion()
                    if kind=='Remount':rotation=bone.matrix.to_quaternion().slerp(rotation,smooth(t))
                    bone.matrix=Matrix.Translation(head)@rotation.to_matrix().to_4x4()
                    bpy.context.view_layer.update()
            # Oppose the thumb on the rear/underside of the same grip. A
            # short bounded CCD solve preserves every phalanx length.
            forward=axis.cross(Vector((0,0,1)))*sign
            thumb_target=grip-axis*.015-forward*.017-Vector((0,0,.023))
            thumb_tip=rig.pose.bones[PREFIX+'Finger_Thumb_3_'+label]
            for iteration in range(12):
                if (thumb_tip.tail-thumb_target).length<.0005:break
                for segment in [3,2,1]:
                    bone=rig.pose.bones[PREFIX+'Finger_Thumb_'+str(segment)+'_'+label]
                    origin=bone.head.copy();current=thumb_tip.tail-origin;desired=thumb_target-origin
                    if min(current.length,desired.length)<.00001:continue
                    delta=current.normalized().rotation_difference(desired.normalized())
                    axis_delta,angle_delta=delta.to_axis_angle();delta=Quaternion(axis_delta,min(angle_delta,math.radians(18)))
                    rotation=delta@bone.matrix.to_quaternion()
                    if kind=='Remount':rotation=bone.matrix.to_quaternion().slerp(rotation,smooth(t))
                    bone.matrix=Matrix.Translation(origin)@rotation.to_matrix().to_4x4();bpy.context.view_layer.update()
    return targets

rig.animation_data_clear()
apply_pose('Idle',0)
print('ASH_V3_ANATOMICAL_IDLE_POSE_APPLIED')
