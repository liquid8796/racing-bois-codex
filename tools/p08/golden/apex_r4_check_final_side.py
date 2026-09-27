import bpy,math,json
from mathutils import Vector
scene=bpy.context.scene;camera=scene.camera;root=bpy.data.objects['RB_Golden_Apex_r4']
for o in root.children_recursive:
 if o.type=='MESH':o.hide_render='_L0_' not in o.name
camera.data.type='ORTHO';camera.data.lens=68;camera.data.ortho_scale=2.5;camera.location=(5, 0, 1.01);camera.rotation_euler=(Vector((0,0,.61))-camera.location).to_track_quat('-Z','Y').to_euler()
back=bpy.data.objects.get('Apex V8 studio cyclorama')
if back:back.rotation_euler.z=math.atan2(camera.location.x,-camera.location.y)
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r4/final-side.png'
bpy.ops.render.render(write_still=True)
for o in root.children_recursive:
 if o.type=='MESH':o.hide_render='_L0_' not in o.name
print(json.dumps({'render':scene.render.filepath,'lod':0,'restoredLod0':True,'visualAccepted':False}))
