import bpy,json
scene=bpy.context.scene;camera=scene.camera;material=bpy.data.materials['Apex_Lens'];shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
print('APEX_R3_LENS_MATERIAL '+json.dumps({'transmission':shader.inputs['Transmission Weight'].default_value,'ior':shader.inputs['IOR'].default_value,'specularIorLevel':shader.inputs['Specular IOR Level'].default_value,'coat':shader.inputs['Coat Weight'].default_value,'textures':[{'name':n.image.name,'path':n.image.filepath,'colorSpace':n.image.colorspace_settings.name} for n in material.node_tree.nodes if n.type=='TEX_IMAGE']}))
lenses=[o for o in bpy.data.objects if o.name.startswith('R3 Flat swept protective lens')];states=[o.hide_render for o in lenses]
old_path=scene.render.filepath;old_samples=scene.cycles.samples
try:
    for o in lenses:o.hide_render=True
    scene.cycles.samples=12;scene.render.filepath='D:/Project/Unity/racing-bois/docs/p08/golden/apex/r3/lens-off-diagnostic.png'
    bpy.ops.render.render(write_still=True)
finally:
    for o,state in zip(lenses,states):o.hide_render=state
    scene.render.filepath=old_path;scene.cycles.samples=old_samples
print('Lens-off diagnostic only; actual material and visibility restored, no acceptance claim.')
