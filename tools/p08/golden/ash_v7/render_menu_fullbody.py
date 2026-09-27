REVIEW_START=1;REVIEW_END=4
"""Seventeen separate real full-body renders; camera fits actual posed bounds."""
import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];obj=bpy.data.objects['AshV7_L0_Skin'];camera=scene.camera
samples=[('idle','RB_Idle',0),('menu-start','RB_MenuHero',0),('menu-mid','RB_MenuHero',.5),('menu-end','RB_MenuHero',1),('ride','RB_Ride',0),('lean-left','RB_LeanLeft',.5),('lean-right','RB_LeanRight',.5),('attack-left','RB_AttackLeft',.5),('attack-right','RB_AttackRight',.5),('kick-left','RB_KickLeft',.5),('kick-right','RB_KickRight',.5),('hit','RB_Hit',.5),('fall-start','RB_Fall',0),('fall-mid','RB_Fall',.5),('fall-end','RB_Fall',1),('run','RB_Run',.25),('remount','RB_Remount',.5)]
bpy.data.collections['ApexR2_ContactReferenceOnly'].hide_render=True;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1000;scene.render.resolution_y=1000;camera.data.type='ORTHO';rows=[]
for number,(name,action,t) in enumerate(samples):
 if not REVIEW_START<=number<REVIEW_END:continue
 clip=bpy.data.actions[action];rig.animation_data.action=clip;a,b=clip.frame_range;f=a+(b-a)*t;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();minimum=Vector(tuple(min(v.co[k] for v in m.vertices) for k in range(3)));maximum=Vector(tuple(max(v.co[k] for v in m.vertices) for k in range(3)));ev.to_mesh_clear();target=(minimum+maximum)*.5;camera.location=target+Vector((2.2,-4.6,.35));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=max(maximum.z-minimum.z,maximum.x-minimum.x,maximum.y-minimum.y)*1.24
 scene.render.filepath=ROOT+'docs/p08/golden/ash/v7/poses/%02d-%s.png'%(number+1,name);bpy.ops.render.render(write_still=True);rows.append({'image':scene.render.filepath,'clip':action,'normalizedTime':t,'bodyBoundsMin':list(minimum),'bodyBoundsMax':list(maximum)})
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
print('ASH_V7_FULLBODY_REVIEW '+json.dumps({'actualRenders':len(rows),'poses':rows,'visualAccepted':False}))
