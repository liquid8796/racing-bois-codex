import bpy
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
camera=scene.camera;camera.location=(0,-3,1.63);camera.rotation_euler=(Vector((0,-.04,1.63))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.45
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.cycles.samples=32
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v2/runtime-face-curved-optics.png'
bpy.ops.render.render(write_still=True)
print('ASH_CURVED_OPTICS_RENDERED')
