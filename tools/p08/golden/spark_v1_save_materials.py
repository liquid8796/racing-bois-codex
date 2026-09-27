import bpy,json
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V1/RB_Golden_Spark_v1_editable.blend')
print(json.dumps({'saved':bpy.data.filepath,'visualAccepted':False,'shaderUvScale':1}))
