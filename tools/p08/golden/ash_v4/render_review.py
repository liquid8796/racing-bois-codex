import bpy,json
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True;bpy.data.objects['AshV2_ReviewFloor'].location.z=0
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
camera=scene.camera;camera.data.type='ORTHO'
shots=[('front-tailored',(0,-4,1.03),(0,-.03,.93),2.05,(1100,1400)),
    ('side-tailored',(4,0,1.03),(0,-.03,.93),2.05,(1100,1400)),
    ('quarter-tailored',(2.8,-4,1.3),(0,-.03,.93),2.05,(1100,1400)),
    ('portrait-tailored',(1.1,-3.5,1.74),(0,-.06,1.687),.43,(1200,1200))]
for name,position,target,scale,size in shots:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=size;scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v4/'+name+'.png'
    bpy.ops.render.render(write_still=True)
print('ASH_V4_REVIEW_RENDER '+json.dumps({'shots':[v[0] for v in shots],'proceduralSourceNotBakedRuntime':True,'visualAccepted':False}))
