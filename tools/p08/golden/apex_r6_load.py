import bpy
import json
bpy.ops.wm.open_mainfile(filepath="D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/R5/RB_Golden_Apex_r5_editable01.blend",load_ui=False,use_scripts=False)
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
print(json.dumps({"loaded":bpy.data.filepath,"dirty":bpy.data.is_dirty,"root":"RB_Golden_Apex_r5","objects":len(bpy.context.scene.objects)}))
