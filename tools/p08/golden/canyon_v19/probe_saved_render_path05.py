import bpy,json
print('CANYON_V19_SAVED_PATH05 '+json.dumps({'source':bpy.data.filepath,
    'storedRenderPath':bpy.context.scene.render.filepath,
    'resolvedRenderPath':bpy.path.abspath(bpy.context.scene.render.filepath),
    'sourceSaved':False}))
