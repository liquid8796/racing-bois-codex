import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
assert bpy.data.filepath.replace('\\','/').endswith('/Garage/V7/RB_Golden_Garage.blend')
root=bpy.data.objects['RB_Golden_Garage'];states=[]
bpy.ops.object.select_all(action='DESELECT')
for o in root.children_recursive:
    if o.type=='MESH':assert all(len(p.vertices)==3 for p in o.data.polygons),o.name
    states.append((o,o.hide_get(),o.hide_render));o.hide_set(False);o.hide_render=False;o.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-garage-v7-staging/RB_Golden_Garage.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=False,use_triangles=False,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for o,hidden,render_hidden in states:o.hide_set(hidden);o.hide_render=render_hidden
print('GARAGE_V7_EXPORT '+json.dumps({'fbx':'_local/p08-garage-v7-staging/RB_Golden_Garage.fbx','source':'ArtSource/P08/Golden/Garage/V7/RB_Golden_Garage.blend','allFacesExplicitTriangles':True,'exporterTriangulation':False,'exporterModifiers':False,'assetsWritten':False,'visualAccepted':False}))
