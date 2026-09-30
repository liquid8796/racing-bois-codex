import bpy,json
from mathutils import Vector
if bpy.data.filepath.replace('\\','/')!='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V8/RB_Golden_Ash_V8_Jacket01.blend':
    raise RuntimeError('Exact owned pre-edit source required')
if bpy.context.preferences.filepaths.use_scripts_auto_execute:
    raise RuntimeError('Auto-execute unexpectedly enabled')
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig']
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
for level in range(3):bpy.data.objects['AshV7_L'+str(level)+'_Skin'].hide_render=level!=0
for name in ['ApexR2_ContactReferenceOnly','ApexR4_ContactReferenceOnly']:
    bpy.data.collections[name].hide_render=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
camera=scene.camera;camera.data.type='ORTHO';rows=[]
for label,target,offset,scale,width,height in [
    ('body-front',(0,0,.92),(0,-4,.02),1.98,900,1200),
    ('portrait-front',(0,-.01,1.585),(0,-4,0),.62,1100,1100),
    ('portrait-profile',(0,-.01,1.585),(-4,0,0),.62,1100,1100)]:
    marker='ash_v8_jacket01_render_'+label
    if scene.get(marker):raise RuntimeError('Preserve existing before render: '+label)
    scene[marker]=True
    target=Vector(target);camera.location=target+Vector(offset)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.resolution_x=width;scene.render.resolution_y=height
    path='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v8/jacket01/'+label+'.png'
    scene.render.filepath=path;bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
    rows.append(dict(label=label,path=path,cameraLocation=list(camera.location),cameraRotation=list(camera.rotation_euler),
        orthoScale=scale,width=width,height=height,frame=scene.frame_current,action=rig.animation_data.action.name))
print('ASH_V8_JACKET01_RENDERS '+json.dumps(dict(rows=rows,sourceSaved=False,autoexecute=bpy.context.preferences.filepaths.use_scripts_auto_execute,visualAccepted=False)))
