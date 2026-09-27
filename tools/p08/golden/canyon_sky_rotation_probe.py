import bpy,math,json
scene=bpy.context.scene
mapping=next(n for n in scene.world.node_tree.nodes if n.type=='MAPPING')
rotation=mapping.inputs['Rotation'].default_value[2]
states=[(o,o.hide_render) for o in scene.objects]
for obj,state in states:
    if obj.type=='MESH':obj.hide_render=True
settings=(scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.cycles.samples,scene.render.filepath)
scene.render.resolution_x=512;scene.render.resolution_y=256;scene.render.resolution_percentage=100;scene.cycles.samples=2
for index in range(8):
    mapping.inputs['Rotation'].default_value[2]=index*math.pi/4
    scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/canyon/v13/sky-rotation-%02d.png'%index
    bpy.ops.render.render(write_still=True)
mapping.inputs['Rotation'].default_value[2]=rotation
for obj,state in states:obj.hide_render=state
scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage,scene.cycles.samples,scene.render.filepath=settings
print('CANYON_HDRI_ROTATIONS 8; restored original scene visibility and rotation')
