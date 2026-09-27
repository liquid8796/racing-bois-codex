import bpy,json
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R2/RB_Golden_Apex_v8_r2_editable.blend',load_ui=False,use_scripts=False)
root=bpy.data.objects['RB_Golden_Apex_v8_r2']
print('APEX_R3_EDITABLE_INSPECTION '+json.dumps({'file':bpy.data.filepath,'components':[{'name':o.name,'type':o.type,'group':o.get('asset_group'),'materials':[m.name for m in o.data.materials] if o.type=='MESH' else []} for o in root.children_recursive]}))
