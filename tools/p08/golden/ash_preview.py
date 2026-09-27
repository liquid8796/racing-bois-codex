import bpy,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
def coord(p):return Vector((-p[0],-p[2],p[1]))
scene.cycles.samples=24
records=[]
for name,position,target,resolution,lens in [('ash-preview-body',(1.5,1.1,3.7),(0,.97,0),(850,1100),75),('ash-preview-face',(.19,1.65,1.0),(0,1.65,.025),(900,900),85)]:
    camera.location=coord(position);camera.rotation_euler=(coord(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=lens
    scene.render.resolution_x,scene.render.resolution_y=resolution;scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/'+name+'.png'
    bpy.ops.render.render(write_still=True);records.append(scene.render.filepath)
print('ASH_PREVIEW '+json.dumps(records))
