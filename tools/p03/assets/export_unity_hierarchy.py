"""Re-export the already authored pack using metadata units, preserving joints."""
import bpy
import json
ROOT='D:/Project/Unity/racing-bois/'
names=['RB_Motorcycle','RB_Rider','RB_TrafficCoupe','RB_TrafficVan']
for name in names:
    root=bpy.data.objects.get(name)
    if root is None:raise RuntimeError('Missing root '+name)
    root.location=(0,0,0);root.rotation_euler=(0,0,0);root.scale=(1,1,1)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for obj in root.children_recursive:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    folder='Characters/' if name=='RB_Rider' else 'Vehicles/'
    bpy.ops.export_scene.fbx(filepath=ROOT+'Assets/RacingBois/Art/'+folder+name+'.fbx',use_selection=True,
        object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',bake_space_transform=False,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
print(json.dumps({'exported':names,'unit_policy':'FBX_SCALE_ALL','bake_space_transform':False}))
