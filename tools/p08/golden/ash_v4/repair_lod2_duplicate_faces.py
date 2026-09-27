import bpy,json,collections
ROOT='D:/Project/Unity/racing-bois/';obj=bpy.data.objects['AshV4_L2_Skin'];mesh=obj.data
vertices=[tuple(v.co) for v in mesh.vertices];keys=[[tuple(v.co) for v in k.data] for k in mesh.shape_keys.key_blocks]
weights=[[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]
seen={};duplicates=collections.Counter()
for p in mesh.polygons:
    identity=tuple(sorted(p.vertices))
    if identity in seen:duplicates[mesh.materials[p.material_index].name]+=1
    else:seen[identity]=p.index
mesh.calc_loop_triangles();before=len(mesh.loop_triangles);changed=mesh.validate(verbose=False,clean_customdata=False);mesh.calc_loop_triangles();after=len(mesh.loop_triangles)
assert changed and before-after==179,'Unexpected validation delta'
assert vertices==[tuple(v.co) for v in mesh.vertices]
assert keys==[[tuple(v.co) for v in k.data] for k in mesh.shape_keys.key_blocks]
assert weights==[[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V4/RB_Golden_Ash_V4.blend',compress=False)
print('ASH_V4_LOD2_VALIDATION_REPAIR '+json.dumps({'beforeTriangles':before,'afterTriangles':after,'duplicateFacesByMaterial':dict(duplicates),'verticesShapeKeysWeightsExact':True,'onlyV4Modified':True}))
