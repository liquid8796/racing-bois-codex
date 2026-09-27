import bpy, json
from mathutils import Vector
scene=bpy.context.scene
camera=scene.camera
scene.cycles.samples=24
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
for name,position,target,orthographic in [('side',(4,0,.72),(0,0,.62),True),('rear',(2.3,3.8,1.42),(0,0,.67),False),('rear-direct',(0,4,1.03),(0,.2,.65),False)]:
    camera.data.type='ORTHO' if orthographic else 'PERSP'
    camera.data.ortho_scale=2.65;camera.data.lens=66
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/apex-'+name+'.png'
    bpy.ops.render.render(write_still=True)
    print('APEX_VIEW_SAVED '+scene.render.filepath)
