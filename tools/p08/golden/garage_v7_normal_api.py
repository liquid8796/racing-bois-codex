import bpy,json
m=bpy.data.objects['Garage_L0_DisplayHelmet'].data
print('MESH_NORMAL_API '+json.dumps({'instanceSetter':hasattr(m,'normals_split_custom_set'),'functions':[name for name in m.bl_rna.functions.keys() if 'normal' in name],'attributes':[(a.name,a.domain,a.data_type) for a in m.attributes]}))
