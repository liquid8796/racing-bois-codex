import bpy,json
ROOT='D:/Project/Unity/racing-bois/'
root=bpy.data.objects['RB_Golden_Garage'];states=[]
bpy.ops.object.select_all(action='DESELECT')
for o in root.children_recursive:
    states.append((o,o.hide_get(),o.hide_render));o.hide_set(False);o.hide_render=False;o.select_set(True)
root.select_set(True);bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-garage-v4-staging/RB_Golden_Garage.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for o,hidden,render_hidden in states:o.hide_set(hidden);o.hide_render=render_hidden
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend')
print('GARAGE_EXPORTED '+json.dumps({'path':'_local/p08-garage-v4-staging/RB_Golden_Garage.fbx','source':'ArtSource/P08/Golden/Garage/V4/RB_Golden_Garage.blend','rotationUnity':[0,0,0],'visualAccepted':False}))

