import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_MenuHero'];scene.frame_set(1)
ref=bpy.data.collections['ApexR2_ContactReferenceOnly'];ref.hide_render=False;bike=bpy.data.objects['RB_Golden_Apex_v8_r2'];previous=bike.location.copy();bike.location=(-.30,-.25,0);bpy.context.view_layer.update()
camera=scene.camera;camera.data.type='ORTHO';scene.cycles.samples=16;scene.cycles.use_denoising=True
shots=[('menu-gaze-r2',(-3.2,-3.6,1.38),(-.15,-.02,.93),3.30,(1600,1100)),('menu-gaze-portrait',(-3.2,-3.6,1.80),(-.055,-.053,1.687),.43,(1000,1000))]
try:
 for name,position,target,scale,size in shots:
  camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale;scene.render.resolution_x,scene.render.resolution_y=size;scene.render.filepath=ROOT+'docs/p08/golden/ash/v6/'+name+'.png';bpy.ops.render.render(write_still=True)
finally:bike.location=previous;ref.hide_render=True;rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
print('ASH_V6_MENU_RENDER '+json.dumps({'shots':[s[0] for s in shots],'bikeReference':'ApexR2, final R3 contact validation remains required','visualAccepted':False}))
