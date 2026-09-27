import bpy,json
print('MENU_SCENE_BEFORE '+json.dumps({'filepath':bpy.data.filepath,'dirty':bpy.data.is_dirty,'objects':len(bpy.data.objects)}))
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Canyon/V16/RB_Golden_Canyon.blend',load_ui=False,use_scripts=False)
root=bpy.data.objects['RB_Golden_Canyon'];rows=[]
for obj in root.children_recursive:
    if obj.type!='MESH' or '_L0_' not in obj.name:continue
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    minimum=[min(p[i] for p in points) for i in range(3)];maximum=[max(p[i] for p in points) for i in range(3)]
    rows.append({'name':obj.name,'location':list(obj.location),'minBlender':minimum,'maxBlender':maximum,'materials':[m.name for m in obj.data.materials],'vertices':len(obj.data.vertices)})
print('MENU_SOURCE_PROBE '+json.dumps({'filepath':bpy.data.filepath,'objects':rows,'camera':{'location':list(bpy.context.scene.camera.location),'rotation':list(bpy.context.scene.camera.rotation_euler)}}))
