import bpy,json
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.44
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1200;scene.render.resolution_y=1200
shots=[('equipment-front-final',(0,-3.5,1.70),(0,-.05,1.695)),('equipment-quarter-final',(1.1,-3.5,1.74),(0,-.06,1.687)),('equipment-side-final',(3.5,0,1.70),(0,-.02,1.695))]
for name,position,target in shots:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v5/'+name+'.png';bpy.ops.render.render(write_still=True)
print('ASH_V5_EQUIPMENT_REVIEW '+json.dumps({'shots':[s[0] for s in shots],'geometryCandidateOnly':True,'visualAccepted':False}))
