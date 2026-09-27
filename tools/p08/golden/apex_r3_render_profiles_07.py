import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera
scene.cycles.device='CPU';scene.cycles.samples=20;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=980;scene.render.resolution_percentage=100
views=[('side-07',(5,0,1.01),'ORTHO',2.5),('front-07',(0,5,1.00),'ORTHO',1.95),('rear-07',(0,-5,1.00),'ORTHO',1.95)]
for name,position,kind,scale in views:
    camera.data.type=kind;camera.data.ortho_scale=scale;camera.location=position;camera.rotation_euler=(Vector((0,0,.60))-camera.location).to_track_quat('-Z','Y').to_euler()
    back=bpy.data.objects.get('Apex V8 studio cyclorama')
    if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/'+name+'.png';bpy.ops.render.render(write_still=True)
    print('APEX_R3_PROFILE '+json.dumps({'file':scene.render.filepath,'visualAccepted':False}))

