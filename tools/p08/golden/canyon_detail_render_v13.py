import bpy
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
position=camera.location.copy();rotation=camera.rotation_euler.copy();lens=camera.data.lens
original=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.cycles.samples,scene.render.filepath)
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
views=[('cliff-detail',(0,12,3),(-7,16,6),45),('rail-detail',(1.5,2,1.3),(4.0,5,.82),50),('foliage-detail',(-2,7,1.4),(-5,10,1.2),46)]
for name,eye,target,focal in views:
    camera.location=Vector(eye);camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=focal
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v13/'+name+'-v13.png'
    bpy.ops.render.render(write_still=True)
camera.location=position;camera.rotation_euler=rotation;camera.data.lens=lens
scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.cycles.samples,scene.render.filepath=original
print('CANYON_DETAILS_RENDERED 3; authoring camera restored')
