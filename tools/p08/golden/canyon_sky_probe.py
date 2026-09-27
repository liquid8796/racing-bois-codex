import bpy,json
sky=next(n for n in bpy.context.scene.world.node_tree.nodes if n.type=='TEX_SKY')
print('SKY_PROPERTIES '+json.dumps([p.identifier for p in sky.bl_rna.properties]))
print('SKY_TYPES '+json.dumps([v.identifier for v in sky.bl_rna.properties['sky_type'].enum_items]))
