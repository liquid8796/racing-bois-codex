"""Concept screen-right gaze correction on the menu-only action."""
import bpy,math,json
from mathutils import Vector,Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];scene=bpy.context.scene;action=bpy.data.actions['RB_MenuHero'];rig.animation_data.action=action
head=rig.pose.bones['RB_P06_Rider_L0_Head'];rest=rig.data.bones[head.name]
original=[]
for frame in [1,31,61]:
 scene.frame_set(frame);bpy.context.view_layer.update();original.append((frame,head.matrix.copy()))
rows=[]
for frame,matrix in original:
 scene.frame_set(frame);forward=(matrix@rest.matrix_local.inverted()).to_3x3()@Vector((0,-1,0))
 yaw=Matrix.Rotation(math.radians(30),4,'Z');rotation=yaw@matrix.to_quaternion().to_matrix().to_4x4();axis=rotation.to_3x3()@rest.matrix_local.to_3x3().inverted()@Vector((1,0,0))
 pitched=Matrix.Rotation(math.radians(-4),4,axis)@rotation
 head.matrix=Matrix.Translation(matrix.translation)@pitched;bpy.context.view_layer.update();head.rotation_mode='QUATERNION';head.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=head.name)
 after=(head.matrix@rest.matrix_local.inverted()).to_3x3()@Vector((0,-1,0));rows.append({'frame':frame,'beforeForward':list(forward),'afterForward':list(after),'headOriginDisplacementMetres':(head.head-matrix.translation).length})
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_MENU_GAZE '+json.dumps({'clip':'RB_MenuHero','changedCurves':'Head.rotation_quaternion only','worldYawDeltaDegrees':30,'headPitchDeltaDegrees':-4,'samples':rows,'gameplayActionChanges':0,'visualAccepted':False}))
