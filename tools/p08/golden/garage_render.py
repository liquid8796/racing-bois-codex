import bpy,json
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
bpy.ops.render.render(write_still=True)
print('GARAGE_RENDER '+json.dumps({'path':scene.render.filepath,'cpuThreads':4,'visualAccepted':False}))
