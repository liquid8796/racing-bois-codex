import bpy,json
root=bpy.data.objects['RB_Golden_Apex_r3'];rows=[]
for o in root.children_recursive:
    if o.type!='MESH':continue
    o.data.calc_loop_triangles();before=len(o.data.loop_triangles);changed=o.data.validate(clean_customdata=False);o.data.update();o.data.calc_loop_triangles()
    if changed or before!=len(o.data.loop_triangles):rows.append({'name':o.name,'before':before,'after':len(o.data.loop_triangles),'changed':changed})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('APEX_R3_SOURCE_NORMALIZED '+json.dumps(rows))
