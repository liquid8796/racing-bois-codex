"""Private material experiment only; no source/FBX/map is saved or overwritten."""
import bpy
from mathutils import Vector
scene=bpy.context.scene;obj=bpy.data.objects['AshV2_L0_Skin'];rig=bpy.data.objects['RB_P06_Rider_Rig'];camera=scene.camera
index=next(i for i,m in enumerate(obj.data.materials) if m.name=='AshV2_TailoredClothing_Baked')
original=obj.data.materials[index];candidate=original.copy();candidate.name='Private_Ash_TextureCandidate';obj.data.materials[index]=candidate
nodes=candidate.node_tree.nodes;links=candidate.node_tree.links;p=nodes['Principled BSDF'];base=p.inputs['Base Color'].links[0].from_socket
image=bpy.data.images.load('D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/TextureCandidates/tailored-leather-v1.png',check_existing=False);image.reload();probe=tuple(image.pixels[:4])
texture=nodes.new('ShaderNodeTexImage');texture.image=image
mix=nodes.new('ShaderNodeMixRGB');links.new(base,mix.inputs[1]);links.new(texture.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],p.inputs['Base Color'])
rig.animation_data.action=bpy.data.actions['RB_Idle'];scene.frame_set(1);bpy.context.view_layer.update()
camera.location=(.4,-4,1.05);camera.rotation_euler=(Vector((0,0,.99))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=2.04
scene.render.resolution_x=900;scene.render.resolution_y=1250;scene.cycles.samples=24
try:
    for name,amount in [('quarter',.25),('full',1.0)]:
        mix.inputs[0].default_value=amount
        scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/ash/v2/private-atlas-'+name+'.png'
        bpy.ops.render.render(write_still=True);print('PRIVATE_ATLAS_PREVIEW '+scene.render.filepath)
finally:
    obj.data.materials[index]=original
    bpy.data.materials.remove(candidate)
print('DESCRIPTOR_INPUT_FILES_UNCHANGED_NO_SOURCE_SAVE')
