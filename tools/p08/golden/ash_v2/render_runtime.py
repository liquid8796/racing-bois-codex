"""Render the exact baked runtime LOD0, real expressions and action samples."""
import bpy,bmesh,math,json
from mathutils import Vector
scene=bpy.context.scene;rig=bpy.data.objects['RB_P06_Rider_Rig'];lod0=bpy.data.objects['AshV2_L0_Skin'];camera=scene.camera
bpy.data.collections['AshV2_Editable_Source'].hide_render=True
for level in range(3):bpy.data.objects['AshV2_L'+str(level)+'_Skin'].hide_render=level!=0
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
camera.data.type='ORTHO';ROOT='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v2/'
def neutral():
    for level in range(3):
        for key in bpy.data.objects['AshV2_L'+str(level)+'_Skin'].data.shape_keys.key_blocks:key.value=0
def action(name,fraction=0):
    rig.animation_data.action=bpy.data.actions[name];start,end=rig.animation_data.action.frame_range
    frame=start+(end-start)*fraction;scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
def shot(name,position,target,scale,resolution):
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.resolution_x,scene.render.resolution_y=resolution;scene.render.filepath=ROOT+name+'.png'
    bpy.ops.render.render(write_still=True);print('ASH_RUNTIME_RENDER '+scene.render.filepath)
neutral();action('RB_Idle')
for name,position,target,scale,resolution in [
    ('runtime-body-front',(0,-4,1.02),(0,0,.95),2.06,(1000,1400)),
    ('runtime-body-back',(0,4,1.02),(0,0,.95),2.06,(1000,1400)),
    ('runtime-body-side',(4,-.02,1.04),(0,-.02,.95),2.06,(1000,1400)),
    ('runtime-face-front',(0,-3,1.63),(0,-.04,1.63),.45,(1100,1100)),
    ('runtime-face-profile',(3,-.035,1.63),(0,-.035,1.63),.48,(1100,1100)),
]:shot(name,position,target,scale,resolution)
for name,key in [('neutral',None),('happy','Happy'),('focused','Focused')]:
    neutral()
    if key:
        for level in range(3):bpy.data.objects['AshV2_L'+str(level)+'_Skin'].data.shape_keys.key_blocks[key].value=1
    bpy.context.view_layer.update()
    shot('portrait-'+name,(.24,-3,1.636),(0,-.04,1.632),.405,(768,768))
neutral()
# An underlying-face diagnostic uses the same runtime mesh and baked maps,
# with only equipment faces omitted from a temporary copy. No reference image
# is substituted for geometry and the copy is removed before saving source.
head=lod0.copy();head.data=lod0.data.copy();scene.collection.objects.link(head);head.name='AshV2_TemporaryHeadInspection'
bm=bmesh.new();bm.from_mesh(head.data)
allowed={'AshV2_Skin_Baked','AshV2_Eyes_Baked','AshV2_Brows_Baked','AshV2_Hair_Baked','AshV2_HairFibers_Baked'}
remove=[face for face in bm.faces if head.data.materials[face.material_index].name not in allowed]
bmesh.ops.delete(bm,geom=remove,context='FACES_ONLY');bm.to_mesh(head.data);bm.free()
lod0.hide_render=True;head.hide_render=False
shot('runtime-unhelmeted-front',(0,-3,1.624),(0,-.04,1.624),.43,(1100,1100))
shot('runtime-unhelmeted-profile',(3,-.035,1.624),(0,-.035,1.624),.47,(1100,1100))
bpy.data.objects.remove(head,do_unlink=True);lod0.hide_render=False
for name,clip,fraction in [('ride','RB_Ride',0),('attack-left','RB_AttackLeft',.5),('kick-right','RB_KickRight',.5),('run','RB_Run',.33),('fall','RB_Fall',.95)]:
    action(clip,fraction);depsgraph=bpy.context.evaluated_depsgraph_get();mesh=lod0.evaluated_get(depsgraph).to_mesh()
    low=Vector([min(v.co[a] for v in mesh.vertices) for a in range(3)]);high=Vector([max(v.co[a] for v in mesh.vertices) for a in range(3)])
    center=(low+high)*.5;size=high-low;lod0.evaluated_get(depsgraph).to_mesh_clear()
    scale=max(size.z*1.15,math.hypot(size.x,size.y)*1.15/.8)
    shot('runtime-pose-'+name,center+Vector((3,-5,1.4)),center,scale,(800,1000))
neutral();action('RB_Idle')
camera.location=(0,-4,1.02);camera.rotation_euler=(Vector((0,0,.95))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=2.06
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V2/RB_Golden_Ash_V2.blend',compress=False)
print('ASH_RUNTIME_REVIEW_COMPLETE_VISUAL_ACCEPTANCE_PENDING')
