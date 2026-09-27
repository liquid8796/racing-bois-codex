import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Canyon'];rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH':continue
    obj.data.calc_loop_triangles();before=len(obj.data.loop_triangles)
    changed=obj.data.validate(clean_customdata=False,verbose=False);obj.data.update();obj.data.calc_loop_triangles()
    if changed:rows.append({'name':obj.name,'beforeTriangles':before,'afterTriangles':len(obj.data.loop_triangles)})
bpy.ops.object.select_all(action='DESELECT')
for obj in root.children_recursive:obj.hide_set(False);obj.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-canyon-v16-staging/RB_Golden_Canyon.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for obj in root.children_recursive:
    if '_L1_' in obj.name or '_L2_' in obj.name:obj.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend')
print('CANYON_SOURCE_NORMALIZED '+json.dumps({'changedObjects':rows,'removedDuplicateTriangles':sum(row['beforeTriangles']-row['afterTriangles'] for row in rows)}))
