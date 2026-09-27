import bpy,json
root=bpy.data.objects['RB_Golden_Apex_r3'];rows=[]
for o in root.children_recursive:
    if not o.name.startswith('R3 Curved main fairing'):continue
    side=1 if o.name.endswith(' 1') else -1;changed=[]
    for p in o.data.polygons:
        target=0 if p.normal.x*side>.8 else 1 if p.normal.x*side<-.8 else p.material_index
        if target!=p.material_index:changed.append(p.index);p.material_index=target
    rows.append({'object':o.name,'correctedSurfaceAssignments':changed})
bpy.ops.wm.save_as_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Apex/V8/R3/RB_Golden_Apex_r3_editable.blend')
print('APEX_R3_CUT_MATERIAL_REPAIR '+json.dumps(rows))
