import bpy,json
rows=[]
for level in range(3):
 obj=bpy.data.objects['AshV7_L'+str(level)+'_Glass'];bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.008,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
 obj.hide_set(level!=0);rows.append({'lod':level,'uv':'UV0','constantMapSamplingUnchanged':True})
print('ASH_V7_GLASS_UV '+json.dumps(rows))
