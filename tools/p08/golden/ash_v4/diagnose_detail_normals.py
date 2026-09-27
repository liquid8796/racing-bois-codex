import bpy,json
from mathutils import Vector
scene=bpy.context.scene;obj=bpy.data.objects['AshV4_L0_Skin'];rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1)
slot=next(i for i,m in enumerate(obj.data.materials) if m.name=='AshV4_LeatherDetails_Baked');original=obj.data.materials[slot]
copy=original.copy();copy.name='AshV4_PrivateDetailNormalProbe';obj.data.materials[slot]=copy
for node in copy.node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=0
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.45;camera.location=(1.1,-3.5,1.74);camera.rotation_euler=(Vector((0,-.06,1.66))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.cycles.samples=24;scene.render.resolution_x=1200;scene.render.resolution_y=1200
scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v4/private-collar-no-normal.png'
try:bpy.ops.render.render(write_still=True)
finally:obj.data.materials[slot]=original;bpy.data.materials.remove(copy)
print('ASH_V4_PRIVATE_NORMAL_PROBE '+json.dumps({'path':scene.render.filepath,'sourceSaved':False,'originalMaterialRestored':True}))
