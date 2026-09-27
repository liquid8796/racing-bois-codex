"""Controlled FBX triangulation variant of the unchanged frozen V5 source."""
import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
assert '/Garage/V5/' in bpy.data.filepath.replace('\\','/')
root=bpy.data.objects['RB_Golden_Garage'];states=[]
bpy.ops.object.select_all(action='DESELECT')
for obj in root.children_recursive:
    states.append((obj,obj.hide_get(),obj.hide_render));obj.hide_set(False);obj.hide_render=False;obj.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-garage-v6-staging/RB_Golden_Garage.fbx',use_selection=True,
    object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,use_triangles=True,
    add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for obj,hidden,render_hidden in states:obj.hide_set(hidden);obj.hide_render=render_hidden
print('GARAGE_TRIANGULATED_EXPORT '+json.dumps({'sourceUnchanged':bpy.data.filepath,'fbx':'_local/p08-garage-v6-staging/RB_Golden_Garage.fbx','explicitTriangles':True,'visualAccepted':False}))
