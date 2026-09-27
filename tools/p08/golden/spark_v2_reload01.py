import bpy,json
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Spark/V2/RB_Golden_Spark_v2_editable.blend',load_ui=False,use_scripts=False)
bpy.context.scene.blendermcp_auto_start_server=False
print('SPARK_V2_RELOADED='+json.dumps({'source':bpy.data.filepath,'modified':False,'scope':'Reset only owned Spark session to V2 geometry baseline before a fresh mechanical refinement.'}))
