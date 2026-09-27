"""Fork immutable V4; remove only obsolete head equipment on the V5 copy."""
import bpy,json
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/'
bpy.ops.wm.open_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',load_ui=False,use_scripts=False)
rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
root=bpy.data.objects['RB_Golden_Ash_V4'];root.name='RB_Golden_Ash_V5'
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV4_L'+str(level)+'_Skin'];obj.name='AshV5_L'+str(level)+'_Skin';old=obj.data
    for key in old.shape_keys.key_blocks:key.value=0
    keep=[];removed={}
    for p in old.polygons:
        role=old.materials[p.material_index].name;low=min(old.vertices[i].co.z for i in p.vertices)
        remove=role in ['AshV2_AmberLens_Baked','AshV4_HelmetEnamel_Baked'] or (role=='AshV2_AgedBrass_Baked' and low>1.60) or (role=='AshV3_Rubber_Baked' and low>1.59) or (role=='AshV3_BootLeather_Baked' and low>1.50)
        if remove:removed[role]=removed.get(role,0)+1
        else:keep.append(p)
    used=sorted(set(i for p in keep for i in p.vertices));mapping={v:i for i,v in enumerate(used)}
    positions=[old.vertices[i].co.copy() for i in used]
    weights=[[(obj.vertex_groups[g.group].name,g.weight) for g in old.vertices[i].groups] for i in used]
    expressions={k.name:[k.data[i].co.copy() for i in used] for k in old.shape_keys.key_blocks}
    face_data=[(tuple(mapping[i] for i in p.vertices),p.material_index,p.use_smooth) for p in keep]
    uv={l.name:[[l.data[i].uv.copy() for i in p.loop_indices] for p in keep] for l in old.uv_layers}
    materials=list(old.materials);group_names=[g.name for g in obj.vertex_groups]
    obj.shape_key_clear();mesh=bpy.data.meshes.new(obj.name+'_HeadEquipmentRemoved');mesh.from_pydata(positions,[],[f[0] for f in face_data]);mesh.update();obj.data=mesh
    obj.vertex_groups.clear()
    for name in group_names:obj.vertex_groups.new(name=name)
    for mat in materials:mesh.materials.append(mat)
    for p,data in zip(mesh.polygons,face_data):p.material_index=data[1];p.use_smooth=data[2]
    for name,faces in uv.items():
        layer=mesh.uv_layers.new(name=name)
        for p,points in zip(mesh.polygons,faces):
            for loop,point in zip(p.loop_indices,points):layer.data[loop].uv=point
    mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
    for i,values in enumerate(weights):
        for name,w in values:obj.vertex_groups[name].add([i],w,'REPLACE')
    for name,coordinates in expressions.items():
        key=obj.shape_key_add(name=name,from_mix=False);key.value=0
        for v,co in zip(key.data,coordinates):v.co=co
    mesh.calc_loop_triangles();rows.append({'lod':level,'removedFacesByRole':removed,'remainingVertices':len(mesh.vertices),'remainingTriangles':len(mesh.loop_triangles),'retainedFaceShapeKeysAndWeightsCopied':True})
    obj.hide_render=level!=0;obj.hide_set(level!=0)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V5/RB_Golden_Ash_V5.blend',compress=False)
print('ASH_V5_HEAD_EQUIPMENT_FORK '+json.dumps({'meshes':rows,'sourceV4Preserved':True,'rigAndActionsEdited':False,'notReadyForExport':True}))
