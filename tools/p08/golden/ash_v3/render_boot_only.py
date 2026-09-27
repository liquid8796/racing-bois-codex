import bpy
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_create();rig.animation_data.action=bpy.data.actions['RB_Ride'];scene.frame_set(1);bpy.context.view_layer.update()
camera=scene.camera;camera.location=(.68,-.37,.51);camera.rotation_euler=(Vector((.286,-.071,.44))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.4
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.cycles.samples=24;scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v3/boot-flat-bake.png'
bpy.ops.render.render(write_still=True)
