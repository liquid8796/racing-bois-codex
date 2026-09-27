import bpy,json
rows=[]
for level in range(3):
 o=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];m=o.data;m.calc_loop_triangles();bad=[];uvs={l.name:[] for l in m.uv_layers}
 for tri in m.loop_triangles:
  a,b,c=[m.vertices[i].co for i in tri.vertices]
  if (b-a).cross(c-a).length_squared<=1e-16:bad.append({'t':tri.index,'p':tri.polygon_index,'role':m.materials[m.polygons[tri.polygon_index].material_index].name})
  for layer in m.uv_layers:
   a,b,c=[layer.data[i].uv for i in tri.loops];ab=b-a;ac=c-a
   if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvs[layer.name].append(tri.index)
 rows.append({'lod':level,'triangles':len(m.loop_triangles),'physical':bad,'uvLayers':{n:{'failures':len(v),'first':v[:10]} for n,v in uvs.items()},'materials':[mat.name for mat in m.materials]})
print('ASH_V6_RUNTIME_PROBE '+json.dumps(rows))
