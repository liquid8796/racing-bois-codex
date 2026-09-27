import bpy,json
from mathutils import Vector
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
assert bpy.data.filepath.replace('\\','/').endswith('/Spark/V2/RB_Golden_Spark_v2_editable.blend')
s=bpy.context.scene;c=s.camera
c.location=(5, 0, 0.61);c.data.type='ORTHO';c.data.lens=81;c.data.ortho_scale=2.38
c.rotation_euler=(Vector((0,0,.61))-c.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1536;s.render.resolution_y=1024;s.render.resolution_percentage=100
s.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/spark/v2/01-side.png'
bpy.ops.render.render(write_still=True)
print('SPARK_V2_RENDER='+json.dumps({'path':s.render.filepath,'view':'side','source':bpy.data.filepath,'sameCameraAsV1_04':True,'visualAccepted':False,'exported':False}))
