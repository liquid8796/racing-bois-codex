import bpy,json
bpy.ops.wm.open_mainfile(filepath='D:/Project/Unity/racing-bois/ArtSource/P08/Golden/Ash/V7/RB_Golden_Ash_V7.blend')
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV7_L'+str(level)+'_Skin'];m=obj.data;m.calc_loop_triangles();minimum=1;bad=[];minimum_poly=-1
    for tri in m.loop_triangles:
        a,b,c=[m.uv_layers[0].data[i].uv for i in tri.loops]
        cross=(float(b.x)-float(a.x))*(float(c.y)-float(a.y))-(float(b.y)-float(a.y))*(float(c.x)-float(a.x))
        if abs(cross)<minimum:minimum=abs(cross);minimum_poly=tri.polygon_index
        if abs(cross)<=1e-14:bad.append({'polygon':tri.polygon_index,'loops':list(tri.loops),'uv':[[float(v.x),float(v.y)] for v in [a,b,c]],'cross':cross})
    rows.append({'name':obj.name,'uvLayers':[layer.name for layer in m.uv_layers],'activeUv':m.uv_layers.active_index,'triangles':len(m.loop_triangles),'minimumCross':minimum,'minimumPolygon':minimum_poly,'failed':bad})
print('V7_SOURCE_UV_PROBE '+json.dumps({'file':bpy.data.filepath,'saved':False,'meshes':rows}))
