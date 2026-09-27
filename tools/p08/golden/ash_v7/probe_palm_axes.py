import bpy,json
from mathutils import Vector
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update();P='RB_P06_Rider_L0_';rows=[]
for side in ['L','R']:
 hand=rig.data.bones[P+'Hand_'+side];long=(rig.data.bones[P+'Finger_Middle_1_'+side].head_local-hand.head_local).normalized();across=(rig.data.bones[P+'Finger_Index_1_'+side].head_local-rig.data.bones[P+'Finger_Pinky_1_'+side].head_local).normalized();normal=across.cross(long).normalized();transform=(rig.pose.bones[hand.name].matrix@hand.matrix_local.inverted()).to_3x3()
 rows.append({'side':side,'palmLongWorld':list(transform@long),'crossNormalWorld':list(transform@normal),'wrist':list(rig.pose.bones[hand.name].head),'fingers':[{'name':b.name,'head':list(b.head),'tip':list(b.tail),'localRotation':list(b.rotation_quaternion)} for b in rig.pose.bones if 'Finger_' in b.name and b.name.endswith('_'+side)]})
print('ASH_V7_PALM_AXES '+json.dumps(rows))
