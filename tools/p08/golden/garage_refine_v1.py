import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Garage']
# The near panel edge meets its steel jamb. Move/extend only this authored wall.
for level in range(3):
    for i in range(3):
        o=bpy.data.objects['Garage_L%d_NearLeftPanel_%d'%(level,i)]
        old_x=-5.4+i*1.1;new_x=-5.35+i*1.2
        for v in o.data.vertices:v.co.x*=1.197/1.097
        o.location.x+=new_x-old_x
for image in bpy.data.images:
    if image.source=='FILE' and '/Garage/V1/Textures/' in image.filepath.replace('\\','/'):image.reload();image.pack()
for i,power in enumerate([60,35,25,65,40,40]):bpy.data.objects['Practical_%d'%i].data.energy=power
fill=bpy.data.objects['DoorSoftAmbient'];fill.data.energy=220;fill.data.color=(.85,.90,1)
for node in bpy.data.materials['Garage_Floor'].node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.55
bpy.context.scene.render.filepath=ROOT+'docs/p08/golden/garage/v1/gameplay-refined.png'
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V1/RB_Golden_Garage.blend')
print('GARAGE_REFINED '+json.dumps({'nearWallJoinsJamb':True,'actualFloorMapsReloaded':True,'visualAccepted':False}))
