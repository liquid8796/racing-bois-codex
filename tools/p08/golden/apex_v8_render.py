"""Actual CPU renders from the currently saved V8 Blender scene."""
import bpy
from mathutils import Vector
scene=bpy.context.scene
scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=1000
scene.render.resolution_percentage=100
camera=scene.camera
for label,position,target,ortho in [
    ('beauty',(-3.6,3.30,1.42),(0,0,.61),False),
    ('side',(-4,0,.67),(0,0,.64),True),
    ('front',(0,4,1.04),(0,.20,.64),False),
    ('rear',(0,-4,1.04),(0,-.12,.64),False)]:
    camera.data.type='ORTHO' if ortho else 'PERSP'
    camera.data.ortho_scale=2.52;camera.data.lens=68
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/v8/apex-'+label+'.png'
    bpy.ops.render.render(write_still=True)
    print('APEX_V8_VIEW '+scene.render.filepath)
