"""Three actual model expression portraits, never generated concept cutouts."""
import bpy,json
from mathutils import Vector,Quaternion
ROOT='D:/Project/Unity/racing-bois/';OUT=ROOT+'Assets/RacingBois/Art/P08/Golden/Ash/'
scene=bpy.context.scene;camera=scene.camera;rig=bpy.data.objects['RB_P06_Rider_Rig']
def coord(p):return Vector((-p[0],-p[2],p[1]))
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.cycles.samples=48
camera.location=coord((.12,1.65,1.04));camera.rotation_euler=(coord((0,1.631,.015))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=80
records=[]
for index,expression in enumerate(['Neutral','Happy','Focused']):
    for obj in rig.children:
        if obj.type=='MESH':
            obj.data.shape_keys.key_blocks['Happy'].value=1 if expression=='Happy' else 0
            obj.data.shape_keys.key_blocks['Focused'].value=1 if expression=='Focused' else 0
    scene.render.filepath=OUT+'Ash_Portrait_'+expression+'.png';bpy.ops.render.render(write_still=True)
    records.append({'expression':expression,'path':scene.render.filepath,'actualModel':True,'shapeWeights':{'Happy':1 if expression=='Happy' else 0,'Focused':1 if expression=='Focused' else 0}})
for obj in rig.children:
    if obj.type=='MESH':
        obj.data.shape_keys.key_blocks['Happy'].value=0;obj.data.shape_keys.key_blocks['Focused'].value=0
print('ASH_ACTUAL_PORTRAITS '+json.dumps(records))
