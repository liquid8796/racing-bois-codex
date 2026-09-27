import bpy,json
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];scene.frame_set(1)
reference=bpy.data.collections['ApexR2_ContactReferenceOnly'];reference.hide_render=False
bike=bpy.data.objects['RB_Golden_Apex_v8_r2'];old=bike.location.copy();bike.location=(-.30,-.25,0);bpy.context.view_layer.update()
camera=scene.camera;camera.data.type='ORTHO';scene.cycles.samples=24;scene.cycles.use_denoising=True
shots=[('menu-hero-r2-roll-fixed',(-3.2,-3.6,1.38),(-.15,-.02,.93),3.30,(1600,1100)),
    ('menu-hand-tail-roll-fixed',(-.88,.91,1.40),(-.23,.49,1.065),.39,(900,900)),
    ('menu-hand-tank-roll-fixed',(-.65,-.85,1.48),(-.18,-.28,1.055),.37,(900,900))]
try:
    for name,position,target,scale,size in shots:
        camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
        scene.render.resolution_x,scene.render.resolution_y=size;scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v4/'+name+'.png'
        bpy.ops.render.render(write_still=True)
finally:bike.location=old;reference.hide_render=True;bpy.context.view_layer.update()
print('ASH_V4_MENU_REVIEW '+json.dumps({'clip':'RB_MenuHero','referenceBike':'Actual ApexR2 imported FBX; appearance not a native material/fidelity claim','shots':[v[0] for v in shots],'visualAccepted':False}))
