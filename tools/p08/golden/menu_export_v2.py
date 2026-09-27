import bpy,json
ROOT='D:/Project/Unity/racing-bois/';root=bpy.data.objects['RB_Golden_MenuEnvironment']
meshes=[o for o in root.children_recursive if o.type=='MESH']
assert all(len(p.vertices)==3 for o in meshes for p in o.data.polygons),'Explicit source triangles required'
bpy.ops.object.select_all(action='DESELECT')
for obj in [root]+list(root.children_recursive):obj.hide_set(False);obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=ROOT+'_local/p08-menu-environment-v2-staging/RB_Golden_MenuEnvironment.fbx',use_selection=True,object_types={'EMPTY','MESH'},axis_forward='-Z',axis_up='Y',use_mesh_modifiers=False,use_triangles=False,add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=True)
for obj in meshes:obj.hide_set('_L0_' not in obj.name);obj.hide_render='_L0_' not in obj.name
points=[obj.matrix_world@v.co for obj in meshes for v in obj.data.vertices]
minimum=[min(v[i] for v in points) for i in range(3)];maximum=[max(v[i] for v in points) for i in range(3)]
rows=[]
for obj in meshes:
    obj.data.calc_loop_triangles();rows.append({'name':obj.name,'triangles':len(obj.data.loop_triangles),'materials':[m.name for m in obj.data.materials]})
print('MENU_EXPORTED '+json.dumps({'objects':rows,'boundsMinUnity':[minimum[0],minimum[2],minimum[1]],'boundsMaxUnity':[maximum[0],maximum[2],maximum[1]],'rootIdentity':True,'modelRotationEuler':[0,0,0],'visualAccepted':False}))
