import bpy
root=bpy.data.objects['RB_Golden_Apex_r3']
for o in root.children_recursive:
    if o.type=='MESH' and 'brake swept ring' in o.name:
        o.data.materials.clear();o.data.materials.append(bpy.data.materials['Apex_Machined'])
        for p in o.data.polygons:p.material_index=0
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('R3 drilled walls bound to machined rotor material; no empty slots.')
