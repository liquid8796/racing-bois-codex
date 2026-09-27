import bpy
import json
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend', load_ui=False, use_scripts=False)
assert not bpy.context.preferences.filepaths.use_scripts_auto_execute
root = bpy.data.objects['RB_Golden_Apex_r3']
root.name = 'RB_Golden_Apex_r4'
for obj in root.children:
    if obj.name.endswith('_Wheel_Front'):
        obj.name = 'RB_Golden_Apex_r4_Wheel_Front'
    elif obj.name.endswith('_Wheel_Rear'):
        obj.name = 'RB_Golden_Apex_r4_Wheel_Rear'
root['referenceConceptSha256'] = 'f8b09f6d24e95724be935f0993bfcd02d2bfaf070e85982c1eba57e6a8479819'
root['licensedGeometryImported'] = False
root['visualAccepted'] = False
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R4/RB_Golden_Apex_r4_editable.blend')
print('R4_SOURCE=' + json.dumps({'path': bpy.data.filepath, 'components': [{'name': o.name, 'type': o.type, 'group': o.get('asset_group')} for o in root.children_recursive]}))
