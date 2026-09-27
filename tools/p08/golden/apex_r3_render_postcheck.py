import bpy,json
root=bpy.data.objects['RB_Golden_Apex_r3']
print('R3_RENDER_POSTCHECK '+json.dumps({'file':bpy.data.filepath,'lastRenderPath':bpy.context.scene.render.filepath,'renderResultSize':list(bpy.data.images['Render Result'].size),'renderVisibleMeshes':[o.name for o in root.children_recursive if o.type=='MESH' and not o.hide_render],'CPUThreads':bpy.context.scene.render.threads,'CPUDevice':bpy.context.scene.cycles.device}))
