import bpy,math,json
o=bpy.data.objects['Garage_L0_BackPanel_0_0'];m=o.data
assert '/Garage/V2/' in bpy.data.filepath.replace('\\','/')
bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
layer=m.uv_layers.get('LightmapUV') or m.uv_layers.new(name='LightmapUV')
m.uv_layers.active=layer
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025,area_weight=1.0,correct_aspect=False,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT');m.calc_loop_triangles();layer=m.uv_layers.get('LightmapUV');bad=0;minimum=1
for tri in m.loop_triangles:
    a,b,c=[layer.data[i].uv for i in tri.loops];ab=b-a;ac=c-a;area=abs(ab.x*ac.y-ab.y*ac.x);minimum=min(minimum,area);bad+=area<=1e-14
print('BLENDER_UV_PROBE '+json.dumps({'mesh':o.name,'triangles':len(m.loop_triangles),'badUv':bad,'minimumUvCross':minimum,'saved':False}))
