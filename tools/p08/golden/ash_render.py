"""Actual candidate inspection views; execute after ash_model through MCP."""
import bpy,math,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';OUT=ROOT+'docs/p08/golden/ash/'
scene=bpy.context.scene;camera=scene.camera
def coord(p):return Vector((-p[0],-p[2],p[1]))
scene.render.resolution_percentage=100;scene.cycles.samples=40
records=[]
for name,position,target,resolution,lens in [
    ('ash-fullbody',(1.65,1.05,3.65),(0,.95,0),(1000,1300),75),
    ('ash-front',(0,1.03,3.7),(0,.96,0),(1000,1300),75),
    ('ash-profile',(3.7,1.04,0),(0,.96,0),(1000,1300),75),
    ('ash-rear',(.0,1.04,-3.7),(0,.96,0),(1000,1300),75),
    ('ash-face',(.20,1.648,1.01),(0,1.64,.013),(1100,1100),88),
]:
    camera.location=coord(position);camera.rotation_euler=(coord(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=lens
    scene.render.resolution_x,scene.render.resolution_y=resolution;scene.render.filepath=OUT+name+'.png'
    bpy.ops.render.render(write_still=True);records.append({'path':OUT+name+'.png','actual3DRender':True})
print('ASH_INSPECTION_RENDERS '+json.dumps(records))
