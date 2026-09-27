import bpy,json
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True
bpy.data.objects['AshV2_ReviewFloor'].location.z=.0
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=2.05
camera.location=(0,-4,1.03);camera.rotation_euler=(Vector((0,-.03,.93))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1100;scene.render.resolution_y=1400;scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v4/front-material-pass.png'
bpy.ops.render.render(write_still=True)
print('ASH_V4_FRONT_PREVIEW '+json.dumps({'path':scene.render.filepath,'clip':'RB_Idle','newMaterialSourcesNotYetBaked':True,'visualAccepted':False}))
