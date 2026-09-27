import bpy
scene=bpy.context.scene
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.device='CPU';scene.cycles.samples=32
scene.render.resolution_percentage=100
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/gameplay-v12.png'
bpy.ops.render.render(write_still=True)
print('CANYON_RENDER_DONE '+scene.render.filepath)
