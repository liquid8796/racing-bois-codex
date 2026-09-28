import bpy
import json
print(json.dumps({"file":bpy.data.filepath,"dirty":bpy.data.is_dirty,"autoExecute":bpy.context.preferences.filepaths.use_scripts_auto_execute,"engine":bpy.context.scene.render.engine,"threads":bpy.context.scene.render.threads,"rootNames":[o.name for o in bpy.context.scene.objects if o.parent is None]}))
