"""Evaluate authored skinned actions; save real pose renders and joint metrics."""
import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene
scene.cycles.samples=12;scene.render.resolution_percentage=75
report=[]
for clip,frame in [('RB_Ride',1),('RB_AttackRight',8),('RB_KickLeft',9),('RB_Run',7),('RB_Fall',19)]:
    action=bpy.data.actions.get(clip)
    if action is None:raise RuntimeError('Missing exact action '+clip)
    rig.animation_data.action=action;scene.frame_set(frame);bpy.context.view_layer.update()
    joints={}
    for part in ['Hip','Head','Hand_L','Hand_R','Foot_L','Foot_R']:
        p=rig.matrix_world@rig.pose.bones['RB_P06_Rider_L0_'+part].head;joints[part]=[-p.x,p.z,-p.y]
    report.append({'clip':clip,'frame':frame,'jointPositionsUnityMeters':joints})
    scene.render.filepath=ROOT+'docs/p06/hero/'+clip+'-pose.png';bpy.ops.render.render(write_still=True)
rig.animation_data.action=None;scene.frame_set(1)
for bone in rig.pose.bones:bone.rotation_quaternion=(1,0,0,0)
print(json.dumps({'poses':report,'method':'Authored actions evaluated against real Armature modifier; renders from Blender Cycles.'}))
