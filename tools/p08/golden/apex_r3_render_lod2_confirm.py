import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera;root=bpy.data.objects['RB_Golden_Apex_r3'];states=[]
for o in root.children_recursive:
    if o.type=='MESH':states.append((o,o.hide_render));o.hide_render='_L2_' not in o.name
try:
    scene.cycles.device='CPU';scene.cycles.samples=20;scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.resolution_x=1400;scene.render.resolution_y=980;scene.render.resolution_percentage=100
    camera.data.type='PERSP';camera.data.lens=68;camera.location=(3.6,3.3,1.42);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
    back=bpy.data.objects.get('Apex V8 studio cyclorama')
    if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/lod2-confirmed.png';bpy.ops.render.render(write_still=True)
finally:
    for o,hidden in states:o.hide_render=hidden
print('APEX_R3_CONFIRMED_SINGLE_RENDER '+json.dumps({'path':scene.render.filepath,'lod':2,'visualAccepted':False,'sourceFileUnchanged':True}))
