import bpy,json,math
from mathutils import Matrix
ROOT='D:/Project/Unity/racing-bois/';rig=bpy.data.objects['RB_P06_Rider_Rig'];rig.animation_data.action=None
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
rows=[]
for level in range(3):
 equipment=bpy.data.objects['AshV6_L'+str(level)+'_Equipment'];mesh=equipment.data;mesh.calc_loop_triangles();bad=[];uvbad=[]
 for tri in mesh.loop_triangles:
  a,b,c=[mesh.vertices[i].co for i in tri.vertices]
  if (b-a).cross(c-a).length_squared<=1e-16:bad.append(tri.index)
  a,b,c=[mesh.uv_layers[0].data[i].uv for i in tri.loops];ab=b-a;ac=c-a
  if abs(ab.x*ac.y-ab.y*ac.x)<=1e-14:uvbad.append(tri.index)
 rows.append({'lod':level,'triangles':len(mesh.loop_triangles),'physicalFailures':bad,'uvFailures':uvbad})
print('ASH_V6_PREMERGE '+json.dumps(rows))
