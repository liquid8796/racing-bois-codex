"""Compare hand curl axes in memory; never keyframe or save descriptor inputs."""
import bpy,math
from mathutils import Vector,Matrix
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];camera=scene.camera;PREFIX='RB_P06_Rider_L0_'
old_action=rig.animation_data.action;old_frame=scene.frame_current
rig.animation_data.action=bpy.data.actions['RB_Ride'];scene.frame_set(8);bpy.context.view_layer.update()
bases={bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones};rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=bases[bone.name]
bpy.context.view_layer.update()
hand=rig.pose.bones[PREFIX+'Hand_L'];center=(hand.head+hand.tail)*.5
camera.location=center+Vector((.30,-.33,.18));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.275
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.cycles.samples=24
try:
    for name,mode in [('global-axis',0),('palm-axis',1),('opposite-axis',-1)]:
        for bone in rig.pose.bones:bone.matrix_basis=bases[bone.name]
        if mode:
            for side,sign in [('L',-1),('R',1)]:
                axis=(rig.data.bones[PREFIX+'Finger_Index_1_'+side].head_local-rig.data.bones[PREFIX+'Finger_Pinky_1_'+side].head_local).normalized()*sign*mode
                for digit in ['Index','Middle','Ring','Pinky']:
                    for segment,degrees in [(1,48),(2,68),(3,38)]:
                        bone=rig.pose.bones[PREFIX+'Finger_'+digit+'_'+str(segment)+'_'+side]
                        rest=rig.data.bones[bone.name].matrix_local
                        rotation=Matrix.Rotation(math.radians(degrees*.82),4,axis)
                        bone.rotation_quaternion=(rest.inverted()@rotation@rest).to_quaternion()
        bpy.context.view_layer.update()
        scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v2/private-fingers-'+name+'.png'
        bpy.ops.render.render(write_still=True);print('PRIVATE_FINGER_AXIS '+scene.render.filepath)
finally:
    rig.animation_data.action=old_action;scene.frame_set(old_frame);bpy.context.view_layer.update()
print('NO_KEYS_OR_DESCRIPTOR_INPUT_FILES_CHANGED')
