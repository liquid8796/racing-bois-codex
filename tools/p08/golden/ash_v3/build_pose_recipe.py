"""Prepare an inspectable V3 recipe; executed code reaches Blender only by MCP."""
from pathlib import Path
folder=Path(__file__).parent
source=(folder.parent/'ash_v2/pose_library.py').read_text(encoding='utf-8')
helper='''
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

'''
source=source.replace('def pose_points(kind,t,side=1):',helper+'def pose_points(kind,t,side=1):')
source=source.replace('angle=46 if riding else 0','angle=50 if riding else 0')
source=source.replace("hip=Vector((0,.904,-.05)) if riding else REST['Hip'][0].copy()","hip=Vector((0,.994,-.05)) if riding else REST['Hip'][0].copy()")
source=source.replace('wrist=Vector((sign*.314,1.027,.636));hand_direction=Vector((-sign*.025,-.048,.121))',"wrist=HAND_CONTACTS[label]['wrist'].copy();hand_direction=y_up(HAND_CONTACTS[label]['rotation']@(rig.data.bones[PREFIX+'Hand_'+label].tail_local-rig.data.bones[PREFIX+'Hand_'+label].head_local))")
source=source.replace('ankle=Vector((sign*.255,.466,-.102));foot_direction=Vector((sign*.028,-.044,.178));hint=Vector((sign*.21,.76,.44))',"ankle=FOOT_CONTACTS[label]['ankle'].copy();foot_direction=REST['Foot_'+label][1]-REST['Foot_'+label][0];hint=Vector((sign*.25,.80,.46))")
source=source.replace("pose.matrix=Matrix.Translation(cv(head))@rotation.to_matrix().to_4x4()", """if name.startswith('Hand_') and kind not in ['Idle','Run','Fall']:
            label=name[-1];contact_rotation=HAND_CONTACTS[label]['rotation']@rest.matrix_local.to_quaternion()
            amount=1.0
            if kind=='Attack' and ((label=='L' and side>0) or (label=='R' and side<0)):amount=1-math.sin(math.pi*t)
            if kind=='Remount':amount=smooth(t)
            rotation=rotation.slerp(contact_rotation,amount)
        pose.matrix=Matrix.Translation(cv(head))@rotation.to_matrix().to_4x4()""")
source=source.replace("rotation=Matrix.Rotation(math.radians(degrees),4,'X')", "axis=HAND_CONTACTS[label]['across']*(-1 if label=='L' else 1)\n        rotation=Matrix.Rotation(math.radians(degrees),4,axis)")
source=source.replace('degrees=[48,68,38][segment-1]*amount','degrees=[69,96,57][segment-1]*amount')
source=source.replace("rotation=Matrix.Rotation(math.radians((-25 if label=='L' else 25)*amount),4,'Z')@rotation", "rotation=Matrix.Rotation(math.radians((-38 if label=='L' else 38)*amount),4,HAND_CONTACTS[label]['normal'])@rotation")
source=source.replace('ASH_ANATOMICAL_IDLE_POSE_APPLIED','ASH_V3_ANATOMICAL_IDLE_POSE_APPLIED')
start=source.index("    if kind=='Lean':\n        a=math.radians")
end=source.index("    if kind=='Fall':",start)
source=source[:start]+source[end:]
source=source.replace("    points={}\n","    if kind=='Lean':hip.x+=.020*side\n    points={}\n")
source=source.replace("    points['Torso']=(torso_head,neck)","    if kind=='Lean':\n        torso_head.x+=.035*side;neck.x+=.075*side\n    points['Torso']=(torso_head,neck)")
source=source.replace("        if riding:\n            wrist=", "        if kind=='Lean':shoulder.x+=.065*side\n        if riding:\n            wrist=")
wrap='''
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
'''
source=source.replace('    return targets\n',wrap+'    return targets\n')
(folder/'pose_library.py').write_text(source,encoding='utf-8')
preview='''
scene=bpy.context.scene;camera=scene.camera
apply_pose('Ride',0)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
camera.data.type='ORTHO'
for name,position,target,scale,resolution in [
    ('contact-side',(3,-.02,1.0),(0,-.20,.94),2.25,(1200,1000)),
    ('contact-three-quarter',(2.8,-4,2.0),(0,-.22,.91),2.55,(1200,1000)),
    ('contact-hand-left',(.58,-1.06,1.23),(.29,-.71,1.007),.29,(900,900)),
    ('contact-foot-left',(.68,-.37,.51),(.286,-.071,.44),.40,(900,900)),
]:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v3/'+name+'.png'
    bpy.ops.render.render(write_still=True)
print('ASH_V3_CONTACT_POSE '+json.dumps({'hands':{k:{'wristYUp':list(v['wrist']),'gripBlender':list(v['grip'])} for k,v in HAND_CONTACTS.items()},'feet':{k:{key:list(value) for key,value in v.items()} for k,v in FOOT_CONTACTS.items()}}))
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V3/RB_Golden_Ash_V3.blend',compress=False)
'''
(folder/'preview_contacts.py').write_text(source+preview,encoding='utf-8')
print('Prepared V3 contact pose and preview recipes')
