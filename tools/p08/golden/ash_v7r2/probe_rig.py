import bpy,json
from mathutils import Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene;old_action=rig.animation_data.action;old_frame=scene.frame_current;old_sub=scene.frame_subframe
parts=['Hip','Torso','Head','UpperArm_L','Forearm_L','Hand_L','UpperArm_R','Forearm_R','Hand_R','Thigh_L','Shin_L','Foot_L','Thigh_R','Shin_R','Foot_R'];rows=[]
try:
    rig.animation_data.action=bpy.data.actions['RB_Fall']
    for frame in [1,9,19]:
        scene.frame_set(frame);bpy.context.view_layer.update();bones=[]
        for part in parts:
            p=rig.pose.bones['RB_P06_Rider_L0_'+part];b=p.bone
            bones.append({'part':part,'head':list(p.head),'tail':list(p.tail),'length':b.length,'restHead':list(b.head_local),'restTail':list(b.tail_local)})
        hip=rig.pose.bones['RB_P06_Rider_L0_Hip'];rotation=hip.matrix.to_quaternion()@hip.bone.matrix_local.to_quaternion().inverted()
        rows.append({'frame':frame,'bodyFloorDirection':list(rotation.inverted()@Vector((0,0,-1))),'bones':bones})
finally:
    rig.animation_data.action=old_action;scene.frame_set(old_frame,subframe=old_sub);bpy.context.view_layer.update()
print('V7R2_RIG '+json.dumps(rows))
