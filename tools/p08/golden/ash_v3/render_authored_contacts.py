"""Render actual keyed V3 clips and inspect material repairs; no pose substitution."""
import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera;rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data_create()
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;camera.data.type='ORTHO'
shots=[
 ('authored-contact-side','RB_Ride',0,(3,-.02,1.0),(0,-.20,.94),2.25,(1200,1000)),
 ('authored-contact-three-quarter','RB_Ride',0,(2.8,-4,2.0),(0,-.22,.91),2.55,(1200,1000)),
 ('authored-contact-hand-left','RB_Ride',0,(.58,-1.06,1.23),(.29,-.71,1.007),.29,(900,900)),
 ('authored-contact-hand-inside','RB_Ride',0,(.11,-.42,1.34),(.29,-.71,1.007),.30,(900,900)),
 ('authored-contact-boot','RB_Ride',0,(.68,-.37,.51),(.286,-.071,.44),.40,(900,900)),
 ('authored-lean-left','RB_LeanLeft',0,(2.8,-4,2.0),(0,-.22,.91),2.55,(1000,900)),
]
for name,clip,t,position,target,scale,resolution in shots:
    action=bpy.data.actions[clip];rig.animation_data.action=action;start,end=action.frame_range;frame=start+(end-start)*t;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale;scene.render.resolution_x,scene.render.resolution_y=resolution
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v3/'+name+'.png';bpy.ops.render.render(write_still=True)
rig.animation_data.action=bpy.data.actions['RB_Ride'];scene.frame_set(1);bpy.context.view_layer.update()
print('ASH_V3_AUTHORED_CLIP_RENDERS '+json.dumps([s[0] for s in shots]))
