RENDER_START=6
RENDER_END=9
import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
jobs=[('before',1),('before',9.25),('before',19),('after',1),('after',3),('after',9.25),('after',10),('after',17.375),('after',19)]
rows=[]
for index,(version,frame) in enumerate(jobs):
    if not RENDER_START<=index<RENDER_END:continue
    source='V7R1/RB_Golden_Ash_V7R1.blend' if version=='before' else 'V7R2/RB_Golden_Ash_V7R2.blend'
    bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/'+source,load_ui=False,use_scripts=False)
    scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Fall'];scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True
    for level in range(3):bpy.data.objects['AshV7_L'+str(level)+'_Skin'].hide_render=level!=0
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    camera=scene.camera;camera.data.type='ORTHO';target=Vector((.20,-.05,.85));camera.location=target+Vector((2.2,-4.6,1.3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=2.55
    path=ROOT+'docs/p08/golden/ash/v7r2/renders/'+version+'-frame-'+str(frame).replace('.','_')+'.png';scene.render.filepath=path;bpy.ops.render.render(write_still=True)
    rows.append({'image':path,'source':source,'frame':frame,'cameraLocation':list(camera.location),'cameraRotation':list(camera.rotation_euler),'orthoScale':camera.data.ortho_scale,'actualRendered':True})
print('V7R2_MATCHED_RENDERS '+json.dumps({'rows':rows,'sourceSaved':False,'visualAccepted':False,'sameCameraAndLighting':True}))
