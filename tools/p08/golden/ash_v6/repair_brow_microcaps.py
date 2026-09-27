import bpy,json
from mathutils import Vector
ROOT='D:/Project/Unity/racing-bois/';rows=[]
for level in range(3):
 o=bpy.data.objects['AshV6_L'+str(level)+'_Skin'];m=o.data;m.calc_loop_triangles();bad=set()
 for tri in m.loop_triangles:
  a,b,c=[m.vertices[i].co for i in tri.vertices]
  if (b-a).cross(c-a).length_squared<=1e-16:bad.add(tri.polygon_index)
 maximum=0
 for index in bad:
  p=m.polygons[index];assert m.materials[p.material_index].name=='AshV4_Forelocks_Baked'
  ids=list(p.vertices);points=[m.vertices[i].co.copy() for i in ids];center=sum(points,Vector())/len(points)
  assert max((p-center).length for p in points)<.0003,'Only microcaps may be expanded'
  for i,p in zip(ids,points):
   delta=(p-center)*.60;before=[k.data[i].co.copy() for k in m.shape_keys.key_blocks];m.vertices[i].co=p+delta
   for key,co in zip(m.shape_keys.key_blocks,before):key.data[i].co=co+delta
   maximum=max(maximum,delta.length)
 # The unused archival UVSource layer is not a second runtime UV map. Only
 # verified UV0 is exported; it contains both body and the new equipment.
 for layer in list(m.uv_layers)[1:]:m.uv_layers.remove(layer)
 m.update();rows.append({'lod':level,'browCapsEnlarged':len(bad),'maximumDisplacementMetres':maximum})
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'ArtSource/P08/Golden/Ash/V6/RB_Golden_Ash_V6.blend',compress=False)
print('ASH_V6_BROW_MICROCAPS '+json.dumps(rows))
