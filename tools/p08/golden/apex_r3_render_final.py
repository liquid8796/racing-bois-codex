import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera;root=bpy.data.objects['RB_Golden_Apex_r3']
scene.cycles.device='CPU';scene.cycles.samples=20;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=980;scene.render.resolution_percentage=100
views=[('beauty-final',(3.6,3.3,1.42),'PERSP',2.5),('front-final',(0,5,1.00),'ORTHO',1.95),('side-final',(5,0,1.01),'ORTHO',2.5),('rear-final',(0,-5,1.00),'ORTHO',1.95)]
for o in root.children_recursive:
    if o.type=='MESH':o.hide_render='_L0_' not in o.name
for name,position,kind,scale in views:
    camera.data.type=kind;camera.data.lens=68;camera.data.ortho_scale=scale;camera.location=position;camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
    back=bpy.data.objects.get('Apex V8 studio cyclorama')
    if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/'+name+'.png';bpy.ops.render.render(write_still=True)
    print('APEX_R3_FINAL_RENDER '+json.dumps({'path':scene.render.filepath,'lod':0,'visualAccepted':False}))
camera.data.type='PERSP';camera.data.lens=68;camera.location=(3.6,3.3,1.42);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
back=bpy.data.objects.get('Apex V8 studio cyclorama')
if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
for level in [1,2]:
    for o in root.children_recursive:
        if o.type=='MESH':o.hide_render=('_L%d_'%level) not in o.name
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/lod%d-final.png'%level;bpy.ops.render.render(write_still=True)
    print('APEX_R3_FINAL_RENDER '+json.dumps({'path':scene.render.filepath,'lod':level,'visualAccepted':False}))
for o in root.children_recursive:
    if o.type=='MESH':o.hide_render='_L0_' not in o.name
