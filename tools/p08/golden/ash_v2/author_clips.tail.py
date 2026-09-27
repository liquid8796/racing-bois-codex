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
