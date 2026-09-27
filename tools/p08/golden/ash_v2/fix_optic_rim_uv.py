"""Map optical edge returns into the declared uniform glass finish field."""
import bpy,math,json
rows=[]
for level in range(3):
    obj=bpy.data.objects['AshV2_L'+str(level)+'_Skin'];data=obj.data;data.calc_loop_triangles();uv=data.uv_layers.active;broken=set()
    for tri in data.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops]
        if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-12:
            name=data.materials[tri.material_index].name
            if name!='AshV2_AmberLens_Baked':raise RuntimeError('Unexpected UV problem in '+name)
            broken.add(tri.polygon_index)
    for index in broken:
        polygon=data.polygons[index];count=len(polygon.loop_indices)
        for layer in data.uv_layers:
            for i,loop in enumerate(polygon.loop_indices):
                angle=math.tau*i/count
                layer.data[loop].uv=(.6006+math.cos(angle)*.008,.5186+math.sin(angle)*.008)
    rows.append({'level':level,'edgeReturnFacesMapped':len(broken)})
print('ASH_OPTIC_EDGE_UV '+json.dumps(rows))
